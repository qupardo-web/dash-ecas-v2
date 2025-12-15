from typing import Optional
import pandas as pd
import ast
import numpy as np
from conn_db import get_db_engine

db_conn = get_db_engine()

FILE_DESTINO = "fuga_a_destino_todas_cohortes.xlsx"
FILE_ABANDONO = "abandono_total_todas_cohortes.xlsx"

#KPI para calcular las instituciones a las que se fueron los estudiantes que abandonaron.
def get_top_fuga_a_destino(top_n: int = 10, anio_n: Optional[int] = None):
    df = pd.read_excel(FILE_DESTINO)

    df_filtrado = df.copy()

    if anio_n is not None:
        df_filtrado['año_cohorte_ecas'] = pd.to_numeric(df_filtrado['año_cohorte_ecas'], errors='coerce').fillna(-1)
        df_filtrado = df_filtrado[df_filtrado['año_cohorte_ecas'] == anio_n].copy()
    
    def parse_list_or_empty(x):
        if isinstance(x, str):
            try:
                import ast
                return ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return []
        return x if isinstance(x, list) else []

    df_filtrado['institucion_destino'] = df_filtrado['institucion_destino'].apply(parse_list_or_empty)

    df_exploded = df_filtrado.explode('institucion_destino').copy()
    
    df_exploded.dropna(subset=['institucion_destino'], inplace=True)
    df_exploded = df_exploded[df_exploded['institucion_destino'] != '']
    
    df_conteo = df_exploded.groupby('institucion_destino')['mrun'].nunique().reset_index()
    df_conteo.rename(columns={'mrun': 'estudiantes_recibidos'}, inplace=True)
    
    df_top = df_conteo.sort_values(
        by='estudiantes_recibidos', 
        ascending=False
    ).head(top_n)
    
    df_top.reset_index(drop=True, inplace=True)
    df_top.index = df_top.index + 1
    df_top.index.name = 'Ranking'

    return df_top

#KPI para calcular las carreras a las que se fueron los estudiantes que abandonaron.
def get_top_fuga_a_carrera(top_n: int = 10, anio_n: Optional[int] = None):
    
    df = pd.read_excel(FILE_DESTINO)

    df_filtrado = df.copy()

    if anio_n is not None:
        df_filtrado['año_cohorte_ecas'] = pd.to_numeric(df_filtrado['año_cohorte_ecas'], errors='coerce').fillna(-1)
        df_filtrado = df_filtrado[df_filtrado['año_cohorte_ecas'] == anio_n].copy()
    
    def parse_list_or_empty(x):
        if isinstance(x, str):
            try:
                import ast
                return ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return []
        return x if isinstance(x, list) else []

    df_filtrado['carrera_destino'] = df_filtrado['carrera_destino'].apply(parse_list_or_empty)

    df_exploded = df_filtrado.explode('carrera_destino').copy()
    
    df_exploded.dropna(subset=['carrera_destino'], inplace=True)
    df_exploded = df_exploded[df_exploded['carrera_destino'] != '']
    
    df_conteo = df_exploded.groupby('carrera_destino')['mrun'].nunique().reset_index()
    df_conteo.rename(columns={'mrun': 'estudiantes_recibidos'}, inplace=True)
    
    df_top = df_conteo.sort_values(
        by='estudiantes_recibidos', 
        ascending=False
    ).head(top_n)
    
    df_top.reset_index(drop=True, inplace=True)
    df_top.index = df_top.index + 1
    df_top.index.name = 'Ranking'

    return df_top

#KPI para calcular las areas a las que se fueron los estudiantes que abandonaron.
def get_top_fuga_a_area(top_n: int = 10, anio_n: Optional[int] = None):
    df = pd.read_excel(FILE_DESTINO)

    df_filtrado = df.copy()

    if anio_n is not None:
        df_filtrado['año_cohorte_ecas'] = pd.to_numeric(df_filtrado['año_cohorte_ecas'], errors='coerce').fillna(-1)
        df_filtrado = df_filtrado[df_filtrado['año_cohorte_ecas'] == anio_n].copy()
    
    def parse_list_or_empty(x):
        if isinstance(x, str):
            try:
                import ast
                return ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return []
        return x if isinstance(x, list) else []

    df_filtrado['area_conocimiento_destino'] = df_filtrado['area_conocimiento_destino'].apply(parse_list_or_empty)

    df_exploded = df_filtrado.explode('area_conocimiento_destino').copy()
    
    df_exploded.dropna(subset=['area_conocimiento_destino'], inplace=True)
    df_exploded = df_exploded[df_exploded['area_conocimiento_destino'] != '']
    
    df_conteo = df_exploded.groupby('area_conocimiento_destino')['mrun'].nunique().reset_index()
    df_conteo.rename(columns={'mrun': 'estudiantes_recibidos'}, inplace=True)
    
    df_top = df_conteo.sort_values(
        by='estudiantes_recibidos', 
        ascending=False
    ).head(top_n)
    
    df_top.reset_index(drop=True, inplace=True)
    df_top.index = df_top.index + 1
    df_top.index.name = 'Ranking'

    return df_top

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

    def parse_list_or_empty(x):
        if isinstance(x, str):
            try:
                # Usar ast.literal_eval es seguro para evaluar strings de Python
                return ast.literal_eval(x)
            except (ValueError, SyntaxError):
                return []
        return x if isinstance(x, list) else []

    df['anio_ingreso_destino'] = df['anio_ingreso_destino'].apply(parse_list_or_empty)

    df['año_cohorte_ecas'] = pd.to_numeric(df['año_cohorte_ecas'], errors='coerce').fillna(-1)

    df_base_filtrada = df[
        (df['año_cohorte_ecas'] >= 2007) & (df['año_cohorte_ecas'] <= 2025)
    ].copy()
    
    df = df_base_filtrada # Usamos este DataFrame como la nueva base para el resto de la función
    
    df_filtrado_cohorte = df.copy()
    
    if anio_n is not None:
        # Solo filtra si anio_n tiene un valor
        df_filtrado_cohorte = df_filtrado_cohorte[df_filtrado_cohorte['año_cohorte_ecas'] == anio_n].copy()
    
    df = df_filtrado_cohorte
    
    if df.empty:
        print("Advertencia: No hay datos de estudiantes para el filtro especificado.")
        return pd.DataFrame()

    df['primer_ingreso_destino'] = df['anio_ingreso_destino'].apply(lambda x: x[0] if x and isinstance(x, list) else np.nan)
    
    df['año_primer_fuga'] = pd.to_numeric(df['año_primer_fuga'], errors='coerce')
    df['primer_ingreso_destino'] = pd.to_numeric(df['primer_ingreso_destino'], errors='coerce')

    df.dropna(subset=['primer_ingreso_destino'], inplace=True)

    df['tiempo_de_descanso'] = df['primer_ingreso_destino'] - df['año_primer_fuga']
    
    bins = [-np.inf, 0, 1, 2, 5, 10, np.inf] # 7 bordes
    labels = ['Reingreso Inmediato/Antes (<=0)', '1 año', '2 años', '3 a 5 años', '6 a 10 años', '+10 años'] # 6 etiquetas
    
    df['rango_descanso'] = pd.cut(df['tiempo_de_descanso'], bins=bins, labels=labels, right=True)
    
    # 5b. Agrupar por Cohorte y Rango para contar MRUNs únicos
    df_conteo = df.groupby(['rango_descanso', 'año_cohorte_ecas'], observed=True)['mrun'].nunique().reset_index()
    df_conteo.rename(columns={'mrun': 'conteo_mruns'}, inplace=True)

    # 5c. Calcular el total de desertores por cohorte (para obtener el porcentaje base)
    total_por_cohorte = df.groupby('año_cohorte_ecas', observed=True)['mrun'].nunique().reset_index()
    total_por_cohorte.rename(columns={'mrun': 'total_desertores_cohorte'}, inplace=True)
    
    # 5d. Unir y calcular el porcentaje
    df_final = pd.merge(df_conteo, total_por_cohorte, on='año_cohorte_ecas', how='left')
    df_final['porcentaje'] = (df_final['conteo_mruns'] / df_final['total_desertores_cohorte']) * 100
    
    # 5e. Formato final: Pivotar (para el reporte) y añadir el total general
    df_pivot_cohorte = df_final.pivot_table(
        index='rango_descanso',
        columns='año_cohorte_ecas',
        values='porcentaje',
        fill_value=0,
        observed=True
    )
    
    # 5f. Calcular el Porcentaje Total General (Base: todos los desertores con destino)
    total_general_mruns = df['mrun'].nunique()
    df_conteo_total = df.groupby('rango_descanso', observed=True)['mrun'].nunique().reset_index()
    df_conteo_total['porcentaje'] = (df_conteo_total['mrun'] / total_general_mruns) * 100
    df_conteo_total.rename(columns={'porcentaje': 'TOTAL GENERAL'}, inplace=True)
    
    # Unir el total general al resultado pivotado
    df_pivot_final = pd.merge(
        df_pivot_cohorte.reset_index(),
        df_conteo_total[['rango_descanso', 'TOTAL GENERAL']],
        on='rango_descanso',
        how='left'
    )
    df_pivot_final.set_index('rango_descanso', inplace=True)
    
    # Limpieza de nombres de columnas
    df_pivot_final.columns = [int(col) if isinstance(col, float) else col for col in df_pivot_final.columns]
    
    return df_pivot_final.sort_index()

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