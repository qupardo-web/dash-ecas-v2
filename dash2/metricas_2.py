import pandas as pd
from typing import Optional
from auxiliar import *

#KPI 1: Porcentaje de estudiantes EX ECAS que llegan a postitulo o postgrado
def kpi1_pct_llegan_postitulo_postgrado(
    anio_n: Optional[int] = None,
    jornada: Optional[str] = None
) -> pd.DataFrame:

    # ---------- 1) UNIVERSO ----------
    df_universo = construir_universo_ex_ecas(anio_n)
    df_universo["mrun"] = df_universo["mrun"].astype(str)

    universo_mrun = set(df_universo["mrun"])

    # Inicializar flags
    df_universo["llega_postitulo"] = False
    df_universo["llega_postgrado"] = False

    # ---------- 2) TITULADOS ----------
    df_tit = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")
    df_tit["mrun"] = df_tit["mrun"].astype(str)

    if anio_n is not None:
        df_tit["año_cohorte_ecas"] = pd.to_numeric(
            df_tit["año_cohorte_ecas"], errors="coerce"
        )
        df_tit = df_tit[df_tit["año_cohorte_ecas"] == anio_n]
    
    if jornada is not None:
        df_tit["jornada"] = df_tit["jornada"].astype(str)
        df_tit = df_tit[df_tit["jornada"] == jornada]

    for _, row in df_tit.iterrows():
        anio_tit = row["año_titulacion_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])

        llega_postitulo = False
        llega_postgrado = False

        for anio, nivel in zip(ingresos, niveles):
            if not str(anio).isdigit():
                continue
            if int(anio) <= anio_tit:
                continue

            flags = clasificar_nivel_post(nivel)

            llega_postitulo |= flags["postitulo"]
            llega_postgrado |= flags["postgrado"] 

        if llega_postitulo:
            df_universo.loc[
                (df_universo["mrun"] == row["mrun"]) &
                (df_universo["origen"] == "Titulados ECAS"),
                "llega_postitulo"
            ] = True

        if llega_postgrado:
            df_universo.loc[
                (df_universo["mrun"] == row["mrun"]) &
                (df_universo["origen"] == "Titulados ECAS"),
                "llega_postgrado"
            ] = True

    # ---------- 3) DESERTORES CON DESTINO ----------
    df_fd = pd.read_excel(FILE_DESTINO)
    df_fd["mrun"] = df_fd["mrun"].astype(str)

    if anio_n is not None:
        df_fd["año_cohorte_ecas"] = pd.to_numeric(
            df_fd["año_cohorte_ecas"], errors="coerce"
        )
        df_fd = df_fd[df_fd["año_cohorte_ecas"] == anio_n]

    if jornada is not None:
        df_fd["jornada"] = df_fd["jornada"].astype(str)
        df_fd = df_fd[df_fd["jornada"] == jornada]

    for _, row in df_fd.iterrows():

        niveles = split_pipe_list(row["nivel_global"])

        llega_postitulo = False
        llega_postgrado = False

        for nivel in niveles:
            flags = clasificar_nivel_post(nivel)
            llega_postitulo |= flags["postitulo"]
            llega_postgrado |= flags["postgrado"]

            if llega_postitulo:
                df_universo.loc[
                    (df_universo["mrun"] == row["mrun"]) &
                    (df_universo["origen"] == "Desertores ECAS"),
                    "llega_postitulo"
                ] = True

            if llega_postgrado:
                df_universo.loc[
                    (df_universo["mrun"] == row["mrun"]) &
                    (df_universo["origen"] == "Desertores ECAS"),
                    "llega_postgrado"
                ] = True

    # ---------- 4) AGREGACIÓN ----------
    resumen = (
        df_universo
        .groupby("origen")
        .agg(
            total_mrun=("mrun", "count"),
            llegan_postitulo=("llega_postitulo", "sum"),
            llegan_postgrado=("llega_postgrado", "sum")
        )
        .reset_index()
    )

    resumen["pct_postitulo"] = (
        resumen["llegan_postitulo"] / resumen["total_mrun"] * 100
    ).round(2)

    resumen["pct_postgrado"] = (
        resumen["llegan_postgrado"] / resumen["total_mrun"] * 100
    ).round(2)

    # ---------- 5) TOTAL GENERAL ----------
    total = resumen["total_mrun"].sum()
    total_postitulo = resumen["llegan_postitulo"].sum()
    total_postgrado = resumen["llegan_postgrado"].sum()

    resumen = pd.concat(
        [
            resumen,
            pd.DataFrame([{
                "origen": "TOTAL (ex-ECAS)",
                "total_mrun": total,
                "llegan_postitulo": total_postitulo,
                "llegan_postgrado": total_postgrado,
                "pct_postitulo": round(total_postitulo / total * 100, 2),
                "pct_postgrado": round(total_postgrado / total * 100, 2)
            }])
        ],
        ignore_index=True
    )

    return resumen

#KPI 2: Institución, tipo de institución, area, carrera a la que se van separado por cohorte y por si es postgrado o postitulo.
#Que permita mostrar el top 10. Metodo generico que tome la columna y analice en base a ella. 
def calcular_top_reingreso_por_columna(
    columna_objetivo: str,          
    cohorte_n: int | None = None,
    top_n: int = 10,
    nivel_objetivo: str | None = None,
    gen_alu: str | None = None,
    jornada: str | None = None,
    solo_desertores: bool = False,
    solo_titulados: bool = False
) -> pd.DataFrame:

    df_universo = construir_universo_ex_ecas(cohorte_n)
    df_universo = df_universo[df_universo["origen"] != "Abandono total"].copy()

    if solo_desertores:
        df_universo = df_universo[df_universo["origen"] == "Desertores ECAS"].copy()
    
    if solo_titulados:
        df_universo = df_universo[df_universo["origen"] == "Titulados ECAS"].copy()

    mruns_validos = set(df_universo["mrun"].astype(str))

    resultados = []

    df_tit = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")
    df_tit["mrun"] = df_tit["mrun"].astype(str)

    if cohorte_n is not None:
        df_tit["año_cohorte_ecas"] = pd.to_numeric(
            df_tit["año_cohorte_ecas"], errors="coerce"
        )
        df_tit = df_tit[df_tit["año_cohorte_ecas"] == cohorte_n]

    if gen_alu is not None:
        df_tit["gen_alu"] = df_tit["gen_alu"].astype(str)
        df_tit = df_tit[df_tit["gen_alu"] == gen_alu]

    if jornada is not None:
        df_tit["jornada"] = df_tit["jornada"].astype(str)
        df_tit = df_tit[df_tit["jornada"] == jornada]


    df_tit = df_tit[df_tit["mrun"].isin(mruns_validos)]

    for _, row in df_tit.iterrows():

        anio_tit = row["año_titulacion_ecas"]

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])
        valores = split_pipe_list(row[columna_objetivo])

        eventos = []

        for anio, nivel, valor in zip(ingresos, niveles, valores):
            if not anio.isdigit():
                continue
            anio = int(anio)
            if anio <= anio_tit:
                continue

            flags = clasificar_nivel_post(nivel)

            if nivel_objetivo is None:
                eventos.append((anio, valor))
            elif nivel_objetivo == "postitulo" and flags["postitulo"]:
                eventos.append((anio, valor))
            elif nivel_objetivo == "postgrado" and flags["postgrado"]:
                eventos.append((anio, valor))
            elif nivel_objetivo == "pregrado" and flags["pregrado"]:
                eventos.append((anio, valor))

        if not eventos:
            continue

        # primer evento cronológico de ese nivel
        _, valor_sel = min(eventos, key=lambda x: x[0])

        resultados.append({
            "mrun": row["mrun"],
            columna_objetivo: valor_sel
        })

    # ======================================================
    # 3) DESERTORES CON DESTINO → fuga_a_destino
    # ======================================================
    df_fd = pd.read_excel(FILE_DESTINO)
    df_fd["mrun"] = df_fd["mrun"].astype(str)

    if cohorte_n is not None:
        df_fd["año_cohorte_ecas"] = pd.to_numeric(
            df_fd["año_cohorte_ecas"], errors="coerce"
        )
        df_fd = df_fd[df_fd["año_cohorte_ecas"] == cohorte_n]

    if gen_alu is not None:
        df_fd["gen_alu"] = df_fd["gen_alu"].astype(str)
        df_fd = df_fd[df_fd["gen_alu"] == gen_alu]

    if jornada is not None:
        df_fd["jornada"] = df_fd["jornada"].astype(str)
        df_fd = df_fd[df_fd["jornada"] == jornada]

    df_fd = df_fd[df_fd["mrun"].isin(mruns_validos)]

    for _, row in df_fd.iterrows():

        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])
        valores = split_pipe_list(row[columna_objetivo])

        eventos = []

        for anio, nivel, valor in zip(ingresos, niveles, valores):
            if not anio.isdigit():
                continue
            anio = int(anio)

            flags = clasificar_nivel_post(nivel)

            if nivel_objetivo is None:
                eventos.append((anio, valor))
            elif nivel_objetivo == "postitulo" and flags["postitulo"]:
                eventos.append((anio, valor))
            elif nivel_objetivo == "postgrado" and flags["postgrado"]:
                eventos.append((anio, valor))
            elif nivel_objetivo == "pregrado" and flags["pregrado"]:
                eventos.append((anio, valor))

        if not eventos:
            continue

        _, valor_sel = min(eventos, key=lambda x: x[0])

        resultados.append({
            "mrun": row["mrun"],
            columna_objetivo: valor_sel
        })

    df_res = pd.DataFrame(resultados)

    if df_res.empty:
        return df_res

    total = df_res["mrun"].nunique()

    conteo = (
        df_res
        .groupby(columna_objetivo)
        .size()
        .rename("cantidad")
        .reset_index()
        .sort_values("cantidad", ascending=False)
    )

    conteo["total_reingresan"] = total
    conteo["porcentaje"] = (conteo["cantidad"] / total * 100).round(2)

    return conteo.head(top_n)

def calcular_permanencia_desertores(
    cohorte_n: int | None = None,
    jornada: str | None = None,
    gen_alu: str | None = None,
    rango_edad: str | None = None,
) -> pd.DataFrame:
    
    # 1. Obtener el universo base (Desertores + Abandono Total)
    df_universo = construir_universo_ex_ecas(cohorte_n)
    
    # Corrección del filtro: Usamos .isin para incluir ambos grupos
    df_universo = df_universo[
        df_universo["origen"].isin(["Desertores ECAS", "Abandono Total"])
    ].copy()

    # 2. Cargar datos de trayectoria para obtener el año de fuga/abandono
    # Nota: Se asume que estos archivos contienen el campo 'año_primer_fuga'
    df_fuga = pd.read_excel(FILE_DESTINO)
    df_abandono = pd.read_excel(FILE_ABANDONO)
    
    # Unificamos ambos orígenes de deserción en un solo DataFrame de eventos
    df_eventos = pd.concat([df_fuga, df_abandono], ignore_index=True)
    df_eventos["mrun"] = df_eventos["mrun"].astype(str)

    # 3. Cruzar Universo con Eventos
    # Esto asegura que solo analizamos a los alumnos que pertenecen al universo filtrado
    df_universo["mrun"] = df_universo["mrun"].astype(str)
    df_analisis = pd.merge(
        df_universo, 
        df_eventos[["mrun", "año_primer_fuga", "gen_alu", "rango_edad", "jornada"]], 
        on="mrun", 
        how="inner"
    )

    # 4. Aplicar filtros de Perfil
    if cohorte_n:
        df_analisis = df_analisis[df_analisis["cohorte"] == cohorte_n]
    if jornada:
        df_analisis = df_analisis[df_analisis["jornada"] == jornada]
    if gen_alu:
        df_analisis = df_analisis[df_analisis["gen_alu"] == gen_alu]
    if rango_edad:
        if isinstance(rango_edad, list):
            df_analisis = df_analisis[df_analisis["rango_edad"].isin(rango_edad)]
        else:
            # Si es un string único, la comparación normal funciona
            df_analisis = df_analisis[df_analisis["rango_edad"] == rango_edad]

    if df_analisis.empty:
        return pd.DataFrame()

    # 5. Cálculo de Permanencia (Delta de años)
    # Cuántos años alcanzó a estar en la institución antes de irse
    df_analisis["años_permanencia"] = (
        df_analisis["año_primer_fuga"] - df_analisis["cohorte"]
    )

    # 6. Agrupación de resultados por Cohorte y Tiempo
    resumen = (
        df_analisis.groupby(["cohorte", "años_permanencia", "origen"])
        .size()
        .reset_index(name="cantidad_alumnos")
    )

    # Calcular el porcentaje de cada grupo respecto al total de la cohorte analizada
    total_cohorte = resumen["cantidad_alumnos"].sum()
    resumen["tasa_sobre_desercion"] = (resumen["cantidad_alumnos"] / total_cohorte * 100).round(2)

    return resumen.sort_values(["cohorte", "años_permanencia"])

#Calcular continuidad post ECAS (postitulo o postgrado) segun origen (titulados o desertores)
#Nota: rango edad toma:
#Para los titulados: edad de titulacion
#Para los desertores: edad de desercion
#Por ende, se entiende que la evaluación por rango de edad es independiente del origen
def calcular_kpi_continuidad_origen(cohorte_n: int | None = None, jornada: str | None = None, gen_alu: str | None = None, rango_edad: str | None = None) -> pd.DataFrame:

    df_universo = construir_universo_ex_ecas(cohorte_n)
    
    df_universo = df_universo[df_universo["origen"].isin(["Titulados ECAS", "Desertores ECAS"])].copy()
    df_universo["mrun"] = df_universo["mrun"].astype(str)

    df_tray = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")
    df_verificacion = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")
    df_tray["mrun"] = df_tray["mrun"].astype(str)

    df_fd = pd.read_excel(FILE_DESTINO)
    df_fd["mrun"] = df_fd["mrun"].astype(str)

    df_tray_total = pd.concat([df_tray, df_fd], ignore_index=True).drop_duplicates(subset=["mrun"], keep="first")

    df_merge = pd.merge(df_universo, df_tray_total, on="mrun", how="inner")

    if gen_alu:
        df_merge = df_merge[df_merge["gen_alu"] == gen_alu]
    if jornada:
        df_merge = df_merge[df_merge["jornada"] == jornada]
    if rango_edad:
        df_merge = df_merge[df_merge["rango_edad"] == rango_edad]

    resultados = []

    for _, row in df_merge.iterrows():
        # Parámetros de control
        anio_tit_ecas = row.get("año_titulacion_ecas", 0)
        es_titulado_ecas = (row["origen"] == "Titulados ECAS")

        # Procesar listas de trayectoria (asumiendo formato pipe '|')
        ingresos = split_pipe_list(row["anio_ingreso_destino"])
        niveles = split_pipe_list(row["nivel_global"])
        
        hizo_postitulo = 0
        hizo_postgrado = 0

        for anio, nivel in zip(ingresos, niveles):
            if not str(anio).isdigit(): 
                continue
            
            anio_ingreso = int(anio)
            flags = clasificar_nivel_post(nivel)

            if es_titulado_ecas:
                # Titulados ECAS: Solo si el ingreso es posterior o igual a su titulación en ECAS
                if anio_ingreso >= anio_tit_ecas:
                    if flags["postitulo"]: hizo_postitulo = 1
                    if flags["postgrado"]: hizo_postgrado = 1
            else:
                # Desertores: Se asume que cualquier postítulo/grado implica título previo externo
                if flags["postitulo"]: hizo_postitulo = 1
                if flags["postgrado"]: hizo_postgrado = 1

        if hizo_postitulo or hizo_postgrado:
            resultados.append({
                "año_cohorte_ecas": row["año_cohorte_ecas"],
                "origen": row["origen"],
                "postitulo": hizo_postitulo,
                "postgrado": hizo_postgrado
            })

    df_res = pd.DataFrame(resultados)
    
    if df_res.empty:
        return pd.DataFrame(columns=["año_cohorte_ecas", "origen", "postitulo", "postgrado"])

    # 4. Agrupación Final
    resumen = df_res.groupby(["año_cohorte_ecas", "origen"]).agg({
        "postitulo": "sum",
        "postgrado": "sum"
    }).reset_index()

    df_final = calcular_contribucion_porcentual(resumen)

    return df_final


