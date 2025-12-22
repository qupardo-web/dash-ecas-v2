from typing import Optional, Literal
import pandas as pd 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DASH1_DIR = BASE_DIR / "dash1"

FILE_TRAYECTORIA = "trayectoria_post_ecas.xlsx"
FILE_DESTINO = DASH1_DIR / "fuga_a_destino_todas_cohortes.xlsx"
FILE_ABANDONO = DASH1_DIR / "abandono_total_todas_cohortes.xlsx"

def split_pipe_list(x):
    if isinstance(x, str):
        parts = [p.strip() for p in x.split("|")]
        return [p for p in parts if p != ""]
    return []

def clasificar_nivel_post(nivel: str) -> dict:

    if not isinstance(nivel, str):
        return {"postitulo": False, "postgrado": False}

    n = nivel.lower()

    return {
        "pregrado" :(
            "pregrado" in n
        ),
        "postitulo": (
            "postítulo" in n or "postitulo" in n
        ),
        "postgrado": (
            "postgrado" in n or
            "magíster" in n or
            "magister" in n or
            "doctor" in n
        )
    }

def construir_universo_ex_ecas(anio_n: Optional[int] = None) -> pd.DataFrame:
    """
    Universo total de ex-ECAS:
    - Titulados
    - Desertores con destino
    - Desertores sin destino
    """

    # TITULADOS
    df_tit = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")
    df_tit["cohorte"] = pd.to_numeric(df_tit["año_cohorte_ecas"], errors="coerce")
    df_tit = df_tit[(df_tit["cohorte"] >= 2007) & (df_tit["cohorte"] <= 2025)]

    if anio_n is not None:
        df_tit = df_tit[df_tit["cohorte"] == anio_n]

    df_tit["mrun"] = df_tit["mrun"].astype(str)
    df_tit["origen"] = "Titulados ECAS"

    titulados_mrun = set(df_tit["mrun"])

    # DESERTORES CON DESTINO
    df_fd = pd.read_excel(FILE_DESTINO)
    df_fd["cohorte"] = pd.to_numeric(df_fd["año_cohorte_ecas"], errors="coerce")
    df_fd = df_fd[(df_fd["cohorte"] >= 2007) & (df_fd["cohorte"] <= 2025)]

    if anio_n is not None:
        df_fd = df_fd[df_fd["cohorte"] == anio_n]

    df_fd["mrun"] = df_fd["mrun"].astype(str)
    df_fd = df_fd[~df_fd["mrun"].isin(titulados_mrun)]
    df_fd["origen"] = "Desertores ECAS"

    desertores_mrun = set(df_fd["mrun"])

    # DESERTORES SIN DESTINO
    df_ab = pd.read_excel(FILE_ABANDONO)
    df_ab["cohorte"] = pd.to_numeric(df_ab["año_cohorte_ecas"], errors="coerce")
    df_ab = df_ab[(df_ab["cohorte"] >= 2007) & (df_ab["cohorte"] <= 2025)]

    if anio_n is not None:
        df_ab = df_ab[df_ab["cohorte"] == anio_n]

    df_ab["mrun"] = df_ab["mrun"].astype(str)
    df_ab = df_ab[
        ~df_ab["mrun"].isin(titulados_mrun | desertores_mrun)
    ]

    df_ab["origen"] = "Abandono total"

    return pd.concat(
        [
            df_tit[["mrun", "cohorte", "origen"]],
            df_fd[["mrun", "cohorte", "origen"]],
            df_ab[["mrun", "cohorte", "origen"]],
        ],
        ignore_index=True
    )

def ordenar_trayectoria_por_anio(row):
    """
    Ordena todas las listas de trayectoria usando
    anio_ingreso_destino como clave.
    """

    claves = row["anio_ingreso_destino"]

    if not claves:
        return row

    columnas = [
        "anio_ingreso_destino",
        "anio_ultimo_matricula",
        "institucion_destino",
        "carrera_destino",
        "nivel_global",
        "area_conocimiento_destino",
        "duracion_total_carrera",
        "tipo_inst_1",
        "tipo_inst_2",
        "tipo_inst_3"
    ]

    # Unir listas en tuplas
    registros = list(zip(*(row[col] for col in columnas)))

    # Ordenar por anio_ingreso_destino (posición 0)
    registros_ordenados = sorted(registros, key=lambda x: x[0])

    # Separar nuevamente en listas
    for i, col in enumerate(columnas):
        row[col] = [r[i] for r in registros_ordenados]

    return row

def calcular_contribucion_porcentual(df_resumen: pd.DataFrame) -> pd.DataFrame:
    # 1. Calcular el total por cohorte (Suma de Titulados + Desertores)
    df_totales = df_resumen.groupby("año_cohorte_ecas")[["postitulo", "postgrado"]].transform("sum")
    
    # 2. Calcular el % de contribución de cada grupo al total de su año
    # Usamos fillna(0) por si una cohorte no tiene registros en alguna categoría
    df_resumen["%_contrib_postitulo"] = (
        (df_resumen["postitulo"] / df_totales["postitulo"]) * 100
    ).round(2).fillna(0)
    
    df_resumen["%_contrib_postgrado"] = (
        (df_resumen["postgrado"] / df_totales["postgrado"]) * 100
    ).round(2).fillna(0)
    
    return df_resumen