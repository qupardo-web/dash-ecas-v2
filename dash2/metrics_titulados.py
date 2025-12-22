#Archivo para calcular metricas en base al excel de trayectoria post titulacion en ECAS.
import pandas as pd
from typing import Optional
from auxiliar import *

FILE_PATH = 'trayectoria_post_ecas.xlsx'

orden_nivel = {
    'Pregrado': 1,
    'Postítulo': 2,
    'Postgrado': 3
}

#KPI 1: Nivel de reingreso a la educación superior
#Evalua si los estudiantes ingresan a un pregrado, postitulo o postgrado tras titularse en ECAS.
#Solo evalua el maximo nivel alcanzado tras titulación en ECAS. 
def calcular_nivel_reingreso(cohorte_n: int | None = None, jornada: str | None = None):

    df = pd.read_excel(FILE_PATH, sheet_name="Trayectoria_Resumen")

    columnas = [
        "mrun",
        "año_cohorte_ecas",
        "año_titulacion_ecas",
        "anio_ingreso_destino",
        "nivel_global",
        "jornada"
    ]

    df = df[columnas].dropna(subset=["mrun", "año_titulacion_ecas"])

    if cohorte_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(df["año_cohorte_ecas"], errors="coerce")
        df = df[df["año_cohorte_ecas"] == cohorte_n]

    if jornada is not None:
        df = df[df["jornada"] == jornada]

    resultados = []

    for _, row in df.iterrows():

        anio_tit = row["año_titulacion_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])

        # Seguridad: listas paralelas
        eventos = zip(ingresos, niveles)

        # Solo eventos posteriores a ECAS
        niveles_post_ecas = [
            nivel
            for anio, nivel in eventos
            if anio.isdigit() and int(anio) > anio_tit
        ]

        if not niveles_post_ecas:
            continue

        # Nivel máximo alcanzado
        nivel_max = max(
            niveles_post_ecas,
            key=lambda n: orden_nivel.get(n, 0)
        )

        resultados.append({
            "mrun": row["mrun"],
            "nivel_global": nivel_max
        })

    df_max = pd.DataFrame(resultados)

    total = df_max["mrun"].nunique()

    conteo = (
        df_max.groupby("nivel_global")
        .size()
        .rename("cantidad")
        .reset_index()
    )

    conteo["total_reingresan"] = total
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(2)

    return conteo.sort_values("nivel_global")

#KPI1.1: Nivel inmediato de reingreso
#Evalua el nivel al que ingresan los estudiantes inmediatamente después de titularse en ECAS.
def calcular_nivel_reingreso_inmediato(cohorte_n: int | None = None, jornada: str | None = None):

    df = pd.read_excel(FILE_PATH, sheet_name="Trayectoria_Resumen")

    columnas = [
        "mrun",
        "año_cohorte_ecas",
        "año_titulacion_ecas",
        "anio_ingreso_destino",
        "nivel_global",
        "jornada"
    ]

    df = df[columnas].dropna(subset=["mrun", "año_titulacion_ecas"])

    if cohorte_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(df["año_cohorte_ecas"], errors="coerce")
        df = df[df["año_cohorte_ecas"] == cohorte_n]

    if jornada is not None:
        df = df[df["jornada"] == jornada]

    resultados = []

    for _, row in df.iterrows():
        anio_tit = row["año_titulacion_ecas"]
        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])

        eventos_post_ecas = [
            (int(anio), nivel)
            for anio, nivel in zip(ingresos, niveles)
            if anio.isdigit() and int(anio) > anio_tit
        ]

        if not eventos_post_ecas:
            continue

        anio_min, nivel_inmediato = min(eventos_post_ecas, key=lambda x: x[0])
        resultados.append({
            "mrun": row["mrun"],
            "nivel_global": nivel_inmediato
        })

    if not resultados:
        return pd.DataFrame(columns=["nivel_global", "cantidad", "total_reingresan", "porcentaje"])

    df_min = pd.DataFrame(resultados)

    total = df_min["mrun"].nunique()

    conteo = (
        df_min.groupby("nivel_global")
        .size()
        .rename("cantidad")
        .reset_index()
    )

    conteo["total_reingresan"] = total
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(2)

    return conteo.sort_values("nivel_global")

def calcular_top_reingreso_por_columna_titulados(
    columna_objetivo: str,
    cohorte_n: int | None = None,
    jornada: str | None = None,
    criterio: str = "max",  # "max" o "min"
    top_n: int | None = None
):
    """
    KPI genérica de reingreso post-ECAS.
    
    - columna_objetivo: columna a analizar (ej: 'tipo_institucion_1', 'area_conocimiento_destino')
    - cohorte_n: cohorte ECAS (opcional)
    - criterio:
        - 'max' → nivel máximo alcanzado
        - 'min' → nivel inmediato post-ECAS
    - top_n: limitar al top N (opcional)
    """

    df = pd.read_excel(FILE_PATH, sheet_name="Trayectoria_Resumen")

    columnas = [
        "mrun",
        "año_cohorte_ecas",
        "año_titulacion_ecas",
        "anio_ingreso_destino",
        "nivel_global",
        "jornada",
        columna_objetivo
    ]

    df = df[columnas].dropna(subset=["mrun", "año_titulacion_ecas"])

    if cohorte_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(df["año_cohorte_ecas"], errors="coerce")
        df = df[df["año_cohorte_ecas"] == cohorte_n]

    if jornada is not None:
        df = df[df["jornada"] == jornada]

    resultados = []

    for _, row in df.iterrows():

        anio_tit = row["año_titulacion_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])
        valores = split_pipe_list(row[columna_objetivo])

        eventos = [
            (int(anio), nivel, valor)
            for anio, nivel, valor in zip(ingresos, niveles, valores)
            if anio.isdigit() and int(anio) > anio_tit
        ]

        if not eventos:
            continue

        # Selección según criterio
        if criterio == "max":
            _, _, valor_sel = max(
                eventos,
                key=lambda x: orden_nivel.get(x[1], 0)
            )
        elif criterio == "min":
            _, _, valor_sel = min(
                eventos,
                key=lambda x: x[0]
            )
        else:
            raise ValueError("criterio debe ser 'max' o 'min'")

        resultados.append({
            "mrun": row["mrun"],
            columna_objetivo: valor_sel
        })

    df_res = pd.DataFrame(resultados)

    total = df_res["mrun"].nunique()

    conteo = (
        df_res.groupby(columna_objetivo)
        .size()
        .rename("cantidad")
        .reset_index()
    )

    conteo["total_reingresan"] = total
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(2)

    conteo = conteo.sort_values("cantidad", ascending=False)

    if top_n is not None:
        conteo = conteo.head(top_n)

    return conteo

#KPI 4: Tiempo de demora en acceder a otra carrera tras titularse en ECAS,
#separado por nivel_global (pregrado, postitulo, postgrado).
#Evalua el promedio. 
def calcular_demora_reingreso_por_nivel(
    cohorte_n: int | None = None
):
    """
    KPI 4:
    Tiempo de demora (en años) para reingresar a la educación superior
    tras titularse de ECAS, separado por nivel_global.
    
    Cada trayectoria post-ECAS se contabiliza como una observación.
    """

    df = pd.read_excel(FILE_PATH, sheet_name="Trayectoria_Resumen")

    columnas = [
        "mrun",
        "año_cohorte_ecas",
        "año_titulacion_ecas",
        "anio_ingreso_destino",
        "nivel_global"
    ]

    df = df[columnas].dropna(subset=["mrun", "año_titulacion_ecas"])

    if cohorte_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(
            df["año_cohorte_ecas"], errors="coerce"
        )
        df = df[df["año_cohorte_ecas"] == cohorte_n]

    registros = []

    for _, row in df.iterrows():

        anio_tit = row["año_titulacion_ecas"]
        cohorte = row["año_cohorte_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])

        for anio, nivel in zip(ingresos, niveles):

            if not anio.isdigit():
                continue

            anio = int(anio)

            if anio <= anio_tit:
                continue

            demora = anio - anio_tit

            registros.append({
                "cohorte": cohorte,
                "nivel_global": nivel,
                "demora_anios": demora
            })

    df_eventos = pd.DataFrame(registros)

    if df_eventos.empty:
        return df_eventos

    resumen = (
        df_eventos
        .groupby(["cohorte", "nivel_global"])
        .agg(
            promedio_demora=("demora_anios", "mean"),
            mediana_demora=("demora_anios", "median"),
            minimo_demora=("demora_anios", "min"),
            maximo_demora=("demora_anios", "max"),
            cantidad_trayectorias=("demora_anios", "count")
        )
        .reset_index()
    )

    resumen["promedio_demora"] = resumen["promedio_demora"].round(2)

    return resumen.sort_values(["cohorte", "nivel_global"])

#KPI 4.1: Tiempo de demora en acceder a otra carrera tras titularse en ECAS,
#separado por cantidad
def calcular_distribucion_demora_reingreso(
    cohorte_n: int | None = None
):
    """
    KPI 4.b:
    Distribución del tiempo de demora (en años) para reingresar
    a la educación superior tras titularse de ECAS.

    Cada trayectoria post-ECAS se contabiliza como una observación.
    """

    df = pd.read_excel(FILE_PATH, sheet_name="Trayectoria_Resumen")

    columnas = [
        "mrun",
        "año_cohorte_ecas",
        "año_titulacion_ecas",
        "anio_ingreso_destino",
        "nivel_global"
    ]

    df = df[columnas].dropna(subset=["mrun", "año_titulacion_ecas"])

    if cohorte_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(
            df["año_cohorte_ecas"], errors="coerce"
        )
        df = df[df["año_cohorte_ecas"] == cohorte_n]

    registros = []

    for _, row in df.iterrows():

        anio_tit = row["año_titulacion_ecas"]
        cohorte = row["año_cohorte_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])

        for anio, nivel in zip(ingresos, niveles):

            if not anio.isdigit():
                continue

            anio = int(anio)

            if anio <= anio_tit:
                continue

            demora = anio - anio_tit

            registros.append({
                "cohorte": cohorte,
                "nivel_global": nivel,
                "demora_anios": demora
            })

    df_eventos = pd.DataFrame(registros)

    if df_eventos.empty:
        return df_eventos

    distribucion = (
        df_eventos
        .groupby(["cohorte", "nivel_global", "demora_anios"])
        .size()
        .rename("cantidad_trayectorias")
        .reset_index()
        .sort_values(["cohorte", "nivel_global", "demora_anios"])
    )

    return distribucion

# KPI5: En promedio, ¿Cómo se ve la ruta de los titulados de ECAS?
# Evaluamos los porcentajes de cuantos hacen un pregrado (titulacion) > postítulo > magister > doctorado. 
def calcular_ruta_promedio_titulados(
    cohorte_n: Optional[int] = None
) -> pd.DataFrame:

    df = pd.read_excel(FILE_PATH, sheet_name="Trayectoria_Resumen")

    columnas = [
        "mrun",
        "año_cohorte_ecas",
        "año_titulacion_ecas",
        "anio_ingreso_destino",
        "nivel_global"
    ]

    df = df[columnas].dropna(subset=["mrun", "año_titulacion_ecas"])

    if cohorte_n is not None:
        df["año_cohorte_ecas"] = pd.to_numeric(
            df["año_cohorte_ecas"], errors="coerce"
        )
        df = df[df["año_cohorte_ecas"] == cohorte_n]

    rutas = []

    for _, row in df.iterrows():

        anio_tit = row["año_titulacion_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])

        # Reconstruir eventos post-ECAS
        eventos = [
            (int(anio), nivel)
            for anio, nivel in zip(ingresos, niveles)
            if anio.isdigit() and int(anio) > anio_tit
        ]

        if not eventos:
            ruta = ["Pregrado"]
        else:
            # Ordenar cronológicamente
            eventos.sort(key=lambda x: x[0])

            # Eliminar niveles repetidos (manteniendo orden)
            niveles_unicos = []
            for _, nivel in eventos:
                if not niveles_unicos or niveles_unicos[-1] != nivel:
                    niveles_unicos.append(nivel)

            ruta = ["Pregrado"] + niveles_unicos

        rutas.append({
            "mrun": row["mrun"],
            "ruta_secuencial": " → ".join(ruta)
        })

    df_rutas = pd.DataFrame(rutas)

    total_titulados = df_rutas["mrun"].nunique()

    conteo = (
        df_rutas.groupby("ruta_secuencial")
        .size()
        .rename("cantidad")
        .reset_index()
    )

    conteo["total_titulados"] = total_titulados
    conteo["porcentaje"] = (conteo["cantidad"] / total_titulados * 100).round(2)

    return conteo.sort_values("cantidad", ascending=False)