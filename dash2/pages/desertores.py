import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from auxiliar import *
import plotly.express as px
from dash import Input, Output, callback, State
from metricas_2 import *
from plots_desertores import *

df_filtros = pd.read_excel(FILE_TRAYECTORIA, sheet_name="Trayectoria_Resumen")

opciones_genero = [{'label': g, 'value': g} for g in df_filtros['gen_alu'].unique() if pd.notna(g)]
opciones_jornada = [{'label': j, 'value': j} for j in df_filtros['jornada'].unique() if pd.notna(j)]
opciones_edad = sorted([{'label': e, 'value': e} for e in df_filtros['rango_edad'].unique() if pd.notna(e)], key=lambda x: x['label'])

df_universo_base = construir_universo_ex_ecas()
cohortes_disponibles = sorted(df_universo_base['cohorte'].dropna().unique())

layout = dbc.Container([
    dbc.Row([
        # --- COLUMNA IZQUIERDA: FILTROS ---
        dbc.Col([
            html.Div([
                html.H4("Filtros de Análisis", className="mb-4"),
                
                # 1. Filtro: Cohorte
                html.Label("Seleccionar Cohorte:"),
                dcc.Dropdown(
                    id='filtro-cohorte',
                    options=[{'label': str(int(c)), 'value': int(c)} for c in cohortes_disponibles],
                    placeholder="Todas las cohortes",
                    className="mb-3"
                ),

                # 2. Filtro: Género (RadioItems para selección única)
                html.Label("Género:"),
                dbc.RadioItems(
                    id='filtro-genero',
                    options=[{"label": "Todos", "value": "todos"}] + opciones_genero,
                    value="todos",
                    className="mb-3"
                ),

                # 3. Filtro: Jornada (Checklist para selección múltiple)
                html.Label("Jornada:"),
                dbc.Checklist(
                    id='filtro-jornada',
                    options=opciones_jornada,
                    value=[j['value'] for j in opciones_jornada], # Todos seleccionados por defecto
                    labelStyle={'display': 'block'},
                    className="mb-3"
                ),

                # 4. Filtro: Rango Etario (Dropdown por la cantidad de opciones)
                html.Label("Rango Etario:"),
                dcc.Dropdown(
                    id='filtro-edad',
                    options=opciones_edad,
                    placeholder="Seleccionar rango...",
                    multi=True, # Permite seleccionar varios rangos
                    className="mb-3"
                ),

                dbc.Button("Aplicar Filtros", id="btn-aplicar", color="primary", className="w-100 mt-2")
            ], 
            style={
                "background-color": "#f8f9fa", 
                "padding": "20px", 
                "border-radius": "10px",
                "height": "100vh",
                "position": "sticky",
                "top": "0"
            })
        ], width=3),

        # --- COLUMNA DERECHA: RESULTADOS ---
        dbc.Col([
            html.H2("Análisis de Desertores y Permanencia", className="text-center mb-4"),
            
            # Gráficos de Permanencia (KPI 4 - Donut Charts)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Permanencia por Jornada (Distribución de Deserción)"),
                        dbc.CardBody([
                            dbc.Spinner(dbc.Row(id='container-permanencia-graficos'), color="primary")
                        ])
                    ], className="mb-4")
                ], width=12)
            ]),

            # Gráficos de Perfil (Barras y Pie)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Top Instituciones de Destino"),
                        dbc.CardBody(dcc.Graph(id='graph-dest-institucion'))
                    ])
                ], width=6, className="mb-4"),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Áreas de Conocimiento de Destino"),
                        dbc.CardBody(dcc.Graph(id='graph-dest-area'))
                    ])
                ], width=6, className="mb-4"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Tipo de Institución (Categoría 1)"),
                        dbc.CardBody(dcc.Graph(id='graph-dest-tipo1'))
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Nivel de destino"),
                        dbc.CardBody(dcc.Graph(id='graph-dest-nivel'))
                    ])
                ], width=6),
            ])
        ], width=9)
    ])
], fluid=True)

@callback(
    Output('container-permanencia-graficos', 'children'),
    [Input('btn-aplicar', 'n_clicks')],
    [State('filtro-cohorte', 'value'),
     State('filtro-jornada', 'value'),
     State('filtro-genero', 'value'),
     State('filtro-edad', 'value')]
)
def update_permanencia_charts(n_clicks, cohorte, jornadas_sel, genero, edad):
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    jornadas_sel = jornadas_sel or ["Diurna", "Vespertina"]
    charts = []
    
    for jor in jornadas_sel:
        df = calcular_permanencia_desertores(
            cohorte_n=cohorte,
            jornada=jor,
            gen_alu=None if genero == "todos" else genero,
            rango_edad=edad
        )

        if df.empty:
            charts.append(dbc.Col(html.P(f"Sin datos para {jor}"), width=6))
            continue

        # LLAMADA A LA FUNCIÓN EXTERNA
        fig = generar_figura_permanencia(df, jor, cohorte)
        
        charts.append(dbc.Col([dcc.Graph(figure=fig)], width=12 // len(jornadas_sel)))
    
    return charts

# --- CALLBACK 2: DESTINOS ---
@callback(
    [Output('graph-dest-institucion', 'figure'),
     Output('graph-dest-area', 'figure'),
     Output('graph-dest-tipo1', 'figure'),
     Output('graph-dest-nivel', 'figure')],
    [Input('btn-aplicar', 'n_clicks')],
    [State('filtro-cohorte', 'value'),
     State('filtro-genero', 'value'),
     State('filtro-jornada', 'value'),
     State('filtro-edad', 'value')]
)
def update_destino_charts(n_clicks, cohorte, genero, jornadas, edades):
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    gen_param = None if genero == "todos" else genero
    jor_param = jornadas[0] if (isinstance(jornadas, list) and len(jornadas) > 0) else None

    # Definimos configuraciones diferentes para cada gráfico si queremos
    config_graficos = [
        ('institucion_destino', 'Top Instituciones', 'Viridis'),
        ('area_conocimiento_destino', 'Áreas de Conocimiento', 'Teal'),
        ('tipo_inst_1', 'Categoría Institución 1', 'Blues'),
        ('nivel_global', 'Nivel de destino', 'Purples')
    ]

    figures = []
    for col_name, titulo, escala in config_graficos:
        df_top = calcular_top_reingreso_por_columna(
            columna_objetivo=col_name,
            cohorte_n=cohorte,
            gen_alu=gen_param,
            jornada=jor_param,
            solo_desertores=True
        )

        if df_top.empty:
            figures.append(px.bar(title=f"Sin datos: {titulo}"))
            continue

        # LLAMADA A LA FUNCIÓN EXTERNA CON PARÁMETROS DIFERENTES
        fig = generar_figura_barras_destino(df_top, titulo, escala)
        figures.append(fig)

    return figures