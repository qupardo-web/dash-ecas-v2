def obtener_detalles_ruta_titulados(cohorte_n: Optional[int] = None) -> pd.DataFrame:
    """
    Función auxiliar que retorna un DataFrame con 'mrun' y su 'ruta_secuencial' completa.
    Esto permite filtrar a los estudiantes específicos.
    """
    
    # 1. Leer datos y pre-filtrar
    df = pd.read_excel(FILE_PATH, sheet_name='Trayectoria_Detallada')
    df = df[['mrun', 'cohorte', 'nivel_global', 'anio_matricula_destino']].dropna()

    if cohorte_n is not None:
        df['cohorte'] = pd.to_numeric(df['cohorte'], errors='coerce')
        df = df[df['cohorte'] == cohorte_n].copy()
    
    # 2. Asignar ranking de nivel y ordenar
    df['nivel_rank'] = df['nivel_global'].map(orden_nivel)
    df['anio_matricula_destino'] = pd.to_numeric(df['anio_matricula_destino'], errors='coerce')
    df = df.dropna(subset=['anio_matricula_destino', 'nivel_rank'])
    
    # 3. CONSOLIDACIÓN DE NIVELES (Eliminar duplicados de nivel)
    df_unico_por_nivel = (
        df.sort_values(by=['mrun', 'anio_matricula_destino', 'nivel_rank'], ascending=[True, True, True])
          .drop_duplicates(subset=['mrun', 'nivel_global'], keep='first')
          .sort_values(by=['mrun', 'anio_matricula_destino'])
          .copy()
    )
    
    # 4. Crear la ruta secuencial única (niveles posteriores al Pregrado ECAS)
    df_rutas = (
        df_unico_por_nivel.groupby('mrun')
        .agg(
            niveles_posteriores=('nivel_global', lambda x: ' → '.join(x.tolist()))
        )
        .reset_index()
    )
    
    # 5. Añadir el nivel de titulación de ECAS ("Pregrado") al inicio
    df_rutas['ruta_secuencial'] = df_rutas['niveles_posteriores'].apply(
        lambda x: 'Pregrado' if x == '' else 'Pregrado → ' + x
    )
    
    # Retornamos el DataFrame con la ruta individual
    return df_rutas


def obtener_mruns_por_ruta(ruta_buscada: str, cohorte_n: Optional[int] = None) -> pd.DataFrame:
    """
    Busca y retorna los MRUN de los estudiantes que siguieron una ruta específica.
    """
    # 1. Obtener el DataFrame con la ruta secuencial de cada estudiante
    df_detalles = obtener_detalles_ruta_titulados(cohorte_n=cohorte_n)
    
    # 2. Filtrar por la ruta específica solicitada
    df_mruns = df_detalles[df_detalles['ruta_secuencial'] == ruta_buscada]
    
    # Opcional: Si quieres ver solo la lista de MRUNs
    return df_mruns[['mrun', 'ruta_secuencial']]

# --- Ejecución para encontrar los MRUNs específicos ---

RUTA_SOLICITADA = 'Pregrado → Postgrado → Pregrado → Postítulo'

# Buscamos los estudiantes (puedes especificar una cohorte aquí si lo deseas)
mruns_encontrados = obtener_mruns_por_ruta(RUTA_SOLICITADA)

print(f"--- Estudiantes con la ruta: {RUTA_SOLICITADA} ---")
if not mruns_encontrados.empty:
    print(f"Se encontraron {len(mruns_encontrados)} estudiantes con esta trayectoria.")
    print(mruns_encontrados)
else:
    print("No se encontraron estudiantes con esa trayectoria en la base de datos.")
