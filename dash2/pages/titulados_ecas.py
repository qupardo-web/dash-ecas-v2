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
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.I(className=f"fas {icono_class} fa-2x", style={"color": "#f39c12"}), width=3),
                dbc.Col([
                    html.P(titulo, className="text-muted mb-0", style={"fontSize": "0.9rem"}),
                    # Usamos f"{valor:,}" para agregar separadores de miles
                    html.H4(children=f"{valor:,}".replace(",", "."), className="mb-0", style={"fontWeight": "bold"}),
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

    dbc.Row([
        dbc.Col(crear_card_metric("Total Titulados", total_titulados, "fa-user-graduate"), width=4),
        dbc.Col(crear_card_metric("Total Desertores", total_desertores, "fa-user-minus"), width=4),
        dbc.Col(crear_card_metric("Total Abandono", total_abandono, "fa-door-open"), width=4),
    ], className="mb-4"),
    
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
    ], className="mb-4"),

    # --- KPI 4 y 5 (Tiempo y Ruta Promedio) ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 4: Tiempo de Acceso a Nueva Carrera (Años)"),
                dbc.CardBody(dcc.Graph(id='graph-tiempo-acceso'))
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KPI 5: Ruta Académica Promedio"),
                dbc.CardBody(dcc.Graph(id='graph-ruta-sankey')) # Ideal para ver el flujo Pre -> Post -> Mag
            ])
        ], width=6)
    ])
], fluid=True,
    style={
        "backgroundColor": "#f5f5f5",  # Un gris muy claro profesional
        "minHeight": "100vh",         # Asegura que cubra toda la altura de la pantalla
        "padding": "20px"
    })


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
    Output('graph-tipo-inst-tit', 'children'),
    [Input('filtro-cohorte-tit', 'value'),
     Input({'type': 'btn-jornada', 'index': ALL}, 'n_clicks')]
)
def update_kpi2_instituciones(cohorte, n_clicks_list):
    triggered_id = ctx.triggered_id
    jornada_sel = triggered_id['index'] if triggered_id and isinstance(triggered_id, dict) else "todos"

    # Lógica de bifurcación para "Ambos"
    if jornada_sel == "todos":
        jornadas_a_procesar = ["Diurna", "Vespertina"]
        ancho = 6
    else:
        jornadas_a_procesar = [jornada_sel]
        ancho = 12

    lista_graficos = []

    for jor in jornadas_a_procesar:
        # Llamada a la función genérica solicitada
        df_inst = calcular_top_reingreso_por_columna_titulados(
            columna_objetivo="institucion_destino",
            cohorte_n=cohorte,
            jornada=jor,
            criterio="min", # Inmediato post titulación
            top_n=5
        )

        if df_inst.empty:
            lista_graficos.append(
                dbc.Col([
                    html.Div([
                        html.B(f"Jornada {jor}"),
                        html.P("Sin datos de instituciones destino.", className="text-muted small")
                    ], className="text-center p-4 border rounded bg-light", style={"height": "400px", "display": "flex", "flexDirection": "column", "justifyContent": "center"})
                ], width=ancho)
            )
            continue

        fig = generar_barras_institucion(df_inst, f"Top Instituciones ({jor})")
        
        lista_graficos.append(
            dbc.Col([
                dcc.Graph(figure=fig, config={'displayModeBar': False})
            ], width=ancho)
        )

    return dbc.Row(lista_graficos)