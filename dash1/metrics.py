from typing import Optional
import pandas as pd
import ast
import numpy as np
from conn_db import get_db_engine

db_conn = get_db_engine()

FILE_DESTINO = "fuga_a_destino_todas_cohortes.xlsx"
FILE_ABANDONO = "abandono_total_todas_cohortes.xlsx"

def split_pipe_column(x):
    if isinstance(x, str):
        return [p.strip() for p in x.split("|") if p.strip() != ""]
    return []

#Funciones auxiliares
def normalizar_trayectoria_destino(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    columnas_pipe = [
        "institucion_destino",
        "carrera_destino",
        "area_conocimiento_destino",
        "anio_ingreso_destino"
    ]

    for col in columnas_pipe:
        df[col] = df[col].apply(split_pipe_column)

    df = df.explode(columnas_pipe)

    df["anio_ingreso_destino"] = pd.to_numeric(
        df["anio_ingreso_destino"], errors="coerce"
    )

    df = df.dropna(subset=["anio_ingreso_destino"])
    df = df[df["institucion_destino"] != ""]

    return df

def construir_secuencia_destino(df: pd.DataFrame) -> pd.DataFrame:
    df = (
        df.sort_values(["mrun", "anio_ingreso_destino"])
          .assign(orden_destino=lambda x: x.groupby("mrun").cumcount() + 1)
    )
    return df

def get_destinos_ecas(anio_n: Optional[int] = None) -> pd.DataFrame:
    df = pd.read_excel(FILE_DESTINO)

    if anio_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(df["año_cohorte_ecas"], errors="coerce")
        df = df[df["año_cohorte_ecas"] == anio_n]

    df = normalizar_trayectoria_destino(df)
    df = construir_secuencia_destino(df)

    return df

#KPI para calcular las instituciones a las que se fueron los estudiantes que abandonaron.
def get_top_fuga_a_destino(top_n=10, anio_n=None, orden=1):
    df = get_destinos_ecas(anio_n)

    df_orden = df[df["orden_destino"] == orden]

    out = (
        df_orden
        .groupby("institucion_destino")["mrun"]
        .nunique()
        .reset_index(name="estudiantes_recibidos")
        .sort_values("estudiantes_recibidos", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    out.index += 1
    out.index.name = "Ranking"

    return out

print(get_top_fuga_a_destino(10, orden=1))
# Segunda institución
print(get_top_fuga_a_destino(10, orden=2))
# Tercera institución
print(get_top_fuga_a_destino(10, orden=3))
#KPI para calcular las carreras a las que se fueron los estudiantes que abandonaron.
def get_top_fuga_a_carrera(top_n: int = 10, anio_n: Optional[int] = None):

    df = get_primer_destino_df(anio_n)

    df_conteo = (
        df
        .groupby("carrera_destino")["mrun"]
        .nunique()
        .reset_index(name="estudiantes_recibidos")
        .sort_values("estudiantes_recibidos", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    df_conteo.index += 1
    df_conteo.index.name = "Ranking"

    return df_conteo

#KPI para calcular las areas a las que se fueron los estudiantes que abandonaron.
def get_top_fuga_a_area(top_n: int = 10, anio_n: Optional[int] = None):

    df = get_primer_destino_df(anio_n)

    df_conteo = (
        df
        .groupby("area_conocimiento_destino")["mrun"]
        .nunique()
        .reset_index(name="estudiantes_recibidos")
        .sort_values("estudiantes_recibidos", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    df_conteo.index += 1
    df_conteo.index.name = "Ranking"

    return df_conteo

#KPI para calcular una estimación de la titulación de los estudiantes que abandonaron.
def get_estimation_titulacion_abandono(anio_n: Optional[int] = None):

    df_destino_meta = pd.read_excel(FILE_DESTINO)

    df_destino_meta['año_cohorte_ecas'] = pd.to_numeric(df_destino_meta['año_cohorte_ecas'], errors='coerce').fillna(-1)
    df_destino_meta['mrun_str'] = df_destino_meta['mrun'].dropna().astype(str)

    df_filtrado_cohorte = df_destino_meta[
        (df_destino_meta['año_cohorte_ecas'] >= 2007) & 
        (df_destino_meta['año_cohorte_ecas'] <= 2025)
    ].copy()
    
    if anio_n is not None:
        df_filtrado_cohorte = df_filtrado_cohorte[df_filtrado_cohorte['año_cohorte_ecas'] == anio_n].copy()

    df_mruns_y_fuga = df_filtrado_cohorte[['mrun_str', 'año_primer_fuga']].drop_duplicates()
    
    mruns_con_destino = df_mruns_y_fuga['mrun_str'].tolist()

    if not mruns_con_destino:
        print("Advertencia: No se encontraron MRUNs clasificados con fuga a destino en el archivo.")
        return pd.DataFrame()
        
    df_mruns_y_fuga.rename(columns={'mrun_str': 'mrun_fuga', 'año_primer_fuga': 'anio_fuga'}, inplace=True)
    df_mruns_y_fuga['mrun_fuga'] = df_mruns_y_fuga['mrun_fuga'].astype(str)
    
    df_mruns_y_fuga.to_sql('#TempFugas', db_conn, if_exists='replace', index=False, chunksize=500)
    
    sql_titulados_reales = f"""
    SELECT DISTINCT
        T.mrun
    FROM 
        dbo.vista_titulados_unificada_limpia T
    INNER JOIN 
        #TempFugas F ON T.mrun = F.mrun_fuga
    WHERE 
        -- Aseguramos que el registro de titulación sea POSTERIOR O IGUAL al año de fuga
        CAST(T.cat_periodo AS INT) >= F.anio_fuga
        -- Aseguramos que el título exista (después de la limpieza)
        AND T.nomb_titulo_obtenido IS NOT NULL;
    """

    try:
        df_titulados_reales = pd.read_sql(sql_titulados_reales, db_conn)
    except Exception as e:
        print(f"ERROR al ejecutar la consulta SQL en la vista de titulados: {e}")
        return pd.DataFrame()
    finally:
        try:
            db_conn.execute("DROP TABLE #TempFugas;")
        except Exception:
            pass 

    mruns_titulados_reales = df_titulados_reales['mrun'].astype(str).tolist()

    df_filtrado_cohorte['es_titulado_real'] = df_filtrado_cohorte['mrun_str'].isin(mruns_titulados_reales)

    df_titulados_final = df_filtrado_cohorte[df_filtrado_cohorte['es_titulado_real']].copy()
    
    total_general = df_titulados_final['mrun'].nunique()

    df_conteo_cohorte = df_titulados_final.groupby('año_cohorte_ecas')['mrun'].nunique().reset_index()
    df_conteo_cohorte.rename(columns={'mrun': 'estudiantes_titulados'}, inplace=True)
    df_conteo_cohorte['año_cohorte_ecas'] = df_conteo_cohorte['año_cohorte_ecas'].astype(int)

    df_total = pd.DataFrame([{'año_cohorte_ecas': 'TOTAL GENERAL', 'estudiantes_titulados': total_general}])
    df_final = pd.concat([df_conteo_cohorte, df_total], ignore_index=True)

    return df_final

#KPI Estimacion de años para volver a estudiar
def get_tiempo_de_descanso(anio_n: Optional[int] = None):

    df = pd.read_excel(FILE_DESTINO)

    # ---------- Parseo formato estándar " | " ----------
    df['anio_ingreso_destino'] = df['anio_ingreso_destino'].apply(
        lambda x: [int(i.strip()) for i in x.split('|')]
        if isinstance(x, str) else []
    )

    df['año_cohorte_ecas'] = pd.to_numeric(df['año_cohorte_ecas'], errors='coerce')
    df['año_primer_fuga'] = pd.to_numeric(df['año_primer_fuga'], errors='coerce')

    df = df[
        (df['año_cohorte_ecas'] >= 2007) &
        (df['año_cohorte_ecas'] <= 2025)
    ]

    if anio_n is not None:
        df = df[df['año_cohorte_ecas'] == anio_n]

    if df.empty:
        return pd.DataFrame()

    # ---------- Primer reingreso ----------
    df['primer_ingreso_destino'] = df['anio_ingreso_destino'].apply(
        lambda x: min(x) if x else np.nan
    )

    df = df.dropna(subset=['primer_ingreso_destino', 'año_primer_fuga'])

    df['tiempo_de_descanso'] = df['primer_ingreso_destino'] - df['año_primer_fuga']

    # ---------- Rangos ----------
    bins = [-np.inf, 0, 1, 2, 5, 10, np.inf]
    labels = [
        'Reingreso Inmediato/Antes (<=0)',
        '1 año',
        '2 años',
        '3 a 5 años',
        '6 a 10 años',
        '+10 años'
    ]

    df['Rango_de_Descanso'] = pd.cut(
        df['tiempo_de_descanso'],
        bins=bins,
        labels=labels
    )

    # ---------- Por cohorte ----------
    conteo = (
        df.groupby(['Rango_de_Descanso', 'año_cohorte_ecas'], observed=False)['mrun']
          .nunique()
          .reset_index(name='conteo')
    )

    total_cohorte = (
        df.groupby('año_cohorte_ecas', observed=False)['mrun']
          .nunique()
          .reset_index(name='total')
    )

    df_merge = conteo.merge(total_cohorte, on='año_cohorte_ecas')
    df_merge['porcentaje'] = (df_merge['conteo'] / df_merge['total']) * 100

    df_pivot = df_merge.pivot_table(
        index='Rango_de_Descanso',
        columns='año_cohorte_ecas',
        values='porcentaje',
        fill_value=0,
        observed=False
    )

    # ---------- TOTAL GENERAL ----------
    total_general = df['mrun'].nunique()

    df_total = (
        df.groupby('Rango_de_Descanso', observed=False)['mrun']
          .nunique()
          .reset_index(name='TOTAL GENERAL')
    )

    df_total['TOTAL GENERAL'] = (df_total['TOTAL GENERAL'] / total_general) * 100

    # ---------- Resultado final ----------
    df_final = (
        df_pivot
        .merge(df_total, on='Rango_de_Descanso', how='left')
        .reset_index()
    )

    return df_final

def get_total_fugados_por_cohorte(anio_n: Optional[int] = None) -> pd.DataFrame:
    
    def _load_and_clean(file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_excel(file_path)
        except FileNotFoundError:
            print(f"❌ ERROR: Archivo '{file_path}' no encontrado.")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ ERROR al cargar '{file_path}': {e}")
            return pd.DataFrame()
        
        df['año_cohorte_ecas'] = pd.to_numeric(df['año_cohorte_ecas'], errors='coerce').fillna(-1)
        df = df[(df['año_cohorte_ecas'] >= 2007) & (df['año_cohorte_ecas'] <= 2025)].copy()

        return df[['mrun', 'año_cohorte_ecas']]

    df_destino = _load_and_clean(FILE_DESTINO)
    df_abandono = _load_and_clean(FILE_ABANDONO)

    df_destino_unicos = df_destino.drop_duplicates(subset=['mrun', 'año_cohorte_ecas']).copy()
    df_abandono_unicos = df_abandono.drop_duplicates(subset=['mrun', 'año_cohorte_ecas']).copy()
    
    conteo_destino = df_destino_unicos.groupby('año_cohorte_ecas')['mrun'].nunique().reset_index()
    conteo_destino.rename(columns={'mrun': 'Fuga_a_Destino'}, inplace=True)
    
    conteo_abandono = df_abandono_unicos.groupby('año_cohorte_ecas')['mrun'].nunique().reset_index()
    conteo_abandono.rename(columns={'mrun': 'Abandono_Total'}, inplace=True)
    
    df_consolidado = pd.merge(
        conteo_destino,
        conteo_abandono,
        on='año_cohorte_ecas',
        how='outer'
    ).fillna(0)
    
    df_consolidado['Total_Desertores'] = df_consolidado['Fuga_a_Destino'] + df_consolidado['Abandono_Total']
    df_consolidado['año_cohorte_ecas'] = df_consolidado['año_cohorte_ecas'].astype(int)
    
    df_consolidado['%_Fuga_a_Destino'] = (df_consolidado['Fuga_a_Destino'] / df_consolidado['Total_Desertores']) * 100
    df_consolidado['%_Abandono_Total'] = (df_consolidado['Abandono_Total'] / df_consolidado['Total_Desertores']) * 100
    
    
    total_fuga_destino = df_destino['mrun'].nunique()
    total_abandono = df_abandono['mrun'].nunique()
    total_general = total_fuga_destino + total_abandono
    
    pct_fuga_destino_total = (total_fuga_destino / total_general) * 100 if total_general else 0
    pct_abandono_total_total = (total_abandono / total_general) * 100 if total_general else 0
    
    df_total_general = pd.DataFrame([{
        'año_cohorte_ecas': 'TOTAL GENERAL',
        'Fuga_a_Destino': total_fuga_destino,
        'Abandono_Total': total_abandono,
        'Total_Desertores': total_general,
        '%_Fuga_a_Destino': pct_fuga_destino_total,
        '%_Abandono_Total': pct_abandono_total_total,
    }])
    
    df_cohortes_filtradas = df_consolidado.copy()
    if anio_n is not None:
        df_cohortes_filtradas = df_cohortes_filtradas[
            df_cohortes_filtradas['año_cohorte_ecas'] == anio_n
        ].copy()
        
    df_final = pd.concat([df_cohortes_filtradas, df_total_general], ignore_index=True)
    
    df_final = df_final[[
        'año_cohorte_ecas', 'Total_Desertores', 
        'Fuga_a_Destino', '%_Fuga_a_Destino', 
        'Abandono_Total', '%_Abandono_Total'
    ]]
    
    return df_final

def get_tasa_desercion_por_cohorte(anio_n: Optional[int] = None) -> pd.DataFrame:

    # -------------------------------------------------
    # 1) TOTAL DE INGRESADOS A ECAS POR COHORTE
    # -------------------------------------------------
    sql_ingresados = """
        SELECT
            mrun,
            anio_ing_carr_ori AS año_cohorte_ecas
        FROM vista_matricula_unificada
        WHERE mrun IS NOT NULL
          AND cod_inst = 104
          AND anio_ing_carr_ori BETWEEN 2007 AND 2025
    """

    df_ingresados = pd.read_sql(sql_ingresados, db_conn)

    # Un estudiante cuenta una sola vez por cohorte
    df_ingresados = (
        df_ingresados
        .drop_duplicates(subset=["mrun", "año_cohorte_ecas"])
        .copy()
    )

    total_ingresados = (
        df_ingresados
        .groupby("año_cohorte_ecas")["mrun"]
        .nunique()
        .reset_index(name="Total_Ingresados")
    )

    # -------------------------------------------------
    # 2) TOTAL DE DESERTORES POR COHORTE
    # -------------------------------------------------
    def _load_desertores(file_path: str) -> pd.DataFrame:
        df = pd.read_excel(file_path)
        df["año_cohorte_ecas"] = pd.to_numeric(df["año_cohorte_ecas"], errors="coerce")
        df = df[(df["año_cohorte_ecas"] >= 2007) & (df["año_cohorte_ecas"] <= 2025)]
        return df[["mrun", "año_cohorte_ecas"]]

    df_destino  = _load_desertores(FILE_DESTINO)
    df_abandono = _load_desertores(FILE_ABANDONO)

    # Unificar desertores (evita doble conteo)
    df_desertores = pd.concat([df_destino, df_abandono], ignore_index=True)
    df_desertores = df_desertores.drop_duplicates(subset=["mrun", "año_cohorte_ecas"])

    total_desertores = (
        df_desertores
        .groupby("año_cohorte_ecas")["mrun"]
        .nunique()
        .reset_index(name="Total_Desertores")
    )

    # -------------------------------------------------
    # 3) CONSOLIDACIÓN Y CÁLCULO DE TASAS
    # -------------------------------------------------
    df_final = pd.merge(
        total_ingresados,
        total_desertores,
        on="año_cohorte_ecas",
        how="left"
    ).fillna(0)

    df_final["Total_Desertores"] = df_final["Total_Desertores"].astype(int)
    df_final["No_Desertores"] = (
        df_final["Total_Ingresados"] - df_final["Total_Desertores"]
    )

    df_final["Tasa_Desercion_%"] = (
        df_final["Total_Desertores"] / df_final["Total_Ingresados"]
    ) * 100

    df_final["Tasa_No_Desercion_%"] = 100 - df_final["Tasa_Desercion_%"]

    # -------------------------------------------------
    # 4) FILTRO OPCIONAL POR COHORTE
    # -------------------------------------------------
    if anio_n is not None:
        df_final = df_final[df_final["año_cohorte_ecas"] == anio_n].copy()

    # -------------------------------------------------
    # 5) ORDEN Y SELECCIÓN FINAL
    # -------------------------------------------------
    df_final = df_final.sort_values("año_cohorte_ecas").reset_index(drop=True)

    df_final = df_final[[
        "año_cohorte_ecas",
        "Total_Ingresados",
        "Total_Desertores",
        "No_Desertores",
        "Tasa_Desercion_%",
        "Tasa_No_Desercion_%"
    ]]

    return df_final
