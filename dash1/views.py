#Archivo para la creación de vistas, como la vista unificada.

from conn_db import get_db_engine
from sqlalchemy import text

#Metodo para obtener los nombres de las tablas que utilizaremos.
def get_table_names(engine, prefijo):
   
    query = f"""
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME LIKE '{prefijo}_[0-9]%'
    ORDER BY TABLE_NAME;
    """
    try:
        with engine.connect() as connection:

            result = connection.execute(text(query)).fetchall()

            return [row[0] for row in result]

    except Exception as e:
        print(f"ERROR al obtener nombres de tablas: {e}")
        return []

def create_unified_view(prefijo: str, consulta_tablas):
    """Crea o reemplaza la vista unificada."""
    engine = get_db_engine()
    if not engine:
        return False, "Error de conexión a la DB."
        
    table_names = get_table_names(engine, prefijo)
    if not table_names:
        return False, "No se encontraron tablas en la DB. ¡Asegúrate de ejecutar carga_csv.py primero!"

    view_name = f'''vista_{prefijo}_unificada'''

    #Query para dropear la vista unificada si ya existe
    drop_query = f"""
    IF OBJECT_ID('dbo.{view_name}', 'V') IS NOT NULL
        DROP VIEW dbo.{view_name};
    """
    
    # Construcción de la parte UNION ALL
    select_statements = []
    for table in table_names:
        select_statements.append(f"""SELECT
        {consulta_tablas}
        FROM dbo.{table}
        """)

    union_query = "\nUNION ALL\n".join(select_statements)

    create_view_query = f"""
    CREATE VIEW dbo.vista_{prefijo}_unificada AS
    {union_query};
    """

    try:
        with engine.connect() as connection:
            #Eliminar vista unificada
            connection.execute(text(drop_query)) 
            connection.commit()
            
            #Crear nueva vista unificada
            connection.execute(text(create_view_query))
            connection.commit()
            
            return True, f"Vista 'vista_{prefijo}_unificada' creada/actualizada con {len(table_names)} tablas."
            
    except Exception as e:
        return False, f"ERROR al crear la vista SQL: {e}"

#Vistas derivadas
def create_derived_view(view_name: str, select_sql: str):
    """
    Crea o reemplaza una vista derivada (sin UNION ALL)
    """
    engine = get_db_engine()
    if not engine:
        return False, "❌ Error de conexión a la DB."

    drop_query = f"""
    IF OBJECT_ID('dbo.{view_name}', 'V') IS NOT NULL
        DROP VIEW dbo.{view_name};
    """

    create_view_query = f"""
    CREATE VIEW dbo.{view_name} AS
    {select_sql};
    """

    try:
        with engine.connect() as connection:
            connection.execute(text(drop_query))
            connection.execute(text(create_view_query))
            connection.commit()

        return True, f"✅ Vista '{view_name}' creada correctamente."

    except Exception as e:
        return False, f"❌ ERROR al crear la vista '{view_name}': {e}"

#Bloque de ejecución

consulta_matricula = """ 
            CAST(cat_periodo AS INT) AS cat_periodo, 
            CAST(mrun AS BIGINT) AS mrun, 
            nomb_inst,
            area_conocimiento,
            codigo_unico,
            dur_total_carr,
            cod_inst,
            jornada, 
            dur_estudio_carr, 
            dur_proceso_tit,
            anio_ing_carr_ori,
            anio_ing_carr_act,
            cod_carrera,
            nomb_carrera,
            region_sede,
            tipo_inst_1,
            fec_nac_alu,
            gen_alu,
            rango_edad,
            id,
            nivel_global,
            nivel_carrera_1,
            nivel_carrera_2
            """

consulta_titulados= """ 
            CAST(cat_periodo AS INT) AS cat_periodo, 
            CAST(mrun AS BIGINT) AS mrun, 
            gen_alu, 
            rango_edad,
            anio_ing_carr_ori,
            nombre_titulo_obtenido,
            nombre_grado_obtenido,
            fecha_obtencion_titulo,
            tipo_inst_1,
            tipo_inst_2,
            tipo_inst_3,
            cod_inst,
            nomb_inst,
            nomb_carrera, 
            dur_total_carr,
            jornada,
            area_conocimiento,
            tipo_plan_carr,
            nivel_global,
            nivel_carrera_1,
            nivel_carrera_2,
            sem_ing_carr_ori,
            anio_ing_carr_act,
            sem_ing_carr_act
            """

sql_vista_titulados_limpia = """
SELECT
    CAST(cat_periodo AS INT) AS cat_periodo,
    CAST(mrun AS BIGINT) AS mrun,
    gen_alu,
    rango_edad,
    anio_ing_carr_ori,

    CASE
        WHEN nombre_titulo_obtenido IN (
            'TECNICO DE NIVEL SUPERIOR EN CONTABILIDAD',
            'CONTADOR TECNICO DE NIVEL SUPERIOR'
        )
        THEN 'CONTADOR TECNICO DE NIVEL SUPERIOR'

        WHEN nombre_titulo_obtenido IS NULL
             AND cod_inst = 104
        THEN 'CONTADOR AUDITOR'

        ELSE nombre_titulo_obtenido
    END AS nomb_titulo_obtenido,

    nombre_grado_obtenido,
    fecha_obtencion_titulo,

    tipo_inst_1,
    tipo_inst_2,
    tipo_inst_3,
    cod_inst,
    nomb_inst,
    nomb_carrera,
    dur_total_carr,
    jornada,
    area_conocimiento,
    tipo_plan_carr,
    nivel_global,
    nivel_carrera_1,
    nivel_carrera_2,
    sem_ing_carr_ori,
    anio_ing_carr_act,
    sem_ing_carr_act

FROM dbo.vista_titulados_unificada
WHERE fecha_obtencion_titulo IS NOT NULL
"""

success, message = create_unified_view("matricula", consulta_matricula)
print(message)

success, message = create_unified_view("titulados", consulta_titulados)
print(message)

successs, message = create_derived_view("vista_titulados_unificada_limpia", sql_vista_titulados_limpia)
print(message)