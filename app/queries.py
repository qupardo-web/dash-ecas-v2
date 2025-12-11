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
    #los registros de ECAS. ej: Estudia el 2012, se sale. El 2013 ya no aparece. Ese es su primer año

    if df_destino.empty:
        # Si no hay destinos, se retorna la base de fugas con listas vacías
        df_base['anio_ingreso_destino'] = [[]] * len(df_base)
        df_base['anio_ultimo_matricula'] = [[]] * len(df_base)
        df_base['institucion_destino'] = [[]] * len(df_base)
        df_base['carrera_destino'] = [[]] * len(df_base)
        df_base['area_conocimiento_destino'] = [[]] * len(df_base)
        df_base['duracion_total_carrera'] = [[]] * len(df_base)
        return df_base


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
        how='left' 
    )

    # 5. Rellenar los NaN (para los desertores sin trayectoria posterior) con listas vacías
    columnas_lista = ['anio_ingreso_destino', 'anio_ultimo_matricula', 'institucion_destino', 'carrera_destino', 'area_conocimiento_destino']
    for col in columnas_lista:
        df_salida[col] = df_salida[col].apply(lambda x: x if isinstance(x, list) else [])

    return df_salida

def get_fuga_multianual_trayectoria(db_conn, anio_n=None):
    
    # 1. PREPARACIÓN DEL FILTRO DE COHORTE
    # Este filtro se aplicará en la subconsulta de cohortes_iniciales
    filtro_cohorte = f"AND anio_ing_carr_ori = {anio_n}" if isinstance(anio_n, int) else ""

    # 2. PRIMERA CONSULTA: IDENTIFICAR TODOS LOS ESTUDIANTES DE ECAS DE LA COHORTE
    # Usamos la consulta base para identificar todos los estudiantes y sus matrículas
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
    
    # Creamos un DataFrame para registrar la deserción de cada estudiante en cada año
    df_fugas = pd.DataFrame(columns=['mrun', 'cohorte', 'anio_fuga'])
    
    # Convertir las matrículas de ECAS a un formato fácil de consultar (set de tuplas (mrun, anio))
    matrículas_ecas = set(df_ecas_cohortes[['mrun', 'cat_periodo']].apply(tuple, axis=1))

    fugas_detectadas = []

    for index, row in cohortes_iniciales.iterrows():
        mrun = row['mrun']
        cohorte = row['cohorte']

        cohorte = int(cohorte)
        
        # Iterar desde el año siguiente a la cohorte hasta el último año disponible
        for anio_actual in range(cohorte + 1, max_anio_registro + 1):
            
            # Verificar si el estudiante no se matriculó en ECAS en el año actual
            if (mrun, anio_actual) not in matrículas_ecas:
                if mrun == 12360:
                    print(f"Fuga detectada para MRUN {mrun} en el año {anio_actual}")
                
                # Buscamos si ya tiene una fuga registrada
                ya_fuga = any(f['mrun'] == mrun for f in fugas_detectadas)

                if not ya_fuga:
                    # Encontramos el primer año de deserción
                    fugas_detectadas.append({
                        'mrun': mrun, 
                        'cohorte': cohorte, 
                        'anio_fuga': anio_actual
                    })
                
                # Como ya desertó, pasamos al siguiente estudiante (no necesitamos revisar años posteriores para este mrun)
                break 
    
    df_fugas = pd.DataFrame(fugas_detectadas)

    if df_fugas.empty:
        print("Todos los estudiantes de la cohorte especificada continuaron hasta el último año de registro.")
        return pd.DataFrame()
        
    # Obtener la lista de MRUNs de los desertores
    mruns_fuga = df_fugas['mrun'].apply(lambda x: int(x)).tolist()
    df_mruns_temp = pd.DataFrame(mruns_fuga, columns=['mrun_fuga'])
    
    # 4.1. Crear y Llenar la tabla temporal en la base de datos
    # Usaremos una tabla temporal global (##Temp) o local (#Temp) para SQL Server/ODBC. 
    # Usar #Temp es más seguro. El parámetro 'name' en to_sql debe ser '#TempTable'
    # El if_exists='replace' asegura que empezamos con una tabla limpia.
    df_mruns_temp.to_sql(
            '#TempMrunsFuga', 
            db_conn, 
            if_exists='replace', 
            index=False,
            chunksize = 1000
        )

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
    
    # 5. PROCESAR Y ESTRUCTURAR LA INFORMACIÓN PARA EL EXCEL FINAL
    
    # Unir la información de la fuga con la trayectoria
    df_trayectoria_completa = pd.merge(df_trayectoria, df_fugas[['mrun', 'anio_fuga']], on='mrun', how='left')

    # Limitar la trayectoria a matrículas posteriores al año de fuga y que no sean ECAS
    # Se debe buscar la trayectoria en el año de fuga o posterior, y en instituciones distintas a ECAS (104)
    df_destino = df_trayectoria_completa[
        (df_trayectoria_completa['anio_matricula_destino'] >= df_trayectoria_completa['anio_fuga']) &
        (df_trayectoria_completa['cod_inst'] != 104)
    ].copy()
    
    df_destino.drop_duplicates(subset=['mrun', 'anio_matricula_destino', 'institucion_destino', 'carrera_destino'], inplace=True)

    # 6. CREAR EL DATAFRAME FINAL PARA EXCEL
    
    df_final = agrupar_trayectoria_por_carrera(df_destino, df_fugas)
    
    # Reordenar las columnas para el formato final deseado
    column_order = [
        'mrun', 'año_cohorte_ecas', 'año_primer_fuga', 
        'anio_ingreso_destino', 'anio_ultimo_matricula',
        'institucion_destino', 'carrera_destino', 'area_conocimiento_destino', 
        'duracion_total_carrera'
    ]
    
    # Asegurarse de que solo existen las columnas deseadas
    df_final = df_final[[col for col in column_order if col in df_final.columns]]
    
    # Renombrar la columna del año de inicio/fin según la solicitud del usuario
    df_final.rename(columns={'anio_ingreso_destino': 'año_ingreso_destino', 
                             'anio_ultimo_matricula': 'año_ultimo_matricula'}, inplace=True)
    
    return df_final.reset_index(drop=True)


# --- EXPORTACIÓN A EXCEL (ADICIÓN SOLICITADA) ---

def exportar_fuga_a_excel(df, anio_n):
    """Guarda el DataFrame de fuga y trayectoria en un archivo Excel."""
    if df.empty:
        print("El DataFrame está vacío, no se generó ningún archivo Excel.")
        return

    # Definir el nombre del archivo
    if anio_n is not None:
        nombre_archivo = f"fuga_y_trayectoria_cohorte_{anio_n}.xlsx"
    else:
        nombre_archivo = "fuga_y_trayectoria_todas_cohortes.xlsx"

    try:
        # Exportar. Las listas se guardarán como texto dentro de las celdas.
        df.to_excel(nombre_archivo, index=False)
        print(f"\n✅ Datos de fuga y trayectoria guardados exitosamente en '{nombre_archivo}'.")
    except Exception as e:
        print(f"\n❌ Error al guardar el archivo Excel: {e}")

# # 3. Si quieres todas las cohortes:
df_fuga_todas = get_fuga_multianual_trayectoria(db_conn)
exportar_fuga_a_excel(df_fuga_todas, anio_n=None)

    

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

