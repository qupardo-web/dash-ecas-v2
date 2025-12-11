import pandas as pd
from conn_db import get_db_engine
import numpy as np
from collections import defaultdict
from collections import defaultdict

COD_INST_ECAS = 104
DURACION_DIURNA_SEMESTRES = 8  # 4 años
DURACION_VESPERTINA_SEMESTRES = 9 # 4.5 años

db_conn = get_db_engine()

def get_mruns_per_year(db_conn, anio_n = None):

    #Obtiene todos los mruns por año de ingreso

    filter_anio = ""

    if isinstance(anio_n, int): 
        filter_anio = f"AND T1.cat_periodo = {anio_n}"

    sql_query= f"""
    SELECT anio_ing_carr_ori AS ingreso_primero,
	COUNT(DISTINCT mrun) AS Total_Mruns
    FROM  vista_matriculas_unificada v
    WHERE cod_inst LIKE 104 
    AND anio_ing_carr_ori NOT IN (9999, 1900)
    {filter_anio}
    GROUP BY anio_ing_carr_ori
    ORDER BY ingreso_primero DESC
    """

    df_total_mruns = pd.read_sql(sql_query, db_conn)

    return df_total_mruns

def get_permanencia_per_year(db_conn, anio_n = None):

    #Evalua la tasa de permanencia de todos los estudiantes año a año

    filter_anio = ""

    if isinstance(anio_n, int):
        filter_anio = f"WHERE T1.cat_periodo = {anio_n}"

    sql_query = f"""
        WITH base AS (
            SELECT 
                cat_periodo,
                mrun
            FROM vista_matriculas_unificada
            WHERE mrun IS NOT NULL
        ),
        t1 AS (
            SELECT * 
            FROM base
            {filter_anio}
        ),
        t2 AS (
            SELECT *
            FROM base
        )
        SELECT 
            T1.cat_periodo AS anio,
            COUNT(DISTINCT T1.mrun) AS total_estudiantes,
            COUNT(DISTINCT T2.mrun) AS permanencia
        FROM t1
        LEFT JOIN t2
            ON T1.mrun = T2.mrun
            AND T1.cat_periodo + 1 = T2.cat_periodo
        GROUP BY T1.cat_periodo
        ORDER BY anio;
    """

    df_total_permanecia_estudiantes = pd.read_sql(sql_query, db_conn)

    return df_total_permanencia_estudiantes

def get_permanencia_primer_anio_per_year(db_conn, anio_n = None, cod_inst = None, nomb_carrera = None):

    #Metodo que obtiene la permanencia del primer año para diferentes instituciones
    #y carreras
    sql_query = f"""" WITH base AS (
    SELECT 
        cat_periodo,
        mrun,
        cod_inst,
        anio_ing_carr_ori,
        nomb_carrera
    FROM vista_matriculas_unificada
    WHERE mrun IS NOT NULL 
      AND cod_inst = {cod_inst} AND nomb_carrera = {nomb_carrera}
    ),
    primer_anio AS (
        SELECT 
            mrun,
            cat_periodo AS anio_ingreso
        FROM base
        WHERE cat_periodo = anio_ing_carr_ori
    )
    SELECT 
        p.anio_ingreso AS anio,
        COUNT(DISTINCT p.mrun) AS total_primer_ano,
        COUNT(DISTINCT b2.mrun) AS permanencia
    FROM primer_anio p
    LEFT JOIN base b2
        ON p.mrun = b2.mrun
    AND b2.cat_periodo = p.anio_ingreso + 1
    GROUP BY p.anio_ingreso
    ORDER BY anio;
    """

    df_total_permanencia_primer_anio = pd.read_sql(sql_query, db_conn)

    return df_total_permanencia_primer_anio

#Metodo para calcular continuidad año a año para los estudiantes de cierta
#cohorte. Permite evaluar:
#¿Cuántos estudiantes continúan después del 1er año?
#¿Dónde ocurre el mayor abandono? (ej: entre 1° y 2° año)
#¿Qué cohortes retuvieron mejor?
#¿La retención está subiendo o bajando en el tiempo?
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
        FROM vista_matriculas_unificada
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
    
    # 1. Prepara la base con la información de Fuga (MRUN, Cohorte ECAS y Año de Fuga)
    df_base = df_fugas[['mrun', 'cohorte', 'anio_fuga']].drop_duplicates()
    df_base.rename(columns={'cohorte': 'año_cohorte_ecas', 'anio_fuga': 'año_primer_fuga'}, inplace=True)
    #Año primer fuga corresponde al año en que el estudiante no aparece por primera vez en 
    #los registros de ECAS. ej: Estudia el 2012, se sale. El 2013 ya no aparece. Ese es su primer año de fuga.

    # 2. Agrupar el DataFrame de destino (df_destino) por la clave única de trayectoria
    # Nota: Ya no se intenta agregar la cohorte aquí, ya que no existe en df_destino
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

def get_fuga_multianual_trayectoria(db_conn, anio_n=None):
    
    filtro_cohorte = f"AND anio_ing_carr_ori = {anio_n}" if isinstance(anio_n, int) else ""

   #Identificacion de estudiantes en ECAS
    sql_base_ecas = f"""
    SELECT 
        mrun,
        cat_periodo,
        anio_ing_carr_ori AS cohorte,
        cod_inst
    FROM vista_matriculas_unificada
    WHERE mrun IS NOT NULL 
    AND cod_inst = 104  -- Filtrar solo por ECAS (código 104)
    {filtro_cohorte}
    ORDER BY mrun, cat_periodo;
    """
    
    df_ecas_cohortes = pd.read_sql(sql_base_ecas, db_conn)
    
    if df_ecas_cohortes.empty:
        print("No se encontraron datos de matrículas para la cohorte especificada en ECAS.")
        return pd.DataFrame()

    # Identificar la cohorte inicial de cada estudiante (que ya debería ser 'cohorte')
    cohortes_iniciales = df_ecas_cohortes[['mrun', 'cohorte']].drop_duplicates()
    
    cohortes_iniciales.dropna(subset=['cohorte'], inplace=True)
   
    if cohortes_iniciales.empty:
        print("Advertencia: No quedan cohortes válidas después de limpiar los valores nulos.")
        return pd.DataFrame()
    
    # Obtener el último año de registro en los datos para establecer el límite del loop
    max_anio_registro = df_ecas_cohortes['cat_periodo'].max()
    
    if pd.isna(max_anio_registro):
        # Si no hay datos, se podría establecer un valor de salida o lanzar una excepción
        print("Advertencia: max_anio_registro es NaN. Saliendo.")
        return pd.DataFrame() 
    
    max_anio_registro = int(max_anio_registro)
    
    # 3. DETECCIÓN DE FUGA MULTIANUAL (PROCESAMIENTO EN PYTHON)
    
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

        print(mrun, anio_primer_fuga, "FUGA DETECTADA (Definitiva)")
        
        fugas_detectadas_supuestas.append({
            'mrun': mrun, 
            'cohorte': cohorte, 
            'anio_fuga': anio_primer_fuga
        })
    
    df_fugas_supuestas = pd.DataFrame(fugas_detectadas_supuestas)

    if df_fugas_supuestas.empty:
        return pd.DataFrame()
        
    mruns_fuga = df_fugas_supuestas['mrun'].apply(lambda x: int(x)).tolist()
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
    FROM vista_matriculas_unificada t1
    INNER JOIN #TempMrunsFuga tm ON t1.mrun = tm.mrun_fuga
    ORDER BY t1.mrun, t1.cat_periodo;
    """
    
    df_trayectoria = pd.read_sql(sql_trayectoria, db_conn)
    
    #Logica de clasificación: Egresado vs Desertor

    df_fuga_base = pd.merge(df_fugas_supuestas, df_trayectoria.groupby('mrun')['duracion_total_carrera'].first().reset_index(), on='mrun', how='left')

    # Calcular el número de años que el estudiante estuvo matriculado en ECAS
    años_matriculados_ecas = df_ecas_cohortes.groupby('mrun')['cat_periodo'].count().reset_index()
    años_matriculados_ecas.rename(columns={'cat_periodo': 'años_matriculados_ecas'}, inplace=True)
    
    df_fuga_base = pd.merge(df_fuga_base, años_matriculados_ecas, on='mrun', how='left')

    df_fuga_base['duracion_total_carrera_años'] = np.ceil(
        df_fuga_base['duracion_total_carrera'] / 2.0
    )

    df_fuga_base['duracion_total_carrera_años'].fillna(0, inplace=True)

    df_egresados = df_fuga_base[
        (df_fuga_base['años_matriculados_ecas'] >= df_fuga_base['duracion_total_carrera_años']) & 
        (df_fuga_base['duracion_total_carrera_años'] > 0) # Asegurar que la duración es válida
    ]
    
    mruns_egresados = df_egresados['mrun'].tolist()
    
    df_fugas_final_meta = df_fugas_supuestas[~df_fugas_supuestas['mrun'].isin(mruns_egresados)].copy()
    mruns_solo_desertores = df_fugas_final_meta['mrun'].tolist()

    if df_fugas_final_meta.empty:
        print("Todos los estudiantes fueron clasificados como Egresados o no hubo fugas.")
        return pd.DataFrame(), pd.DataFrame()
    
    df_fugas_matriculas = df_trayectoria[df_trayectoria['mrun'].isin(mruns_solo_desertores)].copy()

    df_fugas_final = pd.merge(
        df_fugas_matriculas, 
        df_fugas_final_meta[['mrun', 'cohorte', 'anio_fuga']], 
        on='mrun', 
        how='left'
    )
    print(df_fugas_final.head())

    df_destino = df_fugas_final[
        (df_fugas_final['anio_matricula_destino'] >= df_fugas_final['anio_fuga']) &
        (df_fugas_final['cod_inst'] != 104)
    ].copy()
    
    df_destino.drop_duplicates(subset=['mrun', 'anio_matricula_destino', 'institucion_destino', 'carrera_destino'], inplace=True)
    
    # Clasificar Abandono Total (Fugas sin destino posterior)
    mruns_con_destino = df_destino['mrun'].unique()
    mruns_desertores = df_fugas_final['mrun'].unique()
    mruns_abandono_total = [mrun for mrun in mruns_desertores if mrun not in mruns_con_destino]
    
    df_abandono_total = df_fugas_final[df_fugas_final['mrun'].isin(mruns_abandono_total)].drop_duplicates(subset=['mrun'])
    df_abandono_total = df_abandono_total[['mrun', 'cohorte', 'anio_fuga']]
    df_abandono_total.rename(columns={'cohorte': 'año_cohorte_ecas', 'anio_fuga': 'año_primer_fuga'}, inplace=True)
    
    # Generar el DataFrame de Fuga a Destino (para el archivo principal)
    df_destino_agrupado = agrupar_trayectoria_por_carrera(df_destino, df_fugas_final)
    
    # Limpieza de la tabla temporal
    try:
        db_conn.execute("DROP TABLE #TempMrunsFuga;")
    except Exception:
        pass # No es crítico si falla
        
    # Retornar ambos resultados
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

df_fuga_destino, df_abandono = get_fuga_multianual_trayectoria(db_conn, anio_n=None)
exportar_fuga_a_excel(df_fuga_destino, df_abandono, anio_n=None)
    

# def get_fuga_ecas(db_conn, anio_n=None):
#     #Evalua la fuga de mruns en un año x, comparando con su existencia en
#     #el año posterior. Cual es su ultimo año en ECAS y su primer año en otra institución.
#     #Es relevante saber la diferencia entre el primer año en esa institución y el ultimo
#     #En ECAS. Esto nos permite poder calcular tasas de sabatico o años donde el estudiante
#     #No estudio.

# def get_institucion_fuga(db_conn, anio_n=None):
#     #Evalua a que instituciones se fueron los estudiantes en cada año, es decir,
#     #estudiantes que estuvieron cualquier otro año en ECAS y ahora vuelven a la educación
#     #pero desde otra institución

# def get_carrera_fuga(db_conn, anio_n=None):
#     #Evalua la carrera a la que se fueron estos estudiantes

# def get_area_fuga(db_conn, anio_n=None):
#     #Evalua el area de conocimiento a la que se fueron estos estudiantes
#     #luego de abandonar ECAS.

