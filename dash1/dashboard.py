import dash
from dash import dcc
from dash.dependencies import Input, Output
from dash import html
import plotly.express as px
import pandas as pd
from sqlalchemy.engine import Engine
from typing import Optional
import sys
from conn_db import get_db_engine
from queries import *
from metrics import *
from fig_charts import *

#Constantes
COD_ECAS = 104
JORNADA_DIURNA = 'DIURNA'
JORNADA_VESPERTINA = 'VESPERTINA'

DB_ENGINE = get_db_engine()

#Carga de dataframes
df_ingresos = get_mruns_per_year(DB_ENGINE)
df_permanencia_data = get_permanencia_per_year(DB_ENGINE)
df_permanencia_diurna = get_permanencia_ranking_por_jornada(DB_ENGINE, JORNADA_DIURNA)
df_permanencia_vespertina = get_permanencia_ranking_por_jornada(DB_ENGINE, JORNADA_VESPERTINA)
df_continuidad_data = get_continuidad_per_year(DB_ENGINE)
df_fuga_destino_all = get_top_fuga_a_destino(top_n=10, anio_n=None)
df_fuga_carrera_all = get_top_fuga_a_carrera(top_n=10, anio_n=None)
df_fuga_area_all = get_top_fuga_a_area(top_n=10, anio_n=None)
df_tiempo_descanso_data = get_tiempo_de_descanso(anio_n=None)
df_total_fugados_data = get_total_fugados_por_cohorte(anio_n=None)
df_titulacion_estimada_data = get_estimation_titulacion_abandono(anio_n=None)

#Creación de gráficos
admission_chart = create_admission_chart(df_ingresos)
permanencia_chart = create_permanence_chart(df_permanencia_data)
permanence_diurna_chart = create_permanence_chart_jornada(df_permanencia_diurna, JORNADA_DIURNA, COD_ECAS)
permanence_vespertina_chart = create_permanence_chart_jornada(df_permanencia_vespertina, JORNADA_VESPERTINA, COD_ECAS)
survival_chart_initial = create_survival_chart(df_continuidad_data, anio_filtro='ALL')
survival_mean_chart = create_resumen_continuidad_chart(df_continuidad_data)
fuga_destino_chart_initial = create_top_fuga_pie_chart(df_fuga_destino_all, anio_n=None)
fuga_carrera_chart_initial = create_top_fuga_carrera_chart(df_fuga_carrera_all, anio_n=None)
fuga_area_chart_initial = create_fuga_area_pie_chart(df_fuga_area_all, anio_n=None)
df_total_general_pivot = df_tiempo_descanso_data[['TOTAL GENERAL']].copy()
tiempo_descanso_chart_initial = create_tiempo_descanso_chart(df_total_general_pivot, anio_n=None)
total_fugados_chart_initial = create_total_fugados_chart(df_total_fugados_data, anio_n=None)
titulacion_estimada_chart_initial = create_titulacion_estimada_chart(df_titulacion_estimada_data, anio_n=None)


cohortes_disponibles = sorted(df_ingresos['ingreso_primero'].unique().tolist())

cohortes_disponibles_completas = [
    year for year in cohortes_disponibles 
    if year >= 2007 and year <= 2024
]

opciones_dropdown = [{'label': 'Total General (Todas las Cohortes)', 'value': 'ALL'}] + \
                    [{'label': str(year), 'value': year} for year in cohortes_disponibles_completas]

app = dash.Dash(__name__, title="Dashboard de Deserción ECAS")

app.layout = html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '20px'}, children=[
    
    # Encabezado Principal
    html.H1(
        children='Dashboard de Retención y Trayectoria Estudiantil (ECAS)',
        style={
            'textAlign': 'center',
            'color': '#343a40',
            'marginBottom': '30px'
        }
    ),

    # Sección de Ingreso de Alumnos (Gráfico 1)
    html.Div(className='row', children=[
        html.Div(className='col-md-12', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='ingreso-total-chart',
                    figure=admission_chart
                )
            ])
        ])
    ]),
    
    html.Br(),

    html.Div(className='row', children=[
        html.Div(className='col-md-12', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='permanencia-total-chart', #Considera todos en el año, no solo los que ingresaron como primer año en esa cohorte
                    figure=permanencia_chart
                )
            ])
        ])
    ]),

    html.Br(),

    html.Div(style={'marginBottom': '20px', 'marginTop': '20px', 'width': '30%', 'minWidth': '250px'}, children=[
        html.Label("Seleccionar Cohorte de Ingreso:"),
        dcc.Dropdown(
            id='cohorte-dropdown',
            options=opciones_dropdown,
            value='ALL',  # Valor inicial: Mostrar todas las cohortes
            clearable=False
        ),
    ]),
    
    html.Br(),
    
    # Sección de Métricas de Fuga (Placeholder para futuros KPI)
    html.H2(
    children='Análisis de Permanencia por Jornada (Top 5 + ECAS)',
    style={
        'textAlign': 'left',
        'color': '#343a40',
        'marginTop': '20px',
        'borderBottom': '2px solid #e9ecef',
        'paddingBottom': '10px'
    }
    ),
    
    html.Div(className='row', children=[
        # Gráfico 4A: Jornada Diurna
        html.Div(className='col-md-6', children=[
            dcc.Graph(id='permanencia-diurna-chart', figure=create_permanence_chart_jornada(df_permanencia_diurna, JORNADA_DIURNA, COD_ECAS))
        ]),
        
        # Gráfico 4B: Jornada Vespertina
        html.Div(className='col-md-6', children=[
            dcc.Graph(id='permanencia-vespertina-chart', figure=create_permanence_chart_jornada(df_permanencia_vespertina, JORNADA_VESPERTINA, COD_ECAS))
        ]),
    ]),

    html.H2(
    children='5. Tasa de Continuidad Estudiantil por Cohorte',
    style={
        'textAlign': 'left',
        'color': '#343a40',
        'marginTop': '20px',
        'borderBottom': '2px solid #e9ecef',
        'paddingBottom': '10px'
    }
    ),
    html.Div(className='row', children=[
        html.Div(className='col-md-12', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='continuidad-chart',
                    figure=survival_chart_initial # Figura inicial completa
                )
            ])
        ])
    ]),

    html.H2(
    children='6. Top 10 Instituciones de Destino de los Estudiantes Fugados',
    style={
        'textAlign': 'left',
        'color': '#343a40',
        'marginTop': '20px',
        'borderBottom': '2px solid #e9ecef',
        'paddingBottom': '10px'
    }
    ),

    html.Div(className='row', children=[
        html.Div(className='col-md-6', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='fuga-destino-pie-chart',
                    figure=fuga_destino_chart_initial 
                )
            ])
        ]),
    ]),

    html.H2(
    children='7. Top 10 Carreras de Destino de los Estudiantes Fugados',
    style={
        'textAlign': 'left',
        'color': '#343a40',
        'marginTop': '20px',
        'borderBottom': '2px solid #e9ecef',
        'paddingBottom': '10px'
    }
    ),

    html.Div(className='row', children=[
        html.Div(className='col-md-6', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='fuga-carrera-bar-chart',
                    figure=fuga_carrera_chart_initial 
                )
            ])
        ]),
    ]),

    html.H2(
    children='8. Top 10 Areas de Destino de los Estudiantes Fugados',
        style={
            'textAlign': 'left', 'color': '#343a40', 'marginTop': '20px',
            'borderBottom': '2px solid #e9ecef', 'paddingBottom': '10px'
        }
    ),

    html.Div(className='row', children=[
        html.Div(className='col-md-12', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='fuga-area-pie-chart', # Nuevo ID para el Pie Chart
                    figure=fuga_area_chart_initial 
                )
            ])
        ]),
    ]),

    html.H2(
        children='9. Distribución del Tiempo de Descanso Antes de Reingresar',
        style={
            'textAlign': 'left', 'color': '#343a40', 'marginTop': '20px',
            'borderBottom': '2px solid #e9ecef', 'paddingBottom': '10px'
        }
    ),

    html.Div(className='row', children=[
        html.Div(className='col-md-8', children=[ # Usamos 8/12 para centrar un poco el pie chart
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='tiempo-descanso-chart',
                    figure=tiempo_descanso_chart_initial 
                )
            ])
        ]),
    ]),

    html.H2(
        children='10. Distribución del Cambio de Institución v/s Abandono del sistema',
        style={
            'textAlign': 'left', 'color': '#343a40', 'marginTop': '20px',
            'borderBottom': '2px solid #e9ecef', 'paddingBottom': '10px'
        }
    ),

    html.Div(className='col-md-6', children=[
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(
                id='total-fugados-chart', 
                figure=total_fugados_chart_initial # Nuevo KPI
            )
        ])
    ]),

    html.H2(
    children='11. Estimación de Titulados en Instituciones de Destino',
    style={
        'textAlign': 'left', 'color': '#343a40', 'marginTop': '20px',
        'borderBottom': '2px solid #e9ecef', 'paddingBottom': '10px'
    }

    ),

    html.Div(className='row', children=[
        html.Div(className='col-md-12', children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'}, children=[
                dcc.Graph(
                    id='titulacion-estimada-chart',
                    figure=titulacion_estimada_chart_initial 
                )
            ])
        ]),
    ]),

])

@app.callback(
    Output('permanencia-diurna-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_diurna_chart(selected_year):
    # Crear una copia del DataFrame completo para trabajar con ella
    df_filtered = df_permanencia_diurna.copy() 
    
    if selected_year != 'ALL':
        # Convertir el año seleccionado a entero
        year_int = int(selected_year)
        
        # Filtrar el DataFrame al año específico
        df_filtered = df_filtered[df_filtered['anio'] == year_int]
        
    # Reutilizar la función de creación de gráfico con el DataFrame filtrado
    # La función ya aplica la lógica de Top 5 + ECAS por año, que ahora será solo un año.
    return create_permanence_chart_jornada(df_filtered, JORNADA_DIURNA, COD_ECAS)


# --- Callback para actualizar el gráfico de Permanencia Vespertina ---
@app.callback(
    Output('permanencia-vespertina-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_vespertina_chart(selected_year):
    # Crear una copia del DataFrame completo
    df_filtered = df_permanencia_vespertina.copy() 
    
    if selected_year != 'ALL':
        year_int = int(selected_year)
        df_filtered = df_filtered[df_filtered['anio'] == year_int]
        
    # Reutilizar la función de creación de gráfico con el DataFrame filtrado
    return create_permanence_chart_jornada(df_filtered, JORNADA_VESPERTINA, COD_ECAS)

@app.callback(
    Output('continuidad-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_survival_chart(selected_year):
    if selected_year is None or selected_year == "ALL":
        return create_resumen_continuidad_chart(df_continuidad_data)

    return create_survival_chart(
        df_continuidad_data, anio_filtro=selected_year
    )

@app.callback(
    Output('fuga-destino-pie-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_fuga_destino_chart(selected_year):
    
    anio_n_filter = None
    if selected_year != 'ALL':
        try:
            anio_n_filter = int(selected_year)
        except ValueError:
            # Si el valor no es un entero válido (ej., algún error en la opción), ignorar el filtro
            anio_n_filter = None 

    # Recargar o refiltrar los datos desde la fuente
    df_fuga_destino_filtered = get_top_fuga_a_destino(top_n=10, anio_n=anio_n_filter)
    
    # Crear el gráfico
    return create_top_fuga_pie_chart(df_fuga_destino_filtered, anio_n=anio_n_filter)

@app.callback(
    Output('fuga-carrera-bar-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_fuga_carrera_chart(selected_year):
    
    anio_n_filter = None
    if selected_year != 'ALL':
        try:
            anio_n_filter = int(selected_year)
        except ValueError:
            anio_n_filter = None 

    # Recargar o refiltrar los datos desde la fuente
    df_fuga_carrera_filtered = get_top_fuga_a_carrera(top_n=10, anio_n=anio_n_filter)
    
    # Crear el gráfico
    return create_top_fuga_carrera_chart(df_fuga_carrera_filtered, anio_n=anio_n_filter)

@app.callback(
    Output('fuga-area-pie-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_fuga_area_pie_chart(selected_year):
    
    anio_n_filter = None
    if selected_year != 'ALL':
        try:
            anio_n_filter = int(selected_year)
        except (ValueError, TypeError):
            anio_n_filter = None 

    # Recargar o refiltrar los datos
    df_fuga_area_filtered = get_top_fuga_a_area(top_n=10, anio_n=anio_n_filter)
    
    # Crear el gráfico
    return create_fuga_area_pie_chart(df_fuga_area_filtered, anio_n=anio_n_filter)

@app.callback(
    Output('tiempo-descanso-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_tiempo_descanso_chart(selected_year):
    
    # Usamos el DataFrame completo cargado inicialmente (df_tiempo_descanso_data)
    df_base = df_tiempo_descanso_data.copy()
    
    if selected_year == 'ALL':
        # Mostrar TOTAL GENERAL
        df_filtered_pivot = df_base[['TOTAL GENERAL']].copy()
        return create_tiempo_descanso_chart(df_filtered_pivot, anio_n=None)
    else:
        # Mostrar una Cohorte específica (Pie Chart)
        try:
            anio_int = int(selected_year)
            # Pasamos solo la columna de la cohorte seleccionada
            if anio_int in df_base.columns:
                df_filtered_pivot = df_base[[anio_int]].copy()
                return create_tiempo_descanso_chart(df_filtered_pivot, anio_n=anio_int)
            else:
                # Si la cohorte existe en el dropdown pero no en los datos (ej: filtro de top 5)
                return create_tiempo_descanso_chart(pd.DataFrame(), anio_n=anio_int)
                
        except (ValueError, KeyError, TypeError):
            # En caso de error, volver al total general
            df_filtered_pivot = df_base[['TOTAL GENERAL']].copy()
            return create_tiempo_descanso_chart(df_filtered_pivot, anio_n=None)

@app.callback(
    Output('total-fugados-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_total_fugados_chart(selected_year):
    
    # 1. Inicializar la variable de filtro que usaremos en la función del gráfico
    anio_n_filter = None
    
    # Usamos el DataFrame completo cargado en memoria (asumiendo que df_total_fugados_data es global)
    df_base = df_total_fugados_data.copy()
    
    if selected_year != 'ALL':
        try:
            # 2. Asignar el valor de la Cohorte seleccionada a la variable de filtro
            anio_n_filter = int(selected_year)
            
            # Filtrar la fila de la cohorte seleccionada (si existe)
            df_filtered = df_base[df_base['año_cohorte_ecas'] == anio_n_filter].copy()

            # Pasar solo los datos filtrados y el año a la función
            return create_total_fugados_chart(df_filtered, anio_n=anio_n_filter)
            
        except (ValueError, TypeError):
            # Si el valor no es un número válido, tratamos como 'ALL'
            anio_n_filter = None

    # CASO 'ALL' O ERROR: Mostrar todas las cohortes
    # Excluir la fila 'TOTAL GENERAL' para el gráfico de tendencia
    df_filtered = df_base[df_base['año_cohorte_ecas'] != 'TOTAL GENERAL'].copy()
    
    # anio_n=None indica a la función que debe crear el gráfico de tendencia
    return create_total_fugados_chart(df_filtered, anio_n=None)

@app.callback(
    Output('titulacion-estimada-chart', 'figure'),
    [Input('cohorte-dropdown', 'value')]
)
def update_titulacion_estimada_chart(selected_year):
    
    # Usamos el DataFrame completo cargado en memoria (asumiendo que df_titulacion_estimada_data es global)
    df_base = df_titulacion_estimada_data.copy()
    
    if selected_year == 'ALL':
        # Vista de tendencia completa
        return create_titulacion_estimada_chart(df_base, anio_n=None)
    else:
        # Vista de Cohorte específica
        try:
            anio_int = int(selected_year)
            return create_titulacion_estimada_chart(df_base, anio_n=anio_int)
                
        except (ValueError, KeyError, TypeError):
            # En caso de error, volver a la vista general
            return create_titulacion_estimada_chart(df_base, anio_n=None)

if __name__ == '__main__':
    app.run(debug=True)