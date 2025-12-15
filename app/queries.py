import pandas as pd
from conn_db import get_db_engine
import numpy as np
from collections import defaultdict
from typing import List, Optional, Tuple

COD_ECAS = 104
CARRERA_LIKE = '%AUDITOR%'
DURACION_DIURNA_SEMESTRES = 8  # 4 años
DURACION_VESPERTINA_SEMESTRES = 9 # 4.5 años

db_conn = get_db_engine()

def get_mruns_per_year(db_conn, anio_n = None):

    #Obtiene todos los mruns por año de ingreso

    filter_anio = ""

    if isinstance(anio_n, int): 
        filter_anio = f"AND anio_ing_carr_ori = {anio_n}"

    sql_query= f"""
    SELECT anio_ing_carr_ori AS ingreso_primero,
	COUNT(DISTINCT mrun) AS Total_Mruns
    FROM  vista_matricula_unificada v
    WHERE cod_inst LIKE 104 
    AND anio_ing_carr_ori BETWEEN 2007 AND 2025
    AND jornada IN ('Diurna', 'Vespertina')
    AND dur_total_carr BETWEEN 8 AND 10
	AND cat_periodo = anio_ing_carr_ori
    GROUP BY anio_ing_carr_ori
    ORDER BY ingreso_primero ASC
    """

    df_total_mruns = pd.read_sql(sql_query, db_conn)

    return df_total_mruns

def get_permanencia_per_year(db_conn, anio_n = None):

    #Evalua la tasa de permanencia de todos los estudiantes año a año

    filter_anio = ""

    filter_anio = f"HAVING T1.cat_periodo = {anio_n}" if isinstance(anio_n, int) else ""

    sql_query = f"""
        WITH base AS (
            SELECT 
                cat_periodo,
                mrun
            FROM vista_matricula_unificada
            WHERE mrun IS NOT NULL
            AND cod_inst = 104 -- Solo estudiantes matriculados en ECAS
        ),
        max_anio AS (
            -- Subconsulta para encontrar el último año registrado en la base
            SELECT MAX(cat_periodo) AS max_periodo FROM base
        )
        SELECT 
            T1.cat_periodo AS anio,
            COUNT(DISTINCT T1.mrun) AS matriculados_base,
            COUNT(DISTINCT T2.mrun) AS permanencia_conteo,
            -- Cálculo de la tasa de permanencia
            CAST(
                CAST(COUNT(DISTINCT T2.mrun) AS FLOAT) * 100 / 
                CAST(COUNT(DISTINCT T1.mrun) AS FLOAT) AS DECIMAL(5, 2)
            ) AS tasa_permanencia_pct
        FROM base AS T1
        
        LEFT JOIN base AS T2
            ON T1.mrun = T2.mrun
            AND T1.cat_periodo + 1 = T2.cat_periodo
        
        WHERE T1.cat_periodo < (SELECT max_periodo FROM max_anio)
        GROUP BY T1.cat_periodo
        {filter_anio}
        ORDER BY anio;
    """

    df_total_permanencia_estudiantes = pd.read_sql(sql_query, db_conn)

    return df_total_permanencia_estudiantes

def get_permanencia_ranking_por_jornada(db_conn, jornada: str, cod_ecas: int = COD_ECAS) -> pd.DataFrame:

    """
    Calcula la tasa de permanencia de primer año para la competencia directa 
    (carrera de Auditoría, duración 8/9 semestres) en una JORNADA específica.
    """
    
    # Aseguramos el formato de string para SQL
    jornada_sql = jornada.replace("'", "''") 
    
    sql_query = f"""
    WITH base AS (
        SELECT 
            vmu.cat_periodo,
            vmu.mrun,
            vmu.cod_inst,
            vmu.nomb_inst,
            vmu.anio_ing_carr_ori,
            vmu.jornada,
            vmu.region_sede,
            vmu.tipo_inst_1
        FROM vista_matricula_unificada vmu
        WHERE vmu.mrun IS NOT NULL 
            AND vmu.jornada = '{jornada_sql}' -- FILTRO CLAVE POR JORNADA
            AND (
                (vmu.nomb_carrera LIKE '{CARRERA_LIKE}' AND vmu.dur_total_carr BETWEEN 8 AND 10 AND vmu.region_sede = 'Metropolitana' AND vmu.tipo_inst_1 = 'Institutos Profesionales')
                OR vmu.cod_inst = {cod_ecas} 
            )
    ),
    permanencia_base AS (
        SELECT 
            b1.cod_inst,
            b1.nomb_inst,
            b1.mrun,
            b1.cat_periodo AS anio_ingreso,
            b1.jornada, 
            CASE WHEN b2.mrun IS NOT NULL THEN 1 ELSE 0 END AS permanece
        FROM base b1
        LEFT JOIN base b2
            ON b1.mrun = b2.mrun
            AND b2.cat_periodo = b1.cat_periodo + 1
            AND b1.cod_inst = b2.cod_inst
            AND b1.jornada = b2.jornada -- Permanencia debe ser en la misma jornada
        WHERE b1.cat_periodo = b1.anio_ing_carr_ori
    )
    SELECT 
        pb.anio_ingreso AS anio,
        pb.nomb_inst,
        pb.cod_inst,
        pb.jornada,
        COUNT(DISTINCT pb.mrun) AS total_estudiantes,
        SUM(pb.permanece) AS permanencia_conteo,
        CAST(
            CAST(SUM(pb.permanece) AS FLOAT) * 100 / 
            CAST(COUNT(DISTINCT pb.mrun) AS FLOAT) AS DECIMAL(5, 2)
        ) AS tasa_permanencia_pct
    FROM permanencia_base pb
    GROUP BY pb.anio_ingreso, pb.nomb_inst, pb.cod_inst, pb.jornada
    ORDER BY pb.anio_ingreso, tasa_permanencia_pct DESC;
    """

    df_all_data = pd.read_sql(sql_query, db_conn)
    
    # Aquí puedes añadir la lógica de Top 5 + ECAS por año (vista en la respuesta anterior)
    # Por simplicidad, esta función devolverá todos los datos por jornada, y el gráfico filtrará.
    return df_all_data


def get_continuidad_per_year(db_conn, anio_n=None):

    filtro = ""
    if isinstance(anio_n, int):
        filtro = f"AND cohorte = {anio_n}"

    sql_query = f"""
    WITH base AS (
        SELECT 
            mrun,
            cat_periodo,
            anio_ing_carr_ori AS cohorte
        FROM vista_matricula_unificada
        WHERE mrun IS NOT NULL
          AND cod_inst = 104
    ),
    cohortes AS (
        SELECT DISTINCT
            mrun,
            cohorte
        FROM base
        WHERE cat_periodo = cohorte
        {filtro}
    ),
    cohorte_totales AS (
        SELECT
            cohorte,
            COUNT(DISTINCT mrun) AS total_ingreso
        FROM cohortes
        GROUP BY cohorte
    ),
    years AS (
        SELECT DISTINCT cat_periodo FROM base
    ),
    continuidad AS (
        SELECT
            c.cohorte,
            y.cat_periodo AS anio_real,
            y.cat_periodo - c.cohorte AS anio_rel
        FROM cohortes c
        JOIN years y
            ON y.cat_periodo >= c.cohorte
    )
    SELECT
        con.cohorte,
        con.anio_rel + 1 AS anio_relativo,
        con.anio_real,
        COUNT(DISTINCT b.mrun) AS estudiantes,
        CAST(COUNT(DISTINCT b.mrun) AS FLOAT) / ct.total_ingreso AS tasa
    FROM continuidad con
    LEFT JOIN base b
        ON b.cohorte = con.cohorte
       AND b.cat_periodo = con.anio_real
    JOIN cohorte_totales ct
        ON ct.cohorte = con.cohorte
    WHERE con.anio_rel >= 0
    GROUP BY 
        con.cohorte,
        con.anio_rel,
        con.anio_real,
        ct.total_ingreso
    ORDER BY cohorte, anio_relativo;
    """

    # Ejecutar
    df = pd.read_sql(sql_query, db_conn)

    return df

def agrupar_trayectoria_por_carrera(df_destino, df_fugas):
    
    df_base = df_fugas[['mrun', 'cohorte', 'anio_fuga']].drop_duplicates()
    df_base.rename(columns={'cohorte': 'año_cohorte_ecas', 'anio_fuga': 'año_primer_fuga'}, inplace=True)

    df_agrupado = df_destino.groupby(['mrun', 'institucion_destino', 'carrera_destino']).agg(
        # El año de ingreso a ESA carrera será el mínimo de los cat_periodo
        anio_ingreso_destino=('anio_matricula_destino', 'min'),
        # El último año de matrícula en ESA carrera será el máximo de los cat_periodo
        anio_ultimo_matricula=('anio_matricula_destino', 'max'),
        # Mantenemos las columnas descriptivas (tomando la primera ocurrencia)
        area_conocimiento_destino=('area_conocimiento_destino', 'first'),
        duracion_total_carrera=('duracion_total_carrera', 'first')
    ).reset_index()

    # 3. Re-agrupar por MRUN para generar las listas (formato de salida final)
    df_final_estructurado = df_agrupado.groupby('mrun').agg(
        # Nota: La cohorte ECAS ya no está en este DataFrame, la tomaremos del df_base
        anio_ingreso_destino=('anio_ingreso_destino', list),
        anio_ultimo_matricula=('anio_ultimo_matricula', list),
        institucion_destino=('institucion_destino', list),
        carrera_destino=('carrera_destino', list),
        area_conocimiento_destino=('area_conocimiento_destino', list),
        duracion_total_carrera=('duracion_total_carrera', list)
    ).reset_index()

    # 4. Incorporar la información de trayectoria al df_base (que tiene la Cohorte ECAS correcta)
    df_salida = pd.merge(
        df_base, 
        df_final_estructurado,
        on='mrun', 
        how='inner' 
    )

    # 5. Rellenar los NaN (para los desertores sin trayectoria posterior) con listas vacías
    columnas_lista = ['anio_ingreso_destino', 'anio_ultimo_matricula', 'institucion_destino', 'carrera_destino', 'area_conocimiento_destino']
    for col in columnas_lista:
        df_salida[col] = df_salida[col].apply(lambda x: x if isinstance(x, list) else [])

    return df_salida

def calcular_duracion_nominal_ecas(row):
    cohorte = row['cohorte']
    jornada = row['jornada']
    
    # Aseguramos que cohorte sea tratada como número (aunque en el merge debería serlo)
    if not isinstance(cohorte, int):
        cohorte = int(cohorte)

    # Regla 1: Cohortes de 2021 en adelante
    if cohorte >= 2021:
        if 'DIURNA' in jornada.upper():
            return 8 / 2.0  # 4.0 años
        elif 'VESPERTINA' in jornada.upper():
            return 9 / 2.0  # 4.5 años
    
    # Regla 2: Cohortes anteriores a 2021
    elif cohorte < 2021:
        if 'DIURNA' in jornada.upper():
            return 9 / 2.0  # 4.5 años
        elif 'VESPERTINA' in jornada.upper():
            return 10 / 2.0 # 5.0 años
            
    return 0.0 # Duración 0 si la jornada/cohorte no aplica

def get_fuga_multianual_trayectoria(db_conn, anio_n: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    
    filtro_cohorte = f"AND anio_ing_carr_ori = {anio_n}" if isinstance(anio_n, int) else ""

    # 1. Identificación de estudiantes en ECAS, OBTENIENDO JORNADA Y CARRERA DE ORIGEN
    sql_base_ecas = f"""
    SELECT 
        mrun,
        cat_periodo,
        anio_ing_carr_ori AS cohorte,
        cod_inst,
        jornada, 
        nomb_carrera 
    FROM vista_matricula_unificada
    WHERE mrun IS NOT NULL 
    AND cod_inst = 104 
    {filtro_cohorte}
    ORDER BY mrun, cat_periodo;
    """
    
    df_ecas_cohortes = pd.read_sql(sql_base_ecas, db_conn)
    
    if df_ecas_cohortes.empty:
        print("No se encontraron datos de matrículas para la cohorte especificada en ECAS.")
        return pd.DataFrame(), pd.DataFrame()

    # Identificar la cohorte inicial de cada estudiante (y la jornada/carrera de origen para el merge posterior)
    cohortes_iniciales = df_ecas_cohortes[['mrun', 'cohorte']].drop_duplicates()
    cohortes_iniciales.dropna(subset=['cohorte'], inplace=True)
    
    if cohortes_iniciales.empty:
        print("Advertencia: No quedan cohortes válidas después de limpiar los valores nulos.")
        return pd.DataFrame(), pd.DataFrame()
    
    max_anio_registro = df_ecas_cohortes['cat_periodo'].max()
    if pd.isna(max_anio_registro):
        print("Advertencia: max_anio_registro es NaN. Saliendo.")
        return pd.DataFrame(), pd.DataFrame() 
    
    max_anio_registro = int(max_anio_registro)
    
    
    matrículas_ecas = set(df_ecas_cohortes[['mrun', 'cat_periodo']].apply(tuple, axis=1))
    fugas_detectadas_supuestas = []

    for index, row in cohortes_iniciales.iterrows():
        mrun = row['mrun']
        cohorte = row['cohorte']

        cohorte = int(cohorte)

        matriculas_mrun = df_ecas_cohortes[df_ecas_cohortes['mrun'] == mrun]
    
        if matriculas_mrun.empty:
            continue 
            
        max_anio_en_ecas = int(matriculas_mrun['cat_periodo'].max())
        
        if max_anio_en_ecas == max_anio_registro:
            continue
        
        anio_primer_fuga = max_anio_en_ecas + 1
        
        retorno_detectado = False
        for anio_posterior in range(anio_primer_fuga + 1, max_anio_registro + 1):
            if (mrun, anio_posterior) in matrículas_ecas:
                retorno_detectado = True
                break
        if retorno_detectado:
            continue
        
        fugas_detectadas_supuestas.append({
            'mrun': mrun, 
            'cohorte': cohorte, 
            'anio_fuga': anio_primer_fuga
        })
    
    df_fugas_supuestas = pd.DataFrame(fugas_detectadas_supuestas)

    if df_fugas_supuestas.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    mruns_fuga = df_fugas_supuestas['mrun'].apply(lambda x: int(x)).tolist()
    
    # 3. CONSULTA DE TRAYECTORIA Y CREACIÓN DE TABLA TEMPORAL
    
    df_mruns_temp = pd.DataFrame(mruns_fuga, columns=['mrun_fuga'])
    df_mruns_temp.to_sql('#TempMrunsFuga', db_conn, if_exists='replace', index=False, chunksize=1000)

    sql_trayectoria = f"""
    SELECT 
        t1.mrun,
        t1.cat_periodo AS anio_matricula_destino,
        t1.nomb_inst AS institucion_destino,
        t1.nomb_carrera AS carrera_destino,
        t1.area_conocimiento AS area_conocimiento_destino,
        t1.cod_inst,
        t1.dur_total_carr as duracion_total_carrera
    FROM vista_matricula_unificada t1
    INNER JOIN #TempMrunsFuga tm ON t1.mrun = tm.mrun_fuga
    ORDER BY t1.mrun, t1.cat_periodo;
    """
    
    df_trayectoria = pd.read_sql(sql_trayectoria, db_conn)
    
    
    # Merge para obtener la jornada de ECAS y el nombre de la carrera de origen
    df_jornada_origen = df_ecas_cohortes.groupby('mrun').agg(
    jornada=('jornada', 'first'),
    # No es necesario tomar 'cohorte' aquí si ya viene en df_fugas_supuestas,
    # pero sí debemos tomar la jornada de la cohorte original.
    cohorte_origen=('cohorte', 'first') 
    ).reset_index()

    df_fuga_base = pd.merge(
    df_fugas_supuestas, 
    df_jornada_origen[['mrun', 'jornada']], # Solo necesitamos la jornada
    on='mrun', 
    how='left'
    )

    df_fuga_base['duracion_nominal_ecas_años'] = df_fuga_base.apply(
    calcular_duracion_nominal_ecas, 
    axis=1
    )
    
    # Calcular el número de AÑOS ÚNICOS que el estudiante estuvo matriculado en ECAS
    años_matriculados_ecas = df_ecas_cohortes.groupby('mrun')['cat_periodo'].nunique().reset_index()
    años_matriculados_ecas.rename(columns={'cat_periodo': 'años_matriculados_ecas'}, inplace=True)
    
    df_fuga_base = pd.merge(df_fuga_base, años_matriculados_ecas, on='mrun', how='left')
    
    # Clasificación de Egresados
    df_egresados = df_fuga_base[
        (df_fuga_base['años_matriculados_ecas'] >= df_fuga_base['duracion_nominal_ecas_años']) & 
        (df_fuga_base['duracion_nominal_ecas_años'] > 0)
    ]
    
    mruns_egresados = df_egresados['mrun'].tolist()
    
    # Filtrar solo los desertores
    df_fugas_final_meta = df_fuga_base[~df_fuga_base['mrun'].isin(mruns_egresados)].copy()
    mruns_solo_desertores = df_fugas_final_meta['mrun'].tolist()

    if df_fugas_final_meta.empty:
        print("Todos los estudiantes fueron clasificados como Egresados o no hubo fugas.")
        return pd.DataFrame(), pd.DataFrame()
    
    # 5. CONTINUACIÓN: Filtrar trayectorias solo para los desertores

    df_fugas_matriculas = df_trayectoria[df_trayectoria['mrun'].isin(mruns_solo_desertores)].copy()

    df_fugas_final = pd.merge(
        df_fugas_matriculas, 
        df_fugas_final_meta[['mrun', 'cohorte', 'anio_fuga']], 
        on='mrun', 
        how='left'
    )
    print(df_fugas_final.head())

    # 6. Clasificación Fuga a Destino vs Abandono Total
    
    df_destino = df_fugas_final[
        (df_fugas_final['anio_matricula_destino'] >= df_fugas_final['anio_fuga']) &
        (df_fugas_final['cod_inst'] != 104)
    ].copy()
    
    df_destino.drop_duplicates(subset=['mrun', 'anio_matricula_destino', 'institucion_destino', 'carrera_destino'], inplace=True)
    
    # Clasificar Abandono Total (Fugas sin destino posterior)
    mruns_con_destino = df_destino['mrun'].unique()
    mruns_desertores_base = df_fugas_final_meta['mrun'].unique() # Usamos la base de desertores (sin egresados)
    mruns_abandono_total = [mrun for mrun in mruns_desertores_base if mrun not in mruns_con_destino]
    
    # Creamos df_abandono_total a partir de la meta data
    df_abandono_total = df_fugas_final_meta[df_fugas_final_meta['mrun'].isin(mruns_abandono_total)].copy()
    df_abandono_total = df_abandono_total[['mrun', 'cohorte', 'anio_fuga']]
    df_abandono_total.rename(columns={'cohorte': 'año_cohorte_ecas', 'anio_fuga': 'año_primer_fuga'}, inplace=True)
    
    # 7. Generar el DataFrame de Fuga a Destino Agrupado
    df_destino_agrupado = agrupar_trayectoria_por_carrera(df_destino, df_fugas_final_meta) 
    
    # 8. Limpieza de la tabla temporal
    try:
        db_conn.execute("DROP TABLE #TempMrunsFuga;")
    except Exception:
        pass 
        
    return df_destino_agrupado, df_abandono_total

def exportar_fuga_a_excel(df_destino_agrupado, df_abandono_total, anio_n):
    # Exporta los DataFrames de Fuga a Destino y Abandono Total a archivos Excel separados
    if not df_destino_agrupado.empty:
        nombre_archivo_destino = f"fuga_a_destino_cohorte_{anio_n}.xlsx" if anio_n is not None else "fuga_a_destino_todas_cohortes.xlsx"
        try:
            df_destino_agrupado.to_excel(nombre_archivo_destino, index=False)
            print(f"\n✅ Datos de Fuga a Destino guardados en '{nombre_archivo_destino}'.")
        except Exception as e:
            print(f"\n❌ Error al guardar el archivo de Fuga a Destino: {e}")
            
    # 2. Exportar Abandono Total
    if not df_abandono_total.empty:
        nombre_archivo_abandono = f"abandono_total_cohorte_{anio_n}.xlsx" if anio_n is not None else "abandono_total_todas_cohortes.xlsx"
        try:
            df_abandono_total.to_excel(nombre_archivo_abandono, index=False)
            print(f"\n✅ Datos de Abandono Total guardados en '{nombre_archivo_abandono}'.")
        except Exception as e:
            print(f"\n❌ Error al guardar el archivo de Abandono Total: {e}")
            
    if df_destino_agrupado.empty and df_abandono_total.empty:
        print("No se generaron archivos de salida.")

#df_fuga_destino, df_abandono = get_fuga_multianual_trayectoria(db_conn, anio_n=None)
#exportar_fuga_a_excel(df_fuga_destino, df_abandono, anio_n=None)