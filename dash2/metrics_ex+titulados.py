#KPIs orientadas a la evaluación conjunta de estudiantes que se titularon de ECAS, y aquellos que abandonaron ECAS sin titularse.
#KPI 1: ¿Qué porcentaje de ex estudiantes ECAS llega a postítulo o postgrado?
#Evalua que porcentaje de ex estudiantes, tanto aquellos que abandonan sin titularse o aquellos que se titularon, y siguen en la educación superior, logran llegar a hacer una carrera
#con nivel global de postgrado o postítulo, y que porcentaje no lo logra. 
#Tenemos tres archivos: 
#- abandono_total_todas_cohortes.xlsx agrupa estudiantes que luego de abandonar ECAS no volvieron a estudiar.
#- fuga_a_destino_todas_cohortes.xlsx agrupa a los estudiantes que abandonaron ECAS sin titularse y siguieron en la educación superior
#- trayectoria_post_ecas.xlsx agrupa a los estudiantes que se titularon de ECAS. La primera hoja tiene todos los que se titularon, incluyendo
#Los que no continuaron con su educación, por otra parte la segunda hoja tiene la trayectoria posterior de aquellos que se titularon de ECAS.
#La idea en esta KPI es reunir el universo total de las cohortes 2007 a 2025, y ver cuantos que no son estudiantes activos de ECAS
#Han continuado sus estudios en postitulo o postgrado

'''
Archivo trayectoria post ecas
Hoja1: Trayectoria_Resumen: Trayectoria resumida de todos los titulados de ECAS desde 2007 a 2022 (ultimo registro existente de titulacion)
mrun	año_cohorte_ecas	año_titulacion_ecas	anio_ingreso_destino	anio_ultimo_matricula	institucion_destino	carrera_destino	nivel_global	area_conocimiento_destino	duracion_total_carrera
mrun    año de generacion ecas año titulacion año ingreso a otra institución año de ultima matricula destino inst destino carrera nivel global (pregrado, postitulo, etc) area dest duracion total
Hoja2: Trayectoria_Detallada: trayectoria post-ecas de los titulados. Si no aparece aca uno de la hoja 1, entonces su educación acabo en ECAS.

Archivo fuga_a_destino_todas_cohortes: Agrupa la trayectoria de alumnos ECAS que no se titularon
mrun	año_cohorte_ecas	año_primer_fuga	jornada	anio_ingreso_destino	anio_ultimo_matricula	institucion_destino	carrera_destino	area_conocimiento_destino	duracion_total_carrera	nivel_global	nivel_carrera_1	nivel_carrera_2	tipo_inst_1	tipo_inst_2	tipo_inst_3	requisito_ingreso

Archivo abandono_total_todas_cohortes: Ex alumnos ECAS que no se titularon y nunca siguieron estudiando (no hay mas registro de matriculas posteriores)
mrun	año_cohorte_ecas	año_primer_fuga
'''

#Podemos juntar tanto el analisis de los archivos como haciendo queries SQL, donde existe vista_titulados_unificada_limpia con todos los
#registros de titulados, y vista_matriculados_unificada que tiene todas las matriculas.

from typing import Optional
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

def has_postitulo_postgrado(niveles):
    niveles = [n.strip().lower() for n in (niveles or [])]
    postitulo = any("postítulo" in n or "postitulo" in n for n in niveles)
    postgrado = any("postgrado" in n or "magíster" in n or "magister" in n or "doctor" in n for n in niveles)
    return postitulo or postgrado

def kpi_pct_postitulo_postgrado(anio_n: Optional[int] = None) -> pd.DataFrame:
    # ---------- 1) TITULADOS ECAS ----------
    # Hoja 1: resumen de todos los titulados
    df_tit = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Detallada")
    df_tit["anio_titulacion"] = pd.to_numeric(df_tit["anio_titulacion"], errors="coerce")
    df_tit["anio_matricula_destino"] = pd.to_numeric(df_tit["anio_matricula_destino"], errors="coerce")
    df_tit["cohorte"] = pd.to_numeric(df_tit["cohorte"], errors="coerce")
    df_tit = df_tit[(df_tit["cohorte"] >= 2007) & (df_tit["cohorte"] <= 2025)].copy()
    if anio_n is not None:
        df_tit = df_tit[df_tit["cohorte"] == anio_n].copy()

    # nivel_global viene como "Pregrado | Postítulo | ..."
    if "nivel_global" in df_tit.columns:
        df_tit["nivel_global_list"] = df_tit["nivel_global"].apply(split_pipe_list)
    else:
        df_tit["nivel_global_list"] = [[] for _ in range(len(df_tit))]

    df_tit["llego_postitulo_postgrado"] = (
        (df_tit["anio_matricula_destino"] > df_tit["anio_titulacion"]) &
        (df_tit["nivel_global_list"].apply(has_postitulo_postgrado))
    )
    titulados_mrun = set(df_tit["mrun"].dropna().astype(str).unique())

    # ---------- 2) DESERTORES CON DESTINO ----------
    df_fd = pd.read_excel(FILE_DESTINO)
    df_fd["año_cohorte_ecas"] = pd.to_numeric(df_fd["año_cohorte_ecas"], errors="coerce")
    df_fd = df_fd[(df_fd["año_cohorte_ecas"] >= 2007) & (df_fd["año_cohorte_ecas"] <= 2025)].copy()
    if anio_n is not None:
        df_fd = df_fd[df_fd["año_cohorte_ecas"] == anio_n].copy()

    # excluir cualquier titulado para no duplicar universo
    df_fd["mrun_str"] = df_fd["mrun"].astype(str)
    df_fd = df_fd[~df_fd["mrun_str"].isin(titulados_mrun)].copy()

    # nivel_global en archivo fuga destino puede venir como "Pregrado | Postítulo | ..."
    df_fd["nivel_global_list"] = df_fd["nivel_global"].apply(split_pipe_list)
    df_fd["llego_postitulo_postgrado"] = df_fd["nivel_global_list"].apply(has_postitulo_postgrado)
    desertores_destino_mrun = set(df_fd["mrun_str"].dropna().unique())

    # ---------- 3) DESERTORES SIN DESTINO ----------
    df_ab = pd.read_excel(FILE_ABANDONO)
    df_ab["año_cohorte_ecas"] = pd.to_numeric(df_ab["año_cohorte_ecas"], errors="coerce")
    df_ab = df_ab[(df_ab["año_cohorte_ecas"] >= 2007) & (df_ab["año_cohorte_ecas"] <= 2025)].copy()
    if anio_n is not None:
        df_ab = df_ab[df_ab["año_cohorte_ecas"] == anio_n].copy()

    df_ab["mrun_str"] = df_ab["mrun"].astype(str)

    # excluir titulados y excluir los que ya están en fuga con destino
    df_ab = df_ab[~df_ab["mrun_str"].isin(titulados_mrun)].copy()
    df_ab = df_ab[~df_ab["mrun_str"].isin(desertores_destino_mrun)].copy()

    # abandono total nunca llega a postítulo/postgrado (por definición de archivo)
    df_ab["llego_postitulo_postgrado"] = False
    desertores_sin_destino_mrun = set(df_ab["mrun_str"].dropna().unique())

    # ---------- 4) AGREGACIÓN (por grupo + total) ----------
    def resumen_grupo(nombre, mruns_set, df_flag):
        total = len(mruns_set)
        llegaron = df_flag[df_flag["llego_postitulo_postgrado"]]["mrun"].nunique()
        pct = (llegaron / total * 100) if total > 0 else 0
        return {"grupo": nombre, "total_mrun": total, "llegan_postitulo_postgrado": llegaron, "porcentaje": round(pct, 2)}

    out = []
    out.append(resumen_grupo("Titulados ECAS", titulados_mrun, df_tit.assign(mrun=df_tit["mrun"].astype(str))))
    out.append(resumen_grupo("Desertores con destino", desertores_destino_mrun, df_fd))
    out.append(resumen_grupo("Desertores sin destino", desertores_sin_destino_mrun, df_ab))

    # Total consolidado
    universo_total = titulados_mrun | desertores_destino_mrun | desertores_sin_destino_mrun
    llegaron_total = (
        set(df_tit[df_tit["llego_postitulo_postgrado"]]["mrun"].astype(str).unique())
        | set(df_fd[df_fd["llego_postitulo_postgrado"]]["mrun_str"].unique())
    )
    llegaron_total = llegaron_total & universo_total

    total = len(universo_total)
    llegaron = len(llegaron_total)
    pct = (llegaron / total * 100) if total > 0 else 0

    out.append({
        "grupo": "TOTAL (ex-ECAS)",
        "total_mrun": total,
        "llegan_postitulo_postgrado": llegaron,
        "porcentaje": round(pct, 2)
    })

    print("MRUN únicos con postítulo/postgrado:",
      df_tit[df_tit["llego_postitulo_postgrado"]]["mrun"].nunique())

    # MRUN únicos con más de un nivel posterior
    print("MRUN con Postítulo Y Postgrado:",
        df_tit[
            df_tit["nivel_global_list"].apply(
                lambda x: (
                    any("postítulo" in n.lower() for n in x) and
                    any("postgrado" in n.lower() or "magíster" in n.lower() or "doctor" in n.lower() for n in x)
                )
            )
        ]["mrun"].nunique()
    )

    mruns_kpi = set(
    df_tit[df_tit["llego_postitulo_postgrado"]]["mrun"].astype(str)
    )

    # MRUN que realmente aparecen en trayectoria detallada
    df_det = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Detallada")
    mruns_det = set(df_det["mrun"].astype(str).unique())

    # Diferencia
    mruns_solo_resumen = mruns_kpi - mruns_det

    print("MRUN contados en KPI pero sin trayectoria detallada:", len(mruns_solo_resumen))
    print(sorted(list(mruns_solo_resumen))[:10])

    return pd.DataFrame(out)

df_postitulo = kpi_pct_postitulo_postgrado()
print(df_postitulo.head(10))

df_fd_raw = pd.read_excel(FILE_DESTINO)

print("Filas totales archivo fuga destino:", len(df_fd_raw))
print("MRUN únicos archivo fuga destino:", df_fd_raw["mrun"].nunique())