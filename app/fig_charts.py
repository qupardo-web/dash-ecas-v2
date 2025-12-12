import dash
from dash import dcc
from dash import html
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from typing import Optional

COD_ECAS = 104

def create_admission_chart(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de líneas con marcadores para los ingresos por cohorte, 
    y añade una línea horizontal para el promedio general de ingresos.
    """
    if df.empty:
        return go.Figure()
        
    # Calcular el promedio de ingresos (Total_Mruns)
    promedio_mruns = df['Total_Mruns'].mean()
    
    # 1. Crear el gráfico de líneas y puntos (px.line con markers=True)
    fig = px.line(
        df,
        x='ingreso_primero',
        y='Total_Mruns',
        title='1. Ingreso Total de Alumnos a ECAS por Año (Cohorte)',
        labels={
            'ingreso_primero': 'Año de Ingreso (Cohorte)',
            'Total_Mruns': 'Número de Estudiantes'
        },
        color_discrete_sequence=['#1f77b4'],
        template='plotly_white',
        markers=True  # Muestra los puntos/marcadores
    )
    
    # 2. Añadir la línea horizontal de promedio (Roja y punteada)
    fig.add_hline(
        y=promedio_mruns,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Promedio Ingresos: {promedio_mruns:,.0f} alumnos",
        annotation_position="top right",
        annotation_font_color="red"
    )
    
    # Asegura que el eje X se trate como categoría
    fig.update_xaxes(type='category')
    
    # Ajustar marcadores para mayor visibilidad
    fig.update_traces(
        marker=dict(size=8, line=dict(width=2, color='DarkSlateGrey')),
        selector=dict(mode='markers+lines') # Asegura que la capa es de líneas y marcadores
    )
    
    return fig

def create_permanence_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
        
    fig = px.line(
        df,
        x='anio',
        y='tasa_permanencia_pct',
        title='2. Tasa de Permanencia (Retención) Anual de ECAS',
        labels={
            'anio': 'Año Base (N -> N+1)',
            'tasa_permanencia_pct': 'Tasa de Permanencia (%)'
        },
        color_discrete_sequence=['#2ca02c'], # Verde para Retención
        template='plotly_white',
        markers=True
    )
    
    fig.update_xaxes(type='category')
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    
    return fig

def create_permanence_chart_jornada(df: pd.DataFrame, jornada: str, cod_ecas: int) -> go.Figure:
    """Crea el gráfico de barras comparativas para una jornada específica."""
    
    if df.empty:
        return go.Figure().update_layout(title=f"Tasa de Permanencia Primer Año: {jornada}", annotations=[dict(text="No hay datos disponibles.", showarrow=False)])
    
    # 1. Aplicar el Top 5 + ECAS por año (Lógica de Python)
    df_filtered_list = []
    for year in df['anio'].unique():
        df_year = df[df['anio'] == year].copy()
        
        # Filtrar solo el Top 5
        df_top5 = df_year.sort_values(by='tasa_permanencia_pct', ascending=False).head(5)
        
        ids_to_keep = df_top5['cod_inst'].tolist()
        if cod_ecas in df_year['cod_inst'].values:
            ids_to_keep.append(cod_ecas)
        
        ids_to_keep = list(set(ids_to_keep))
        df_year_filtered = df_year[df_year['cod_inst'].isin(ids_to_keep)]
        
        df_filtered_list.append(df_year_filtered)

    df_final_ranking = pd.concat(df_filtered_list, ignore_index=True)

    df_final_ranking['anio'] = df_final_ranking['anio'].astype(str)
    
    # Ordenar el DataFrame final por año ascendente (2007, 2008, 2009...)
    df_final_ranking.sort_values(by='anio', ascending=True, inplace=True)
    
    # 2. Preparar el gráfico
    df_final_ranking['Institucion'] = df_final_ranking.apply(
        lambda row: "ECAS" if row['cod_inst'] == cod_ecas else row['nomb_inst'], axis=1
    )
    
    color_map = {'ECAS': '#d62728'} 

    fig = px.bar(
        df_final_ranking,
        x='anio',
        y='tasa_permanencia_pct',
        color='Institucion',      
        barmode='group',          
        title=f'Tasa de Permanencia de Primer Año: {jornada} (Top 5 + ECAS)',
        labels={
            'anio': 'Año de Ingreso (Cohorte)',
            'tasa_permanencia_pct': 'Permanencia (%)',
            'Institucion': 'Institución',
            'total_estudiantes': 'Ingresados en la cohorte',
            'permanencia_conteo': 'Estudiantes que permanecieron de la cohorte'
        },
        template='plotly_white',
        color_discrete_map=color_map, 

        custom_data=['total_estudiantes', 'permanencia_conteo', 'nomb_inst']
    )

    fig.update_traces(
        hovertemplate=(
            "<b>Institución:</b> %{customdata[2]}<br>" # customdata[2] es el nombre de la institución (nomb_inst)
            "<b>Cohorte:</b> %{x}<br>"
            "<b>Tasa de Permanencia:</b> %{y:.2f}%<br>"
            "---<br>"
            "<b>Ingresados (Base):</b> %{customdata[0]:.0f}<br>" # customdata[0] es 'total_estudiantes'
            "<b>Permanecieron:</b> %{customdata[1]:.0f}"          # customdata[1] es 'permanencia_conteo'
            "<extra></extra>" # Elimina la traza por defecto
        )
    )

    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    fig.update_xaxes(type='category', categoryorder='category ascending')
    
    return fig

def create_survival_chart(df: pd.DataFrame, anio_filtro: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de supervivencia con líneas para cohortes y una línea adicional 
    para el promedio general de supervivencia.
    """
    if df.empty:
        return go.Figure().update_layout(title="5. Tasa de Continuidad Estudiantil (Supervivencia)", annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    # Convertir la tasa a porcentaje para el eje Y
    df['tasa_pct'] = df['tasa'] * 100
    
    # 1. CALCULAR EL PROMEDIO GENERAL DE SUPERVIVENCIA POR AÑO RELATIVO
    df_promedio = df.groupby('anio_relativo')['tasa_pct'].mean().reset_index()
    df_promedio.rename(columns={'tasa_pct': 'promedio_general_pct'}, inplace=True)
    
    # 2. APLICAR EL FILTRO DE COHORTE
    if anio_filtro is not None and anio_filtro != 'ALL':
        df_plot = df[df['cohorte'] == int(anio_filtro)].copy()
        chart_title = f'5. Tasa de Continuidad: Cohorte {anio_filtro} vs. Promedio'
    else:
        # Si es 'ALL' o None, mostramos todas las cohortes y el promedio
        df_plot = df.copy()
        chart_title = '5. Tasa de Continuidad Estudiantil (Supervivencia) por Cohorte'

    # 3. CREAR EL GRÁFICO DE LÍNEAS BASE (Cohortes)
    fig = px.line(
        df_plot,
        x='anio_relativo',
        y='tasa_pct',
        color='cohorte' if anio_filtro is None or anio_filtro == 'ALL' else None,
        line_group='cohorte', 
        title=chart_title,
        labels={
            'anio_relativo': 'Año Relativo de Estudio (1 = Primer Año)',
            'tasa_pct': 'Tasa de Supervivencia (%)',
            'cohorte': 'Cohorte de Ingreso'
        },
        template='plotly_white',
        markers=True 
    )

    # 4. AÑADIR LA LÍNEA DE PROMEDIO GENERAL (usando go.Scatter)
    fig.add_trace(
        go.Scatter(
            x=df_promedio['anio_relativo'],
            y=df_promedio['promedio_general_pct'],
            mode='lines+markers',
            name='Promedio General de Supervivencia',
            line=dict(color='red', dash='dash', width=3),
            marker=dict(size=8, symbol='star'),
            hovertemplate="<b>Promedio General:</b> %{y:.2f}%<br>Año Relativo: %{x}<extra></extra>"
        )
    )

    # 5. AJUSTES FINALES
    fig.update_xaxes(
        tickmode='linear',
        tick0=1,
        dtick=1,
        title_text='Año Relativo de Estudio (1 = Primer Año)'
    )
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    
    # Si se selecciona una cohorte específica, ocultar la leyenda de cohortes, ya que solo hay una
    if anio_filtro is not None and anio_filtro != 'ALL':
        fig.update_layout(showlegend=True)
    else:
        fig.update_layout(showlegend=True) # Mostrar leyenda para ambas líneas (cohorte y promedio)

    return fig

def create_top_fuga_pie_chart(df: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de pastel para visualizar la distribución de estudiantes 
    en el Top N de instituciones de destino.
    """
    if df.empty:
        title = f"6. Distribución de Fuga a Destino (Cohorte {anio_n} - Top N)" if anio_n else "6. Distribución de Fuga a Destino (Top N)"
        return go.Figure().update_layout(title=title, annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    total_estudiantes = df['estudiantes_recibidos'].sum()
    
    subtitle = f"Total de estudiantes analizados en el Top {len(df)}: {total_estudiantes:,}"
    title = f"6. Distribución de Fuga a Destino (Cohorte {anio_n})" if anio_n else "6. Distribución de Fuga a Destino"

    fig = px.pie(
        df,
        values='estudiantes_recibidos',
        names='institucion_destino',
        title=title,
        template='plotly_white',
        hole=0.3, # Para que sea un "donut chart"
    )

    # Ajustar la plantilla de hover para mostrar el conteo exacto y el porcentaje
    fig.update_traces(
        textinfo='percent+label',
        hovertemplate=(
            "<b>Institución:</b> %{label}<br>"
            "<b>Estudiantes Recibidos:</b> %{value:,.0f}<br>"
            "<b>Proporción:</b> %{percent}<extra></extra>"
        )
    )
    
    # Añadir un texto central si es un donut chart
    fig.add_annotation(
        text=subtitle,
        x=0.5, y=-0.1, showarrow=False, font_size=10
    )
    
    return fig

def create_top_fuga_carrera_chart(df: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de barras horizontales para visualizar el Top N de carreras 
    a las que se fugaron los estudiantes, mostrando el ranking.
    """
    if df.empty:
        title = f"7. Top Carreras de Destino (Cohorte {anio_n} - Top N)" if anio_n else "7. Top Carreras de Destino (Top N)"
        return go.Figure().update_layout(title=title, annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    total_estudiantes = df['estudiantes_recibidos'].sum()
    
    subtitle = f"Total de estudiantes analizados en el Top {len(df)}: {total_estudiantes:,}"
    title = f"7. Top {len(df)} Carreras de Destino (Cohorte {anio_n})" if anio_n else f"7. Top {len(df)} Carreras de Destino"

    # Aseguramos el orden descendente para el ranking (la barra más larga arriba)
    df_plot = df.sort_values(by='estudiantes_recibidos', ascending=True).copy()
    
    fig = px.bar(
        df_plot,
        y='carrera_destino',
        x='estudiantes_recibidos',
        orientation='h', # Barras Horizontales
        title=title,
        labels={
            'carrera_destino': 'Carrera de Destino',
            'estudiantes_recibidos': 'Estudiantes Recibidos (MRUNs Únicos)'
        },
        template='plotly_white',
        color='estudiantes_recibidos', # Color basado en el conteo
        color_continuous_scale=px.colors.sequential.Teal
    )

    # Ajustar la plantilla de hover para mostrar el conteo exacto y el ranking
    fig.update_traces(
        hovertemplate=(
            "<b>Carrera:</b> %{y}<br>"
            "<b>Estudiantes Recibidos:</b> %{x:,.0f}<br>"
            "<extra></extra>"
        )
    )
    
    # Añadir un texto central si es un donut chart
    fig.add_annotation(
        text=subtitle,
        x=0.5, y=-0.1, showarrow=False, xref='paper', yref='paper', font_size=10
    )
    
    # Ajustar el layout para el ranking
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'} # Asegura que la barra más larga esté arriba
    )
    
    return fig

def create_fuga_area_pie_chart(df: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de pastel (Pie Chart) para visualizar la distribución de estudiantes 
    en el Top N de áreas de conocimiento de destino.
    """
    if df.empty:
        title = f"Top Áreas de Conocimiento de Destino (Cohorte {anio_n})" if anio_n else "Top Áreas de Conocimiento de Destino"
        return go.Figure().update_layout(title=title, annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    total_estudiantes = df['estudiantes_recibidos'].sum()
    n_areas = len(df)
    
    subtitle = f"Total de estudiantes analizados en el Top {n_areas}: {total_estudiantes:,}"
    title = f"Distribución de Fuga por Área de Conocimiento (Top {n_areas}, Cohorte {anio_n})" if anio_n else f"Distribución de Fuga por Área de Conocimiento (Top {n_areas})"

    fig = px.pie(
        df,
        values='estudiantes_recibidos',
        names='area_conocimiento_destino',
        title=title,
        template='plotly_white',
        hole=0.4, # Para un mejor visual (donut chart)
    )

    # Ajustar la plantilla de hover para mostrar el conteo exacto y el porcentaje
    fig.update_traces(
        textinfo='label+percent', # Muestra la etiqueta y el porcentaje en el gráfico
        hovertemplate=(
            "<b>Área de Destino:</b> %{label}<br>"
            "<b>Estudiantes Recibidos:</b> %{value:,.0f}<br>"
            "<b>Proporción:</b> %{percent}<extra></extra>"
        )
    )
    
    # Ajustes de layout para el título y leyenda
    fig.update_layout(
        margin=dict(t=50, b=10),
        legend_title_text="Áreas de Conocimiento"
    )
    
    # Añadir un texto central si es un donut chart (opcional)
    fig.add_annotation(
        text=subtitle,
        x=0.5, y=-0.1, showarrow=False, font_size=10
    )
    
    return fig