import sys
sys.path.append('C:/Users/ezequ/Downloads/dash-ecas-v2/dash-ecas-v2/dash1')

from conn_db import get_db_engine
import pandas as pd
from pathlib import Path
from auxiliar import *

db_engine = get_db_engine()

#Recopilación de trayectoria
def agrupar_trayectoria_post_titulacion(df_trayectoria, df_titulados):

    # ---------- 1) BASE METADATA TITULADOS ----------
    df_base = df_titulados[
        [
            "mrun",
            "cohorte",
            "anio_titulacion",
            "gen_alu",
            "jornada",
            "rango_edad"
        ]
    ].copy()

    # --- NORMALIZACIÓN DE RANGO EDAD ---
    # Pasamos a minúsculas y quitamos espacios extra para evitar: '20 a 24 Años' != '20 a 24 años'
    df_base["rango_edad"] = (
        df_base["rango_edad"]
        .astype(str)
        .str.lower()
        .str.strip()
        .str.capitalize() # Deja: '20 a 24 años'
    )

    df_base.rename(columns={
        "cohorte": "año_cohorte_ecas",
        "anio_titulacion": "año_titulacion_ecas"
    }, inplace=True)

    # Traducción de género
    mapa_genero = {1: "Hombre", 2: "Mujer"}
    df_base["gen_alu"] = (
        df_base["gen_alu"]
        .map(mapa_genero)
        .fillna("Sin información")
    )

    # ---------- 2) AGRUPACIÓN POST-ECAS POR CARRERA ----------
    # (El resto de la función se mantiene igual...)
    df_agrupado = (
        df_trayectoria
        .groupby(
            ["mrun", "institucion_destino", "carrera_destino", "nivel_global"],
            as_index=False
        )
        .agg(
            anio_ingreso_destino=("anio_matricula_destino", "min"),
            anio_ultimo_matricula=("anio_matricula_destino", "max"),
            area_conocimiento_destino=("area_conocimiento_destino", "first"),
            duracion_total_carrera=("duracion_total_carrera", "first"),
            tipo_inst_1=("tipo_inst_1", "first"),
            tipo_inst_2=("tipo_inst_2", "first"),
            tipo_inst_3=("tipo_inst_3", "first")
        )
    )

    # ---------- 3) SERIALIZAR TRAYECTORIA POST-ECAS ----------
    df_trayectoria_lista = (
        df_agrupado
        .sort_values(["mrun", "anio_ingreso_destino"])
        .groupby("mrun")
        .agg({col: list for col in df_agrupado.columns if col != 'mrun'})
        .reset_index()
    )

    # ---------- 4) MERGE FINAL ----------
    df_salida = pd.merge(df_base, df_trayectoria_lista, on="mrun", how="left")

    columnas_lista = [
        "anio_ingreso_destino", "anio_ultimo_matricula", "institucion_destino",
        "carrera_destino", "nivel_global", "area_conocimiento_destino",
        "duracion_total_carrera", "tipo_inst_1", "tipo_inst_2", "tipo_inst_3"
    ]

    for col in columnas_lista:
        df_salida[col] = df_salida[col].apply(lambda x: x if isinstance(x, list) else [])

    # ---------- 5) ORDEN CRONOLÓGICO ----------
    df_salida = df_salida.apply(ordenar_trayectoria_por_anio, axis=1)

    return df_salida

def creacion_trayectoria_titulados(db_conn):

    # 1️⃣ Titulados ECAS (metadata estable)
    sql_titulados_ecas = """
    SELECT
        mrun,
        MAX(gen_alu) AS gen_alu,
        MIN(anio_ing_carr_ori) AS cohorte,
        MAX(cat_periodo) AS anio_titulacion,
        MAX(jornada) AS jornada,
        MAX(rango_edad) AS rango_edad
    FROM vista_titulados_unificada_limpia
    WHERE mrun IS NOT NULL
      AND cod_inst = 104
      AND anio_ing_carr_ori BETWEEN 2007 AND 2025
    GROUP BY mrun
    """
    df_titulados = pd.read_sql(sql_titulados_ecas, db_conn)

    # 4️⃣ Tabla temporal MRUNs titulados
    df_mruns_temp = pd.DataFrame(df_titulados["mrun"].unique(), columns=["mrun"])
    df_mruns_temp.to_sql("#TempMrunsTitulados", db_conn, if_exists="replace", index=False)

    # 5️⃣ Trayectoria post-ECAS
    sql_trayectoria = """
    SELECT
        m.mrun,
        m.cat_periodo AS anio_matricula_destino,
        m.nomb_inst AS institucion_destino,
        m.nomb_carrera AS carrera_destino,
        m.area_conocimiento AS area_conocimiento_destino,
        m.nivel_global,
        m.nivel_carrera_1,
        m.nivel_carrera_2,
        m.cod_inst,
        m.dur_total_carr AS duracion_total_carrera,
        m.tipo_inst_1,
        m.tipo_inst_2,
        m.tipo_inst_3,
        ISNULL(m.requisito_ingreso, 'Sin información') AS requisito_ingreso
    FROM vista_matricula_unificada m
    INNER JOIN #TempMrunsTitulados t
        ON m.mrun = t.mrun
    ORDER BY m.mrun, m.cat_periodo;
    """
    df_trayectoria = pd.read_sql(sql_trayectoria, db_conn)

    df_trayectoria = pd.merge(
        df_trayectoria,
        df_titulados,
        on="mrun",
        how="left"
    )

    # 6️⃣ Agrupación final (resumen)
    df_trayectoria_agrupada = agrupar_trayectoria_post_titulacion(
        df_trayectoria,
        df_titulados
    )

    return df_trayectoria_agrupada

def exportar_trayectoria_post_ecas_excel(
    df_trayectoria_agrupada: pd.DataFrame,
    ruta_salida: str
) -> None:
    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    # ---- 1️⃣ Preparar versión "amigable" para Excel (listas → texto)
    df_excel_resumen = df_trayectoria_agrupada.copy()

    columnas_lista = [
        'institucion_destino',
        'carrera_destino',
        'nivel_global',
        'area_conocimiento_destino',
        'anio_ingreso_destino',
        'anio_ultimo_matricula',
        'duracion_total_carrera',
        'tipo_inst_1',
        'tipo_inst_2',
        'tipo_inst_3'
    ]

    for col in columnas_lista:
        if col in df_excel_resumen.columns:
            df_excel_resumen[col] = df_excel_resumen[col].apply(
                lambda x: " | ".join(map(str, x)) if isinstance(x, list) else ""
            )

    # ---- 2️⃣ Exportar Excel
    with pd.ExcelWriter(ruta, engine='xlsxwriter') as writer:
        df_excel_resumen.to_excel(
            writer,
            sheet_name='Trayectoria_Resumen',
            index=False
        )

        workbook = writer.book
        worksheet = writer.sheets['Trayectoria_Resumen']

        for idx, col in enumerate(df_excel_resumen.columns):
            max_len = max(
                df_excel_resumen[col].astype(str).map(len).max(),
                len(col)
            )
            worksheet.set_column(idx, idx, min(max_len + 2, 50))

    print(f"✔ Archivo exportado correctamente en: {ruta}")

if __name__ == "__main__":

    df_trayectoria_agrupada = creacion_trayectoria_titulados(db_engine)

    exportar_trayectoria_post_ecas_excel(
        df_trayectoria_agrupada=df_trayectoria_agrupada,
        ruta_salida="trayectoria_post_ecas.xlsx"
    )

    print("✅ Proceso finalizado correctamente.")
