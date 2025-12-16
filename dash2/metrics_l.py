#Archivo para calcular metricas en base al excel de trayectoria post titulacion en ECAS.
import pandas as pd
from typing import Optional

FILE_PATH = 'trayectoria_post_ecas.xlsx'

orden_nivel = {
    'Pregrado': 1,
    'Postítulo': 2,
    'Postgrado': 3
}

#KPI 1: Nivel de reingreso a la educación superior
#Evalua si los estudiantes ingresan a un pregrado, postitulo o postgrado tras titularse en ECAS.
def calcular_nivel_reingreso(cohorte_n: int | None = None):

    df = pd.read_excel(FILE_PATH, sheet_name='Trayectoria_Detallada')
    df = df[['mrun', 'cohorte', 'nivel_global']].dropna()

    if cohorte_n is not None:
        df['cohorte'] = pd.to_numeric(df['cohorte'], errors='coerce')
        df = df[df['cohorte'] == cohorte_n]

    df['nivel_rank'] = df['nivel_global'].map(orden_nivel)

    df_max = (
        df.sort_values('nivel_rank')
          .groupby('mrun', as_index=False)
          .last()
    )

    total = len(df_max)

    conteo = (
        df_max.groupby('nivel_global')
        .size()
        .rename('cantidad')
        .reset_index()
    )

    conteo['total_reingresan'] = total
    conteo['porcentaje'] = (conteo['cantidad'] / total * 100).round(2)

    return conteo.sort_values('nivel_global')

# #KPI 2: Tipo de institución de reingreso
# #Evalua el tipo de institución a la que ingresan los estudiantes tras titularse en ECAS.
def calcular_tipo_institucion_reingreso(cohorte_n: int | None = None, tipo_seleccionado: str = 'tipo_inst_1'):

    df = pd.read_excel(FILE_PATH, sheet_name='Trayectoria_Detallada')

    df = df[['mrun', 'cohorte', 'nivel_global', tipo_seleccionado]].dropna()

    if cohorte_n is not None:
        df['cohorte'] = pd.to_numeric(df['cohorte'], errors='coerce')
        df = df[df['cohorte'] == cohorte_n]

    df['nivel_rank'] = df['nivel_global'].map(orden_nivel)

    df_max = (
        df.sort_values('nivel_rank')
          .groupby('mrun', as_index=False)
          .last()
    )

    total = len(df_max)

    conteo = (
        df_max.groupby(tipo_seleccionado)
        .size()
        .rename('cantidad')
        .reset_index()
    )

    conteo['total_reingresan'] = total
    conteo['porcentaje'] = (conteo['cantidad'] / total * 100).round(2)

    return conteo.sort_values('cantidad', ascending=False)

# #KPI 3: Áreas de conocimiento de reingreso
# #Evalua las áreas de conocimiento a las que ingresan los estudiantes tras titularse en ECAS.
def calcular_areas_conocimiento_reingreso(cohorte_n: int | None = None):

    df = pd.read_excel(FILE_PATH, sheet_name='Trayectoria_Detallada')
    df = df[['mrun', 'cohorte', 'nivel_global', 'area_conocimiento_destino']].dropna()

    if cohorte_n is not None:
        df['cohorte'] = pd.to_numeric(df['cohorte'], errors='coerce')
        df = df[df['cohorte'] == cohorte_n]

    df['nivel_rank'] = df['nivel_global'].map(orden_nivel)

    df_max = (
        df.sort_values('nivel_rank')
          .groupby('mrun', as_index=False)
          .last()
    )

    total = len(df_max)

    conteo = (
        df_max.groupby('area_conocimiento_destino')
        .size()
        .rename('cantidad')
        .reset_index()
    )

    conteo['total_reingresan'] = total
    conteo['porcentaje'] = (conteo['cantidad'] / total * 100).round(2)

    return conteo.sort_values('cantidad', ascending=False)

#KPI 4: Tiempo de demora en acceder a otra carrera tras titularse en ECAS,
#separado por nivel_global (pregrado, postitulo, postgrado).
def calcular_tiempo_demora_reingreso(cohorte_n: int | None = None):
    # Leer datos
    df = pd.read_excel(FILE_PATH, sheet_name='Trayectoria_Detallada')

    columnas = [
        'mrun', 'cohorte', 'nivel_global', 'anio_titulacion', 'anio_matricula_destino'
    ]
    df = df[columnas].dropna()

    # Filtrar por cohorte si se solicita
    if cohorte_n is not None:
        df['cohorte'] = pd.to_numeric(df['cohorte'], errors='coerce')
        df = df[df['cohorte'] == cohorte_n].copy()

    # Asegurar que los años son numéricos
    df['anio_titulacion'] = pd.to_numeric(df['anio_titulacion'], errors='coerce')
    df['anio_matricula_destino'] = pd.to_numeric(df['anio_matricula_destino'], errors='coerce')

    # Eliminar filas con NaN
    df = df.dropna(subset=['anio_titulacion', 'anio_matricula_destino'])

    # Solo considerar matrículas posteriores a la titulación
    df = df[df['anio_matricula_destino'] >= df['anio_titulacion']]

    # Eliminar duplicados por mrun (estudiantes) y quedarnos con la primera matrícula posterior
    df = df.sort_values(by='anio_matricula_destino')  # Ordenamos por año de matrícula (primero el más bajo)
    df = df.drop_duplicates(subset=['mrun'], keep='first')  # Mantenemos solo la primera matrícula posterior

    # Cálculo de la demora (diferencia entre año de matrícula y año de titulación)
    df['demora_anios'] = df['anio_matricula_destino'] - df['anio_titulacion']

    # Resumen por nivel_global
    resumen = (
        df.groupby('nivel_global')
          .agg(
              cantidad_casos=('demora_anios', 'count'),
              promedio_demora=('demora_anios', 'mean'),
              mediana_demora=('demora_anios', 'median'),
              min_demora=('demora_anios', 'min'),
              max_demora=('demora_anios', 'max')
          )
          .reset_index()
    )

    resumen[['promedio_demora', 'mediana_demora']] = resumen[
        ['promedio_demora', 'mediana_demora']
    ].round(2)

    return resumen.sort_values('nivel_global')

tiempo_demora = calcular_tiempo_demora_reingreso()
print(tiempo_demora)

#KPI5: En promedio, ¿Cómo se ve la ruta de los titulados de ECAS?
#Evaluamos los porcentajes de cuantos hacen un pregrado (titulacion) > postítulo > magister > doctorado. 
def calcular_ruta_promedio_titulados(cohorte_n: Optional[int] = None) -> pd.DataFrame:
    """
    KPI 5: Calcula la ruta académica secuencial única (eliminando matrículas repetidas dentro del mismo nivel)
    que toman los titulados de ECAS después de graduarse.
    """
    
    # 1. Leer datos y pre-filtrar
    df = pd.read_excel(FILE_PATH, sheet_name='Trayectoria_Detallada')
    df = df[['mrun', 'cohorte', 'nivel_global', 'anio_matricula_destino']].dropna()

    if cohorte_n is not None:
        df['cohorte'] = pd.to_numeric(df['cohorte'], errors='coerce')
        df = df[df['cohorte'] == cohorte_n].copy()
    
    # 2. Asignar ranking de nivel y ordenar
    df['nivel_rank'] = df['nivel_global'].map(orden_nivel)
    
    # Asegurar que los años de matrícula sean numéricos para ordenar correctamente
    df['anio_matricula_destino'] = pd.to_numeric(df['anio_matricula_destino'], errors='coerce')
    df = df.dropna(subset=['anio_matricula_destino', 'nivel_rank'])
    
    # 3. CONSOLIDACIÓN DE NIVELES: Obtener la primera matrícula para cada Nivel Global por MRUN
    # Ordenamos por año de matrícula destino (cronológico) y luego por rank (ascendente).
    # Si un estudiante cursa Postgrado en 2020 y 2021, queremos solo el de 2020.
    # Si cursa dos Postítulos, queremos el primero.
    df_unico_por_nivel = (
        df.sort_values(by=['mrun', 'anio_matricula_destino', 'nivel_rank'], ascending=[True, True, True])
          .drop_duplicates(subset=['mrun', 'nivel_global'], keep='first')
          .sort_values(by=['mrun', 'anio_matricula_destino']) # Reordenamos por tiempo para la secuencia
          .copy()
    )
    
    # 4. Crear la ruta secuencial única
    df_rutas = (
        df_unico_por_nivel.groupby('mrun')
        .agg(
            # Concatenamos los niveles posteriores al Pregrado de ECAS
            niveles_posteriores=('nivel_global', lambda x: ' → '.join(x.tolist()))
        )
        .reset_index()
    )
    
    # 5. Añadir el nivel de titulación de ECAS ("Pregrado") al inicio
    # Si la lista de niveles posteriores está vacía, la ruta es solo 'Pregrado'.
    df_rutas['ruta_secuencial'] = df_rutas['niveles_posteriores'].apply(
        lambda x: 'Pregrado' if x == '' else 'Pregrado → ' + x
    )
    
    # 6. Contar la frecuencia de cada ruta y calcular el porcentaje
    total_titulados = len(df_rutas)
    
    conteo_rutas = (
        df_rutas.groupby('ruta_secuencial')
        .size()
        .rename('cantidad')
        .reset_index()
    )
    
    conteo_rutas['total_titulados'] = total_titulados
    conteo_rutas['porcentaje'] = (conteo_rutas['cantidad'] / total_titulados * 100).round(2)
    
    return conteo_rutas.sort_values('cantidad', ascending=False)

rutas_promedio_df = calcular_ruta_promedio_titulados()

# 2. Definir el nombre y la ruta del archivo de salida
NOMBRE_ARCHIVO_SALIDA = 'KPI5_Ruta_Titulados_ECAS.xlsx'

# 3. Exportar el DataFrame a Excel
# Usamos index=False para no incluir el índice de Pandas en el archivo.
try:
    rutas_promedio_df.to_excel(NOMBRE_ARCHIVO_SALIDA, index=False)
    print(f"\n✅ Datos exportados con éxito a: {NOMBRE_ARCHIVO_SALIDA}")
    print("El archivo contiene el conteo y porcentaje de cada ruta secuencial.")
except Exception as e:
    print(f"\n❌ ERROR al exportar a Excel: {e}")
