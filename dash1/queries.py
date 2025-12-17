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
    AND nomb_carrera LIKE '%AUDITOR%'
    GROUP BY anio_ing_carr_ori
    ORDER BY ingreso_primero ASC
    """

    df_total_mruns = pd.read_sql(sql_query, db_conn)

    return df_total_mruns

def get_permanencia_per_year(db_conn, anio_n: Optional[int] = None) -> pd.DataFrame:
    
    # El filtro 'anio_n' se aplica a la cohorte
    filter_cohorte = f"AND T1.cohorte = {anio_n}" if isinstance(anio_n, int) else ""

    sql_query = f"""
        WITH base AS (
            SELECT 
                cat_periodo,
                mrun,
                CAST(anio_ing_carr_ori AS INT) AS cohorte 
            FROM vista_matricula_unificada
            WHERE mrun IS NOT NULL
            AND cod_inst = 104 -- Solo estudiantes matriculados en ECAS
            AND anio_ing_carr_ori IS NOT NULL
            AND anio_ing_carr_ori BETWEEN 2007 AND 2025
        ),
        matriculados_n AS (
            -- T1: Identifica a los estudiantes matriculados en su AÑO DE INGRESO (N)
            SELECT 
                mrun, 
                cohorte,
                cohorte AS anio_n,
                cohorte + 1 AS anio_n_plus_1
            FROM base
        )
        -- Consulta principal: Calcula la permanencia de N a N+1 para cada cohorte
        SELECT 
            T1.cohorte AS cohorte_ingreso,
            COUNT(DISTINCT T1.mrun) AS matriculados_base, -- Tamaño de la cohorte inicial
            COUNT(DISTINCT T2.mrun) AS retencion_conteo, -- Los que se matricularon en el año N+1
            
            -- Cálculo de la tasa de retención (permanencia N -> N+1)
            CAST(
                CAST(COUNT(DISTINCT T2.mrun) AS FLOAT) * 100 / 
                CAST(COUNT(DISTINCT T1.mrun) AS FLOAT) AS DECIMAL(5, 2)
            ) AS tasa_retencion_pct
            
        FROM matriculados_n AS T1
        
        LEFT JOIN base AS T2
            -- Condición 1: Mismo estudiante (mrun)
            ON T1.mrun = T2.mrun
            -- Condición 2: El estudiante aparece en la matrícula del AÑO SIGUIENTE (N+1)
            AND T2.cat_periodo = T1.anio_n_plus_1
        
        GROUP BY 
            T1.cohorte
            
        ORDER BY 
            T1.cohorte;
    """

    df_retencion_n1 = pd.read_sql(sql_query, db_conn)

    return df_retencion_n1

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
        vmu.mrun,
        vmu.cod_inst,
        vmu.nomb_inst,
        CAST(vmu.anio_ing_carr_ori AS INT) AS cohorte,
        vmu.cat_periodo,
        vmu.jornada
    FROM vista_matricula_unificada vmu
    WHERE vmu.mrun IS NOT NULL
      AND (
            (vmu.nomb_carrera LIKE '{CARRERA_LIKE}'
             AND vmu.dur_total_carr BETWEEN 8 AND 10
             AND vmu.region_sede = 'Metropolitana'
             AND vmu.tipo_inst_1 = 'Institutos Profesionales')
           OR vmu.cod_inst = {cod_ecas}
      )
      AND vmu.anio_ing_carr_ori BETWEEN 2007 AND 2025
    ),

    primer_registro AS (
        -- Primer año cronológico del estudiante en la institución
        SELECT
            mrun,
            cod_inst,
            cohorte,
            MIN(cat_periodo) AS primer_anio
        FROM base
        GROUP BY mrun, cod_inst, cohorte
    ),

    cohorte_origen AS (
        -- Asignar UNA jornada: la del primer registro
        SELECT
            b.mrun,
            b.cod_inst,
            b.nomb_inst,
            b.cohorte,
            b.jornada
        FROM primer_registro pr
        JOIN base b
        ON b.mrun = pr.mrun
        AND b.cod_inst = pr.cod_inst
        AND b.cohorte = pr.cohorte
        AND b.cat_periodo = pr.primer_anio
        WHERE b.jornada = '{jornada_sql}'
    ),

    matriculados_n1 AS (
        -- Matrícula en N+1 en la MISMA institución (cualquier jornada)
        SELECT DISTINCT
            mrun,
            cod_inst,
            cohorte
        FROM base
        WHERE cat_periodo = cohorte + 1
    )

    SELECT
        c.cohorte AS anio,
        c.nomb_inst,
        c.cod_inst,
        c.jornada,

        COUNT(DISTINCT c.mrun) AS total_estudiantes,

        COUNT(DISTINCT m.mrun) AS permanencia_conteo,

        CAST(
            COUNT(DISTINCT m.mrun) * 100.0 /
            COUNT(DISTINCT c.mrun)
            AS DECIMAL(5,2)
        ) AS tasa_permanencia_pct

    FROM cohorte_origen c
    LEFT JOIN matriculados_n1 m
        ON m.mrun = c.mrun
    AND m.cod_inst = c.cod_inst
    AND m.cohorte = c.cohorte

    GROUP BY
        c.cohorte,
        c.nomb_inst,
        c.cod_inst,
        c.jornada

    ORDER BY
        c.cohorte,
        tasa_permanencia_pct DESC;
    """

    df_all_data = pd.read_sql(sql_query, db_conn)
    
    # Aquí puedes añadir la lógica de Top 5 + ECAS por año (vista en la respuesta anterior)
    # Por simplicidad, esta función devolverá todos los datos por jornada, y el gráfico filtrará.
    return df_all_data


def get_continuidad_per_year(db_conn, anio_n=None):

    filtro_cohorte_sql = ""
    if isinstance(anio_n, int):
        # El filtro se aplicará al final, pero lo definimos aquí si lo queremos en SQL
        filtro_cohorte_sql = f"AND s.cohorte = {anio_n}"

    sql_query = f"""
    WITH base AS (
        SELECT DISTINCT
            mrun,
            cat_periodo,
            CAST(anio_ing_carr_ori AS INT) AS cohorte
        FROM vista_matricula_unificada
        WHERE mrun IS NOT NULL
          AND cod_inst = 104
          AND anio_ing_carr_ori IS NOT NULL
    ),

    cohortes AS (
        SELECT
            mrun,
            cohorte
        FROM base
        WHERE cat_periodo = cohorte
    ),

    base_cohorte AS (
        -- ... (Tu CTE existente para la base de la cohorte) ...
        SELECT
            b.mrun,
            b.cohorte,
            b.cat_periodo,
            b.cat_periodo - b.cohorte AS anio_rel
        FROM base b
        JOIN cohortes c
            ON b.mrun = c.mrun AND b.cohorte = c.cohorte
        WHERE b.cat_periodo >= b.cohorte
    ),

    supervivencia_individual AS (
        -- ... (Tu CTE existente para max_anio_rel) ...
        SELECT
            mrun,
            cohorte,
            MAX(anio_rel) AS max_anio_rel
        FROM (
            SELECT
                mrun, cohorte, anio_rel,
                COUNT(*) OVER (
                    PARTITION BY mrun, cohorte
                    ORDER BY anio_rel
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) - 1 AS secuencia
            FROM base_cohorte
        ) t
        WHERE anio_rel = secuencia
        GROUP BY mrun, cohorte
    ),

    titulacion AS (
        SELECT 
            t.mrun, 
            CAST(t.anio_ing_carr_ori AS INT) AS cohorte_ingreso,
            t.cat_periodo AS anio_titulacion,
            -- Calcula el año relativo de titulación
            t.cat_periodo - CAST(t.anio_ing_carr_ori AS INT) AS anio_rel_titulacion
        FROM vista_titulados_unificada t
        WHERE t.cod_inst = 104 -- Solo ECAS
        AND t.nombre_titulo_obtenido IS NOT NULL -- Solo titulados reales
        AND t.mrun IN (SELECT mrun FROM cohortes) -- Solo alumnos de la cohorte matriculada
    ),

    titulados_por_anio AS (
    SELECT
        cohorte_ingreso AS cohorte,
        anio_rel_titulacion AS anio_rel,
        COUNT(DISTINCT mrun) AS titulados_anio
    FROM titulacion
    GROUP BY
        cohorte_ingreso,
        anio_rel_titulacion
    ),

    scaffold AS (
        SELECT DISTINCT
            cohorte,
            anio_rel
        FROM base_cohorte
    ),

    cohorte_totales AS (
        SELECT
            cohorte,
            COUNT(DISTINCT mrun) AS total_ingreso
        FROM cohortes
        GROUP BY cohorte
    )

    SELECT
    s.cohorte,
    s.anio_rel + 1 AS anio_relativo,
    s.cohorte + s.anio_rel AS anio_real,
    
    -- Supervivencia
    COUNT(DISTINCT si.mrun) AS estudiantes_sobreviven,
    CAST(COUNT(DISTINCT si.mrun) AS FLOAT) / ct.total_ingreso AS tasa_supervivencia,
    
    -- Titulación acumulada (VENTANA SOBRE AGREGADOS)
    SUM(COALESCE(tpa.titulados_anio, 0)) OVER (
        PARTITION BY s.cohorte
        ORDER BY s.anio_rel
        ROWS UNBOUNDED PRECEDING
    ) AS titulados_acumulados,
    
    -- Tasa titulación acumulada
    CAST(
        SUM(COALESCE(tpa.titulados_anio, 0)) OVER (
            PARTITION BY s.cohorte
            ORDER BY s.anio_rel
            ROWS UNBOUNDED PRECEDING
        ) AS FLOAT
    ) / ct.total_ingreso AS tasa_titulacion_acumulada

    FROM scaffold s
    JOIN cohorte_totales ct 
        ON ct.cohorte = s.cohorte

    LEFT JOIN supervivencia_individual si 
        ON si.cohorte = s.cohorte 
    AND si.max_anio_rel >= s.anio_rel

    LEFT JOIN titulados_por_anio tpa
        ON tpa.cohorte = s.cohorte
    AND tpa.anio_rel = s.anio_rel

    WHERE s.anio_rel >= 0 {filtro_cohorte_sql}

    GROUP BY
        s.cohorte,
        s.anio_rel,
        ct.total_ingreso,
        tpa.titulados_anio

    ORDER BY
        s.cohorte,
        s.anio_rel;
    """

    # Ejecutar
    df = pd.read_sql(sql_query, db_conn)

    return df

def agrupar_trayectoria_por_carrera(df_destino, df_fugas):

    # 1. Base de metadata de fuga
    df_base = df_fugas[['mrun', 'cohorte', 'anio_fuga', 'jornada']].drop_duplicates()
    df_base.rename(
        columns={
            'cohorte': 'año_cohorte_ecas',
            'anio_fuga': 'año_primer_fuga'
        },
        inplace=True
    )

    # 2. Reconstruir ingreso y último año por carrera / institución
    df_por_carrera = (
        df_destino
        .groupby(
            ['mrun', 'institucion_destino', 'carrera_destino'],
            as_index=False
        )
        .agg(
            anio_ingreso_destino=('anio_matricula_destino', 'min'),
            anio_ultimo_matricula=('anio_matricula_destino', 'max'),
            area_conocimiento_destino=('area_conocimiento_destino', 'first'),
            duracion_total_carrera=('duracion_total_carrera', 'first'),
            nivel_global=('nivel_global', 'first'),
            nivel_carrera_1=('nivel_carrera_1', 'first'),
            nivel_carrera_2=('nivel_carrera_2', 'first'),
            tipo_inst_1=('tipo_inst_1', 'first'),
            tipo_inst_2=('tipo_inst_2', 'first'),
            tipo_inst_3=('tipo_inst_3', 'first'),
            requisito_ingreso=('requisito_ingreso', 'first')
        )
    )

    # 3. Orden cronológico real de la trayectoria
    df_por_carrera = df_por_carrera.sort_values(
        by=['mrun', 'anio_ingreso_destino']
    )

    # 4. Columnas a serializar
    columnas_trayectoria = [
        'anio_ingreso_destino',
        'anio_ultimo_matricula',
        'institucion_destino',
        'carrera_destino',
        'area_conocimiento_destino',
        'duracion_total_carrera',
        'nivel_global',
        'nivel_carrera_1',
        'nivel_carrera_2',
        'tipo_inst_1',
        'tipo_inst_2',
        'tipo_inst_3',
        'requisito_ingreso'
    ]

    def serializar(col):
        return ' | '.join(col.astype(str))

    # 5. Serializar trayectoria por MRUN
    df_trayectoria = (
        df_por_carrera
        .groupby('mrun')
        .agg({col: serializar for col in columnas_trayectoria})
        .reset_index()
    )

    # 6. Merge final
    df_salida = pd.merge(
        df_base,
        df_trayectoria,
        on='mrun',
        how='inner'
    )

    return df_salida

def get_fuga_multianual_trayectoria(db_conn, anio_n: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    
    filtro_cohorte = f"AND anio_ing_carr_ori = {anio_n}" if isinstance(anio_n, int) else ""

    # 1. Identificación de estudiantes en ECAS
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
    AND anio_ing_carr_ori BETWEEN 2007 AND 2025
    {filtro_cohorte}
    ORDER BY mrun, cat_periodo;
    """
    
    df_ecas_cohortes = pd.read_sql(sql_base_ecas, db_conn)
    
    if df_ecas_cohortes.empty:
        print("No se encontraron datos de matrículas para la cohorte especificada en ECAS.")
        return pd.DataFrame(), pd.DataFrame()

    cohortes_iniciales = (
    df_ecas_cohortes
    .groupby('mrun', as_index=False)
    .agg(cohorte=('cohorte', 'min'))
    )
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

    # 2. Detección de Fugas Supuestas (basado en ausencia de matrícula y no retorno)
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
        print("No se detectaron fugas o todos se mantuvieron hasta el final del período registrado.")
        return pd.DataFrame(), pd.DataFrame()
        
    
    # 3. IDENTIFICAR TITULADOS (EGRESADOS) REALES USANDO VISTA UNIFICADA
    
    sql_titulados = """
    SELECT 
        DISTINCT mrun
    FROM vista_titulados_unificada_limpia
    WHERE mrun IS NOT NULL
      AND cod_inst = 104; -- Opcional: Filtrar solo titulados de ECAS si es relevante.
    """
    df_mruns_titulados = pd.read_sql(sql_titulados, db_conn)
    
    mruns_titulados = df_mruns_titulados['mrun'].tolist()
    
    # 4. CLASIFICACIÓN DE EGRESADOS/TITULADOS (Criterio simple y exacto)
    
    # Los egresados son todas las 'fugas supuestas' que tienen un registro de titulación.
    df_egresados = df_fugas_supuestas[
        df_fugas_supuestas['mrun'].isin(mruns_titulados)
    ].copy()
    
    mruns_egresados = df_egresados['mrun'].tolist()
    
    # Los Desertores son las fugas supuestas que NO son titulados.
    df_fugas_final_meta = df_fugas_supuestas[~df_fugas_supuestas['mrun'].isin(mruns_egresados)].copy()
    mruns_solo_desertores = df_fugas_final_meta['mrun'].tolist()

    if df_fugas_final_meta.empty:
        print("Todos los estudiantes que dejaron la institución fueron clasificados como Egresados/Titulados.")
        return pd.DataFrame(), pd.DataFrame() 
    
    # 5. Obtener jornada y merge (Necesario para la función agrupar_trayectoria_por_carrera)
    df_jornada_origen = df_ecas_cohortes.groupby('mrun').agg(
        jornada=('jornada', 'first')
    ).reset_index()

    df_fugas_final_meta = pd.merge(
        df_fugas_final_meta, 
        df_jornada_origen[['mrun', 'jornada']], 
        on='mrun', 
        how='left'
    )
    
    # 6. CONSULTA DE TRAYECTORIA Y CREACIÓN DE TABLA TEMPORAL (Solo para los desertores)
    
    df_mruns_temp = pd.DataFrame(mruns_solo_desertores, columns=['mrun_fuga'])
    df_mruns_temp.to_sql('#TempMrunsFuga', db_conn, if_exists='replace', index=False, chunksize=1000)

    sql_trayectoria = f"""
    SELECT 
        t1.mrun,
        t1.cat_periodo AS anio_matricula_destino,
        t1.nomb_inst AS institucion_destino,
        t1.nomb_carrera AS carrera_destino,
        t1.area_conocimiento AS area_conocimiento_destino,
        t1.cod_inst,
        t1.dur_total_carr as duracion_total_carrera,
        t1.nivel_global,
        t1.nivel_carrera_1,
        t1.nivel_carrera_2,
        t1.tipo_inst_1,
        t1.tipo_inst_2,
        t1.tipo_inst_3,
        t1.requisito_ingreso
    FROM vista_matricula_unificada t1
    INNER JOIN #TempMrunsFuga tm ON t1.mrun = tm.mrun_fuga
    ORDER BY t1.mrun, t1.cat_periodo;
    """
    df_trayectoria = pd.read_sql(sql_trayectoria, db_conn)
    
    # 7. Unir las trayectorias con la metadata de fuga
    df_fugas_matriculas = df_trayectoria[df_trayectoria['mrun'].isin(mruns_solo_desertores)].copy()
    
    df_fugas_final = pd.merge(
        df_fugas_matriculas, 
        df_fugas_final_meta[['mrun', 'cohorte', 'anio_fuga', 'jornada']], 
        on='mrun', 
        how='left'
    )
    
    # 8. Clasificación Fuga a Destino vs Abandono Total
    
    df_destino = df_fugas_final[
        (df_fugas_final['anio_matricula_destino'] >= df_fugas_final['anio_fuga']) &
        (df_fugas_final['cod_inst'] != 104)
    ].copy()
    
    df_destino.drop_duplicates(subset=['mrun', 'anio_matricula_destino', 'institucion_destino', 'carrera_destino'], inplace=True)
    
    # Clasificar Abandono Total (Fugas sin destino posterior)
    mruns_con_destino = df_destino['mrun'].unique()
    mruns_desertores_base = df_fugas_final_meta['mrun'].unique()
    mruns_abandono_total = [mrun for mrun in mruns_desertores_base if mrun not in mruns_con_destino]
    
    df_abandono_total = df_fugas_final_meta[df_fugas_final_meta['mrun'].isin(mruns_abandono_total)].copy()
    df_abandono_total = df_abandono_total[['mrun', 'cohorte', 'anio_fuga']]
    df_abandono_total.rename(columns={'cohorte': 'año_cohorte_ecas', 'anio_fuga': 'año_primer_fuga'}, inplace=True)
    
    # 9. Generar el DataFrame de Fuga a Destino Agrupado
    # Importante: Aquí se pasa df_fugas_final_meta, que solo contiene desertores
    df_destino_agrupado = agrupar_trayectoria_por_carrera(df_destino, df_fugas_final_meta) 
    
    # 10. Limpieza de la tabla temporal
    try:
        db_conn.execute("DROP TABLE #TempMrunsFuga;")
    except Exception:
        pass 

    return df_destino_agrupado, df_abandono_total

#KPI: Titulados en ECAS que vienen desde otra institucion
#Evaluar la cantidad de estudiantes por cohorte (ingreso) que entran a ECAS luego de dejar otra institución,
#y se titulan exitosamente. Se debe evaluar la trayectoria del estudiantes antes de anio_ing_carr_ori en ECAS 
#y ver si se titularon luego en ECAS. Se podria tomar como población total todos los estudiantes que vienen de otra institución
#hacia ECAS, y calcular el porcentaje de titulados vs no titulados
def titulados_en_ecas_desde_otra_institucion(db_conn, anio_n: Optional[int] = None):

    filtro_cohorte = ""
    if isinstance(anio_n, int):
        filtro_cohorte = f"AND pb.cohorte_ecas = {anio_n}"

    sql_query = f"""
    WITH ingreso_ecas AS (
        SELECT DISTINCT
            mrun,
            CAST(anio_ing_carr_ori AS INT) AS cohorte_ecas
        FROM vista_matricula_unificada
        WHERE cod_inst = 104
          AND mrun IS NOT NULL
          AND anio_ing_carr_ori BETWEEN 2007 AND 2025
    ),

    trayectoria_previa AS (
        SELECT DISTINCT
            vmu.mrun
        FROM vista_matricula_unificada vmu
        JOIN ingreso_ecas ie
          ON vmu.mrun = ie.mrun
        WHERE vmu.cod_inst <> 104
          AND vmu.cat_periodo < ie.cohorte_ecas
    ),

    poblacion_base AS (
        SELECT
            ie.mrun,
            ie.cohorte_ecas
        FROM ingreso_ecas ie
        JOIN trayectoria_previa tp
          ON ie.mrun = tp.mrun
    ),

    titulados_ecas AS (
        SELECT DISTINCT
            mrun
        FROM vista_titulados_unificada
        WHERE cod_inst = 104
          AND nombre_titulo_obtenido IS NOT NULL
    )

    SELECT
        pb.cohorte_ecas,
        COUNT(DISTINCT pb.mrun) AS total_provenientes,
        COUNT(DISTINCT te.mrun) AS titulados_ecas,
        COUNT(DISTINCT pb.mrun) - COUNT(DISTINCT te.mrun) AS no_titulados_ecas,
        CAST(
            COUNT(DISTINCT te.mrun) * 100.0 /
            COUNT(DISTINCT pb.mrun)
            AS DECIMAL(5,2)
        ) AS tasa_titulacion_ecas
    FROM poblacion_base pb
    LEFT JOIN titulados_ecas te
      ON pb.mrun = te.mrun
    WHERE 1 = 1
    {filtro_cohorte}
    GROUP BY pb.cohorte_ecas
    ORDER BY pb.cohorte_ecas;
    """

    return pd.read_sql(sql_query, db_conn)

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

#df_destino, df_abandono = get_fuga_multianual_trayectoria(db_conn, anio_n=None)
#exportar_excel = exportar_fuga_a_excel(df_destino, df_abandono, anio_n=None)