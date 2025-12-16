import sys
sys.path.append('C:/Users/ezequ/Downloads/dash-ecas-v2/dash-ecas-v2/dash1')

from conn_db import get_db_engine
import pandas as pd
from queries import agrupar_trayectoria_por_carrera
from pathlib import Path

#KPI 1: Nivel de reingreso a la educación superior
#Debemos evaluar los ex-alumnos de ECAS que se titularon, y se han matriculado nuevamente en alguna institución de educación superior en los años posteriores a su titulación.
#Veremos si estudian una carrera de pregrado, postitulo o postgrado.
#Usaremos la vista vista_titulados_unificada_limpia para obtener los titulados de ECAS, y luego
#revisaremos en la vista_matricula_unificada donde se matricularon fuera de ECAS, identificando si es pregrado, postitulo o postgrado.
#a través del campo nivel_global.
#Finalmente, calcularemos el porcentaje de titulados que reingresaron a la educación superior por cohorte, es decir
#por año en que ingresaron a ECAS.

db_engine = get_db_engine()

def agrupar_trayectoria_post_titulacion(df_trayectoria, df_titulados):
    """
    Agrupa la trayectoria académica posterior a la titulación ECAS.
    Una fila por titulado, con listas que representan su trayectoria.
    """

    df_base = df_titulados[['mrun', 'cohorte', 'anio_titulacion']].drop_duplicates()
    df_base.rename(columns={
        'cohorte': 'año_cohorte_ecas',
        'anio_titulacion': 'año_titulacion_ecas'
    }, inplace=True)

    df_agrupado = (
        df_trayectoria
        .groupby(['mrun', 'institucion_destino', 'carrera_destino', 'nivel_global'])
        .agg(
            anio_ingreso_destino=('anio_matricula_destino', 'min'),
            anio_ultimo_matricula=('anio_matricula_destino', 'max'),
            area_conocimiento_destino=('area_conocimiento_destino', 'first'),
            duracion_total_carrera=('duracion_total_carrera', 'first')
        )
        .reset_index()
    )

    df_trayectoria_lista = (
        df_agrupado
        .groupby('mrun')
        .agg(
            anio_ingreso_destino=('anio_ingreso_destino', list),
            anio_ultimo_matricula=('anio_ultimo_matricula', list),
            institucion_destino=('institucion_destino', list),
            carrera_destino=('carrera_destino', list),
            nivel_global=('nivel_global', list),
            area_conocimiento_destino=('area_conocimiento_destino', list),
            duracion_total_carrera=('duracion_total_carrera', list)
        )
        .reset_index()
    )

    df_salida = pd.merge(
        df_base,
        df_trayectoria_lista,
        on='mrun',
        how='left'
    )

    columnas_lista = [
        'anio_ingreso_destino',
        'anio_ultimo_matricula',
        'institucion_destino',
        'carrera_destino',
        'nivel_global',
        'area_conocimiento_destino',
        'duracion_total_carrera'
    ]

    for col in columnas_lista:
        df_salida[col] = df_salida[col].apply(
            lambda x: x if isinstance(x, list) else []
        )

    return df_salida

def creacion_trayectoria_titulados(db_conn):
    sql_titulados_ecas = f"""
    SELECT
        mrun,
        MIN(anio_ing_carr_ori) AS cohorte,
        MAX(cat_periodo) AS anio_titulacion
    FROM vista_titulados_unificada_limpia
    WHERE mrun IS NOT NULL
    AND cod_inst = 104
    AND anio_ing_carr_ori BETWEEN 2007 AND 2025
    GROUP BY mrun
    """
    df_titulados = pd.read_sql(sql_titulados_ecas, db_conn)

    mruns_titulados = df_titulados['mrun'].unique().tolist()

    df_mruns_temp = pd.DataFrame(mruns_titulados, columns=['mrun'])
    df_mruns_temp.to_sql('#TempMrunsTitulados', db_conn, if_exists='replace', index=False)

    sql_trayectoria = f"""SELECT
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
    m.tipo_inst_1
    FROM vista_matricula_unificada m
    INNER JOIN #TempMrunsTitulados t
        ON m.mrun = t.mrun
    ORDER BY m.mrun, m.cat_periodo;
    """

    df_trayectoria = pd.read_sql(sql_trayectoria, db_conn)

    df_trayectoria = pd.merge(
        df_trayectoria,
        df_titulados[['mrun', 'anio_titulacion', 'cohorte']],
        on='mrun',
        how='left'
    )

    df_post_titulacion = df_trayectoria[
        df_trayectoria['anio_matricula_destino'] > df_trayectoria['anio_titulacion']
    ].copy()

    mruns_con_reingreso = df_post_titulacion['mrun'].unique()
    mruns_titulados_base = df_titulados['mrun'].unique()

    mruns_sin_reingreso = [
        mrun for mrun in mruns_titulados_base
        if mrun not in mruns_con_reingreso
    ]

    df_sin_reingreso = df_titulados[
    df_titulados['mrun'].isin(mruns_sin_reingreso)
    ].copy()

    df_trayectoria_agrupada = agrupar_trayectoria_post_titulacion(df_trayectoria, df_titulados)

    return df_trayectoria_agrupada, df_post_titulacion

def exportar_trayectoria_post_ecas_excel(
    df_trayectoria_agrupada: pd.DataFrame,
    df_trayectoria_detallada: pd.DataFrame,
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
        'duracion_total_carrera'
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

        df_trayectoria_detallada.to_excel(
            writer,
            sheet_name='Trayectoria_Detallada',
            index=False
        )

        # ---- 3️⃣ Ajustes estéticos mínimos
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

    df_trayectoria_agrupada, df_trayectoria_detallada = creacion_trayectoria_titulados(db_engine)

    exportar_trayectoria_post_ecas_excel(
        df_trayectoria_agrupada=df_trayectoria_agrupada,
        df_trayectoria_detallada=df_trayectoria_detallada,
        ruta_salida="trayectoria_post_ecas.xlsx"
    )

    print("✅ Proceso finalizado correctamente.")

