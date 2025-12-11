import pandas as pd
from connector_db import get_db_engine
import numpy as np

COD_INST_ECAS = 104
DURACION_DIURNA_SEMESTRES = 8  # 4 años
DURACION_VESPERTINA_SEMESTRES = 9 # 4.5 años

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

def get permanencia_per_year(db_conn, anio_n = None):

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

def get_permanencia_primer_anio_per_year(db_conn, anio_n = None, cod_inst, nomb_carrera):

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

def get_continuidad_per_year(db_conn, anio_n=None):
    #Evalua la continuidad de los que ingresaron en primer año a la carrera
    #Esto permite 1. Saber en que año hay mayor abandono
    #             2. Saber que mruns abandonaron (es decir, cuales no completaron la carrera.)

def get_fuga_cohorte(db_conn, anio=n=None):
    #Evalua la fuga de los que ingresaron en primer año y luego abandonaron 
    #Para cambiarse de carrera

def get_fuga_ecas(db_conn, anio_n=None):
    #Evalua la fuga de mruns en un año x, comparando con su existencia en
    #el año posterior. Cual es su ultimo año en ECAS y su primer año en otra institución.
    #Es relevante saber la diferencia entre el primer año en esa institución y el ultimo
    #En ECAS. Esto nos permite poder calcular tasas de sabatico o años donde el estudiante
    #No estudio.

def get_institucion_fuga(db_conn, anio_n=None):
    #Evalua a que instituciones se fueron los estudiantes en cada año, es decir,
    #estudiantes que estuvieron cualquier otro año en ECAS y ahora vuelven a la educación
    #pero desde otra institución

def get_carrera_fuga(db_conn, anio_n=None):
    #Evalua la carrera a la que se fueron estos estudiantes

def get_area_fuga(db_conn, anio_n=None):
    #Evalua el area de conocimiento a la que se fueron estos estudiantes
    #luego de abandonar ECAS.

