import dash_bootstrap_components as dbc
from plot_titulados import *
from auxiliar import *
from metrics_titulados import *
from metricas_2 import *
from dash import Input, Output, callback, html, dcc, ALL, ctx

#Totales
df_total = kpi1_pct_llegan_postitulo_postgrado()
total_titulados = df_total.loc[df_total['origen'] == 'Titulados ECAS', 'total_mrun'].values[0]
total_desertores = df_total.loc[df_total['origen'] == 'Desertores ECAS', 'total_mrun'].values[0]
total_abandono = df_total.loc[df_total['origen'] == 'Abandono total', 'total_mrun'].values[0]


df_filtros = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")
opciones_jornada = [{'label': j, 'value': j} for j in df_filtros['jornada'].unique() if pd.notna(j)]
cohortes_disponibles = sorted(df_filtros['año_cohorte_ecas'].dropna().unique())

def crear_card_metric(titulo, valor, icono_class):
    # Formateo de miles con punto como separador (estilo chileno)
    valor_formateado = f"{valor:,}".replace(",", ".")
    
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.I(className=f"fas {icono_class} fa-2x", style={"color": "#f39c12"}), width=3),
                dbc.Col([
                    html.P(titulo, className="text-muted mb-0", style={"fontSize": "0.9rem"}),
                    html.H4(valor_formateado, className="mb-0", style={"fontWeight": "bold"}),
                ], width=9),
            ], align="center")
        ]),
        className="shadow-sm border-0 rounded"
    )

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Dashboard de Seguimiento de Titulados ECAS", className="text-center my-4"),
            html.Hr()
        ], width=12)
    ]),

    dbc.Row(id="contenedor-metricas-totales", className="mb-4"),
    
    # --- FILTROS ---
    dbc.Row([
        dbc.Col([
            html.Label("Cohorte (Año Ingreso):"),
            dcc.Dropdown(
                id='filtro-cohorte-tit',
                # Generamos las opciones dinámicamente desde tu lista 'cohortes_disponibles'
                options=[
                    {'label': f"{int(c)}", 'value': int(c)} 
                    for c in cohortes_disponibles
                ],
                placeholder="Seleccione una cohorte...",
                className="mt-1",
                clearable=True  # Permite limpiar la selección para ver el total histórico
            )
        ], width=6),
        dbc.Col([
            html.Label("Jornada ECAS:"),
            html.Div([
                dbc.ButtonGroup([
                    # 1. Botón "Ambos" (Manual)
                    dbc.Button(
                        "Ambos", 
                        id={"type": "btn-jornada", "index": "todos"}, 
                        color="primary", 
                        outline=False
                    )
                ] + [
                    # 2. Botones dinámicos desde opciones_jornada
                    dbc.Button(
                        opt['label'],
                        id={"type": "btn-jornada", "index": opt['value']},
                        # Asignamos colores según el nombre para mantener tu estilo (Opcional)
                        color="warning" if opt['value'] == "Diurna" else "danger",
                        outline=True # Outline=True hace que se vean más limpios al estar agrupados
                    ) for opt in opciones_jornada
                ], className="mt-2 w-100") # w-100 para que use todo el ancho de la columna
            ])
        ], width=6),
    ], className="mb-4 p-3 bg-light rounded"),

    # --- KPI 1, 2 y 3 (Nivel, Institución y Área) ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 1: Nivel inmediato de Reingreso"),
                # Dejamos el Body vacío para que el callback inyecte los dcc.Graph necesarios
                dbc.CardBody(id='graph-nivel-reingreso') 
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 1.b: Máximo Nivel Alcanzado post-ECAS"),
                dbc.CardBody(id='graph-nivel-maximo') # El contenedor dinámico 
            ])
        ], width=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 2: Instituciones de Destino"),
                dbc.CardBody(
                    id='graph-tipo-inst-tit',
                    style={
                    "maxHeight": "500px",  # Altura fija máxima para la tarjeta
                    "overflowY": "auto",   # Habilita el scroll vertical si el gráfico es más alto
                    "overflowX": "auto"
                })
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 3: Areas de destino"),
                dbc.CardBody(
                    id='graph-tipo-area',
                    style={
                    "maxHeight": "500px",  # Altura fija máxima para la tarjeta
                    "overflowY": "auto",   # Habilita el scroll vertical si el gráfico es más alto
                    "overflowX": "auto"
                })
            ])
        ], width=6),
    ], className="mb-4"),

    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 3: Tiempo de Acceso a Nueva Carrera (Años tras titulación)"),
                dbc.CardBody(
                    id='graph-tiempo-acceso',
                    style={
                        "height": "650px",      # Altura fija para ver ~2 filas de gráficos
                        "overflow-y": "auto",   # Scroll activado
                        "overflow-x": "hidden"
                    }
                )
            ])
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 5: Representación de Trayectorias Académicas"),
                dbc.CardBody(id='graph-ruta-pictograma')
            ])
        ], width=12)
    ], className="mt-4")
        ], fluid=True,
            style={
                "backgroundColor": "#f5f5f5",  # Un gris muy claro profesional
                "minHeight": "100vh",         # Asegura que cubra toda la altura de la pantalla
                "padding": "20px"
            })

@callback(
    Output("contenedor-metricas-totales", "children"),
    [Input("filtro-cohorte-tit", "value"),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_metricas_encabezado(cohorte_sel, n_clicks_list):
    # 1. Identificar jornada seleccionada (opcional si tu kpi1 lo usa)
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else None

    # 2. Obtener datos filtrados
    # Nota: Asegúrate que kpi1_pct_llegan_postitulo_postgrado acepte cohorte_n
    df_total = kpi1_pct_llegan_postitulo_postgrado(anio_n=cohorte_sel)

    # 3. Extraer valores con manejo de errores
    def get_val(origen):
        try:
            return int(df_total.loc[df_total['origen'] == origen, 'total_mrun'].iloc[0])
        except (IndexError, KeyError, ValueError):
            return 0

    val_titulados = get_val('Titulados ECAS')
    val_desertores = get_val('Desertores ECAS')
    val_abandono = get_val('Abandono total')

    # 4. Crear las tarjetas usando tu función técnica
    card_titulados = dbc.Col(
        crear_card_metric("Total Titulados", val_titulados, "fa-graduation-cap"),
        width=4
    )
    card_desertores = dbc.Col(
        crear_card_metric("Total Desertores", val_desertores, "fa-user-slash"),
        width=4
    )
    card_abandono = dbc.Col(
        crear_card_metric("Abandono Total", val_abandono, "fa-door-open"),
        width=4
    )

    return [card_titulados, card_desertores, card_abandono]

@callback(
    Output('graph-nivel-reingreso', 'children'),
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi1_reingreso(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"


    if jornada_sel == "todos":
        jornadas_a_procesar = ["Diurna", "Vespertina"]
        ancho = 6 # Lado a lado
    else:
        jornadas_a_procesar = [jornada_sel]
        ancho = 12 # Pantalla completa dentro de la card

    lista_recursos = []

    for jor in jornadas_a_procesar:
        df_nivel = calcular_nivel_reingreso_inmediato(cohorte_n=cohorte, jornada=jor)

        if df_nivel.empty:
            lista_recursos.append(
                dbc.Col([
                    html.Div([
                        html.B(f"Jornada {jor}"),
                        html.P("Sin registros de reingreso.", className="text-muted small")
                    ], className="text-center p-4 border rounded bg-light", style={"height": "300px"})
                ], width=ancho)
            )
            continue

        fig = generar_pie_nivel_reingreso(df_nivel, f"Reingreso Inmediato ({jor})")
        
        lista_recursos.append(
            dbc.Col([
                dcc.Graph(figure=fig, config={'displayModeBar': False})
            ], width=ancho)
        )

    return dbc.Row(lista_recursos)

@callback(
    Output('graph-nivel-maximo', 'children'), # ID del contenedor en el layout
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi1_maximo(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"

    # Definir jornadas y ancho
    if jornada_sel == "todos":
        jornadas_a_procesar = ["Diurna", "Vespertina"]
        ancho = 6 # Lado a lado (Pie charts funcionan bien así)
    else:
        jornadas_a_procesar = [jornada_sel]
        ancho = 12

    lista_graficos = []

    for jor in jornadas_a_procesar:
        # Llamada a la función de nivel máximo
        df_max = calcular_nivel_reingreso(cohorte_n=cohorte, jornada=jor)
        
        if df_max.empty:
            lista_graficos.append(
                dbc.Col([
                    html.Div([
                        html.B(f"Jornada {jor}"),
                        html.P("Sin datos de nivel máximo alcanzado.", className="text-muted small")
                    ], className="text-center p-4 border rounded bg-light")
                ], width=ancho)
            )
            continue

        # Usamos la misma función de generación de Pie que ya tienes
        fig = generar_pie_nivel_reingreso(df_max, f"Nivel Máximo ({jor})")
        
        lista_graficos.append(
            dbc.Col([
                dcc.Graph(figure=fig, config={'displayModeBar': False})
            ], width=ancho)
        )

    return dbc.Row(lista_graficos)

@callback(
    Output('graph-tipo-inst-tit', 'children'),
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi2_instituciones(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"

    jornadas_a_procesar = ["Diurna", "Vespertina"] if jornada_sel == "todos" else [jornada_sel]
    ancho = 6 if jornada_sel == "todos" else 12

    lista_graficos = []

    for jor in jornadas_a_procesar:
        df_inst = calcular_top_reingreso_por_columna_titulados(
            columna_objetivo="institucion_destino",
            cohorte_n=cohorte,
            jornada=jor,
            criterio="min",
            top_n=5
        )

        if df_inst.empty:
            lista_graficos.append(crear_columna_vacia(f"Jornada {jor}", "instituciones", ancho))
            continue

        # Llamada a la función GENÉRICA
        fig = generar_barras_categoricas(df_inst, f"Top Instituciones ({jor})")
        
        lista_graficos.append(
            dbc.Col([dcc.Graph(figure=fig, config={'displayModeBar': False})], width=ancho)
        )
    

    return dbc.Row(lista_graficos)

@callback(
    Output('graph-tipo-area', 'children'),
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi3_areas(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"

    jornadas_a_procesar = ["Diurna", "Vespertina"] if jornada_sel == "todos" else [jornada_sel]
    ancho = 6 if jornada_sel == "todos" else 12

    lista_graficos = []

    for jor in jornadas_a_procesar:
        df_area = calcular_top_reingreso_por_columna_titulados(
            columna_objetivo="area_conocimiento_destino",
            cohorte_n=cohorte,
            jornada=jor,
            criterio="min",
            top_n=5
        )

        if df_area.empty:
            lista_graficos.append(crear_columna_vacia(f"Jornada {jor}", "áreas", ancho))
            continue

        # Llamada a la misma función GENÉRICA con título de áreas
        fig = generar_barras_categoricas(df_area, f"Top Áreas ({jor})")
        
        lista_graficos.append(
            dbc.Col([dcc.Graph(figure=fig, config={'displayModeBar': False})], width=ancho)
        )

    return dbc.Row(lista_graficos)

# Función auxiliar para no repetir código de "Sin datos"
def crear_columna_vacia(jornada, tipo, ancho):
    return dbc.Col([
        html.Div([
            html.B(jornada),
            html.P(f"Sin datos de {tipo} destino.", className="text-muted small")
        ], className="text-center p-4 border rounded bg-light", 
           style={"height": "400px", "display": "flex", "flexDirection": "column", "justifyContent": "center"})
    ], width=ancho)

@callback(
    Output('graph-tiempo-acceso', 'children'),
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi4_demora(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"
    
    jornadas_a_procesar = ["Diurna", "Vespertina"] if jornada_sel == "todos" else [jornada_sel]
    niveles = ["Pregrado", "Postítulo", "Postgrado"]
    
    contenido_total = []

    for jor in jornadas_a_procesar:
        # Título de sección de jornada
        contenido_total.append(html.H5(f"Jornada: {jor}", className="mt-4 mb-2 border-bottom"))
        
        # Fila para los 3 niveles de esta jornada
        fila_graficos = []
        
        df_demora_base = calcular_distribucion_demora_reingreso(cohorte_n=cohorte, jornada=jor)
        
        for nivel in niveles:
            # Filtramos el DF por el nivel actual
            df_nivel = df_demora_base[df_demora_base["nivel_global"] == nivel] if not df_demora_base.empty else pd.DataFrame()

            if df_nivel.empty:
                fila_graficos.append(
                    dbc.Col([
                        html.Div(f"Sin datos - {nivel}", className="text-muted small p-4 bg-light border")
                    ], width=4)
                )
            else:
                fig = generar_scatter_tiempo_demora(df_nivel, f"Reingreso a {nivel}")
                fila_graficos.append(
                    dbc.Col([dcc.Graph(figure=fig, config={'displayModeBar': False})], width=4)
                )
        
        contenido_total.append(dbc.Row(fila_graficos))

    return contenido_total

@callback(
    Output('graph-ruta-pictograma', 'children'),
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi_rutas(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"

    jornadas_a_procesar = ["Diurna", "Vespertina"] if jornada_sel == "todos" else [jornada_sel]
    ancho = 6 if jornada_sel == "todos" else 12

    lista_graficos = []

    for jor in jornadas_a_procesar:
        df_rutas = calcular_ruta_promedio_titulados(cohorte_n=cohorte, jornada=jor)

        if df_rutas.empty:
            lista_graficos.append(crear_columna_vacia(f"Jornada {jor}", "rutas", ancho))
            continue

        fig = generar_pictograma_rutas(df_rutas, f"Rutas de Reingreso ({jor})")
        
        lista_graficos.append(
            dbc.Col([
                dcc.Graph(figure=fig, config={'displayModeBar': False})
            ], width=ancho)
        )

    return dbc.Row(lista_graficos)