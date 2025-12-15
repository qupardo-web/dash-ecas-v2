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

def create_unified_view(nombre, consulta_tablas):
    """Crea o reemplaza la vista unificada."""
    engine = get_db_engine()
    if not engine:
        return False, "Error de conexión a la DB."
        
    table_names = get_table_names(engine, nombre)
    if not table_names:
        return False, "No se encontraron tablas en la DB. ¡Asegúrate de ejecutar carga_csv.py primero!"

    #Query para dropear la vista unificada si ya existe
    drop_query = f"""
    IF OBJECT_ID('dbo.vista_{nombre}_unificada', 'V') IS NOT NULL
        DROP VIEW dbo.vista_{nombre}_unificada;
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
    CREATE VIEW dbo.vista_{nombre}_unificada AS
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
            
            return True, f"Vista 'vista_{nombre}_unificada' creada/actualizada con {len(table_names)} tablas."
            
    except Exception as e:
        return False, f"ERROR al crear la vista SQL: {e}"

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
            id
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
            sem_ing_carr_ori,
            anio_ing_carr_act,
            sem_ing_carr_act
            """

success, message = create_unified_view("matricula", consulta_matricula)
print(message)

success, message = create_unified_view("titulados", consulta_titulados)
print(message)