import dash
from dash import dcc
from dash import html
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from typing import Optional
import numpy as np

COD_ECAS = 104

def create_admission_chart(df: pd.DataFrame) -> go.Figure:
    """
    Crea un gráfico de líneas con marcadores para los ingresos por cohorte, 
    y añade una línea horizontal para el promedio general de ingresos.
    """
    if df.empty:
        return go.Figure()

    total_mruns_general = df['Total_Mruns'].sum()
        
    # Calcular el promedio de ingresos (Total_Mruns)
    promedio_mruns = df['Total_Mruns'].mean()
    
    # 1. Crear el gráfico de líneas y puntos (px.line con markers=True)
    fig = px.line(
        df,
        x='ingreso_primero',
        y='Total_Mruns',
        title=f'1. Ingreso Total de Alumnos a ECAS por Año (Cohorte) - Total General: {total_mruns_general:,.0f} alumnos',
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
    
    fig.update_traces(
        marker=dict(size=8, line=dict(width=2, color='DarkSlateGrey')),
        selector=dict(mode='markers+lines'),
        # Formato del hover mejorado
        hovertemplate=(
            "<b>Año de Cohorte:</b> %{x}<br>"
            "<b>Ingresos:</b> %{y:,.0f} estudiantes<extra></extra>"
        )
    )
    
    # 4. Ajustes de eje
    fig.update_xaxes(type='category')
    
    return fig

def create_permanence_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
        
    # La columna a graficar en el eje X ahora es la COHORTE

    ultima_cohorte_completa = df['cohorte_ingreso'].max()

    df_filtrado = df[df['cohorte_ingreso'] < ultima_cohorte_completa].copy()

    promedio_retencion = df_filtrado['tasa_retencion_pct'].mean()
    
    fig = px.line(
        df_filtrado,

        x='cohorte_ingreso', 
        y='tasa_retencion_pct',
        title='2. Tasa de Retención De Primer Año por Cohorte',
        labels={
            'cohorte_ingreso': 'Año de Ingreso (Cohorte)',
            'tasa_retencion_pct': 'Tasa de Retención al Año Siguiente (%)'
        },
        color_discrete_sequence=['#1f77b4'], # Un color limpio
        template='plotly_white',
        markers=True
    )

    fig.add_hline(
        y=promedio_retencion,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Promedio: {promedio_retencion:.2f}%",
        annotation_position="top left"
    )
    
    fig.update_xaxes(
        type='category',
        categoryorder='category ascending' 
    )
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    
    # Añadir hover data para claridad
    fig.update_traces(
        hovertemplate="Cohorte %{x}<br>Retención: %{y:.2f}%<extra></extra>"
    )
    
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
    if df.empty:
        return go.Figure().update_layout(title="5. Tasa de Continuidad Estudiantil y Titulación", annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    df['tasa_supervivencia_pct'] = df['tasa_supervivencia'] * 100
    df['tasa_titulacion_pct'] = df['tasa_titulacion_acumulada'] * 100
    
    df_promedio_supervivencia = df.groupby('anio_relativo')['tasa_supervivencia_pct'].mean().reset_index().rename(columns={'tasa_supervivencia_pct': 'promedio_general_supervivencia_pct'})
    
    df_promedio_titulacion = df.groupby('anio_relativo')['tasa_titulacion_pct'].mean().reset_index().rename(columns={'tasa_titulacion_pct': 'promedio_general_titulacion_pct'})

    if anio_filtro is not None and anio_filtro != 'ALL':
        df_plot = df[df['cohorte'] == int(anio_filtro)].copy()
        chart_title = f'5. Continuidad y Titulación: Cohorte {anio_filtro} vs. Promedio'
    else:
        df_plot = df.copy()
        chart_title = '5. Tasa de Continuidad Estudiantil y Titulación por Cohorte'

    max_anio_relativo = df_plot['anio_relativo'].max()
    limite_eje_x = max(max_anio_relativo, df_promedio_supervivencia['anio_relativo'].max())

    fig = px.line(
        df_plot,
        x='anio_relativo',
        y='tasa_supervivencia_pct',
        color='cohorte' if anio_filtro is None or anio_filtro == 'ALL' else None,
        line_group='cohorte', 
        title=chart_title,
        template='plotly_white',
        markers=True,
        custom_data=['estudiantes_sobreviven', 'titulados_acumulados', 'cohorte'],
        color_discrete_sequence=px.colors.qualitative.D3 # Asignar colores a las cohortes
    )

    fig.add_trace(
        go.Scatter(
            x=df_plot['anio_relativo'],
            y=df_plot['tasa_titulacion_pct'],
            mode='lines+markers',
            name=f'Titulación Acumulada (Cohorte {anio_filtro})' if anio_filtro and anio_filtro != 'ALL' else 'Titulación Acumulada',
            line=dict(color='blue', dash='solid', width=2),
            marker=dict(size=6, symbol='circle-open'),
            visible='legendonly' if anio_filtro is None or anio_filtro == 'ALL' else True, # Ocultar por defecto si son muchas líneas
            customdata=df_plot[['estudiantes_sobreviven', 'titulados_acumulados', 'cohorte']].values,
            yaxis='y',
            hovertemplate="<b>Titulación Acumulada:</b> %{y:.2f}%<br>Año Relativo: %{x}<br>Titulados: %{customdata[1]:.0f}<extra></extra>"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_promedio_supervivencia['anio_relativo'],
            y=df_promedio_supervivencia['promedio_general_supervivencia_pct'],
            mode='lines+markers',
            name='Promedio General Supervivencia',
            line=dict(color='red', dash='dash', width=3),
            marker=dict(size=8, symbol='star'),
            hovertemplate="<b>Promedio General (S):</b> %{y:.2f}%<br>Año Relativo: %{x}<extra></extra>"
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_promedio_titulacion['anio_relativo'],
            y=df_promedio_titulacion['promedio_general_titulacion_pct'],
            mode='lines+markers',
            name='Promedio General Titulación',
            line=dict(color='purple', dash='dash', width=3),
            marker=dict(size=8, symbol='square-open'),
            hovertemplate="<b>Promedio General (T):</b> %{y:.2f}%<br>Año Relativo: %{x}<extra></extra>"
        )
    )

    
    fig.update_xaxes(
        tickmode='linear', tick0=1, dtick=1, title_text='Año Relativo de Estudio (1 = Primer Año)',
        range=[0.5, limite_eje_x + 0.5]
    )
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    
    
    fig.update_traces(
        hovertemplate=(
            "<b>Cohorte:</b> %{customdata[2]}<br>"
            "<b>Año Relativo:</b> %{x}<br>"
            "<b>Tasa de Supervivencia:</b> %{y:.2f}%<br>"
            "---<br>"
            "<b>Estudiantes Activos:</b> %{customdata[0]:.0f}<br>"
            "<b>Titulados Acumulados:</b> %{customdata[1]:.0f}"
            "<extra></extra>"
        ),
        selector=lambda trace: trace.type == 'scatter' and 'Promedio' not in trace.name and 'Titulación Acumulada' not in trace.name
    )

    fig.update_layout(legend_title_text="Series")
    return fig

def create_resumen_continuidad_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()

    df_prom = (
        df.groupby("anio_relativo", as_index=False)
        .agg(
            supervivencia_pct=("tasa_supervivencia", "mean"),
            titulacion_pct=("tasa_titulacion_acumulada", "mean"),
            sobreviven_prom=("estudiantes_sobreviven", "mean"),
            titulados_prom=("titulados_acumulados", "mean")
        )
    )

    fig = go.Figure()

    # 🔹 Supervivencia
    fig.add_trace(go.Scatter(
        x=df_prom["anio_relativo"],
        y=df_prom["supervivencia_pct"] * 100,
        mode="lines+markers",
        name="Promedio Supervivencia",
        line=dict(dash="dash", width=3),
        marker=dict(symbol="circle"),
        customdata=df_prom[["sobreviven_prom"]],
        hovertemplate=(
            "<b>Año %{x}</b><br>"
            "Supervivencia: %{y:.1f}%<br>"
            "Estudiantes promedio: %{customdata[0]:.0f}"
            "<extra></extra>"
        )
    ))

    # 🔹 Titulación
    fig.add_trace(go.Scatter(
        x=df_prom["anio_relativo"],
        y=df_prom["titulacion_pct"] * 100,
        mode="lines+markers",
        name="Promedio Titulación Acumulada",
        line=dict(width=3),
        marker=dict(symbol="square"),
        customdata=df_prom[["titulados_prom"]],
        hovertemplate=(
            "<b>Año %{x}</b><br>"
            "Titulación acumulada: %{y:.1f}%<br>"
            "Titulados promedio: %{customdata[0]:.0f}"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Tasa Promedio de Supervivencia y Titulación (Todas las Cohortes)",
        xaxis_title="Año Relativo de Estudio (1 = Primer Año)",
        yaxis_title="Porcentaje (%)",
        yaxis=dict(range=[0, 100]),
        template="plotly_white",
        legend_title="Indicadores"
    )

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

def create_tiempo_descanso_chart(df_pivot: pd.DataFrame, anio_n: Optional[int] = None):

    if df_pivot.empty:
        title = (
            f"10. Distribución de Tiempo de Descanso (Cohorte {anio_n})"
            if anio_n else
            "10. Distribución de Tiempo de Descanso"
        )
        return go.Figure().update_layout(
            title=title,
            annotations=[dict(text="No hay datos disponibles.", showarrow=False)]
        )

    # 👉 NO reset_index, NO rename
    df_plot = df_pivot.copy()

    # Selección de columna
    columna_target = (
        anio_n if anio_n is not None and anio_n in df_plot.columns
        else 'TOTAL GENERAL'
    )

    df_plot_single = df_plot[
        ['Rango_de_Descanso', columna_target]
    ].copy()

    df_plot_single.rename(
        columns={columna_target: 'Porcentaje'},
        inplace=True
    )

    df_plot_single = df_plot_single[df_plot_single['Porcentaje'] > 0]

    total_reingreso = df_plot_single['Porcentaje'].sum()

    title = (
        f"10. Distribución del Tiempo de Descanso (Cohorte {anio_n} | Reingreso: {total_reingreso:.1f}%)"
        if anio_n else
        f"10. Distribución del Tiempo de Descanso (Total General | Reingreso: {total_reingreso:.1f}%)"
    )

    fig = px.pie(
        df_plot_single,
        values='Porcentaje',
        names='Rango_de_Descanso',
        hole=0.4,
        title=title,
        template='plotly_white'
    )

    fig.update_traces(
        textinfo='label+percent',
        hovertemplate="<b>Rango:</b> %{label}<br><b>Porcentaje:</b> %{value:.1f}%<extra></extra>"
    )

    fig.update_yaxes(range=[0, 100])

    return fig

def create_total_fugados_chart(df_final: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de barras apiladas (Stacked Bar Chart) mostrando el total de desertores 
    por cohorte, desglosado en Fuga a Destino y Abandono Total, usando go.Bar.
    """
    if df_final.empty:
        return go.Figure().update_layout(title="2. Total de Desertores y Distribución", annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    df_plot = df_final.copy()
    df_cohorts = df_plot[df_plot['año_cohorte_ecas'] != 'TOTAL GENERAL'].copy()
    
    total_desertores_general = df_cohorts['Total_Desertores'].sum()
    total_text = f" (Total General: {total_desertores_general:,.0f} alumnos)"
    
    # 1. Preparación de datos (Se mantiene igual)
    if anio_n is None:
        df_plot = df_cohorts
        chart_title = f'2. Total de Desertores por Cohorte y Distribución{total_text}'
    else:
        df_plot = df_cohorts[df_cohorts['año_cohorte_ecas'] == anio_n].copy()
        if df_plot.empty:
            return go.Figure().update_layout(
                title=f"2. Total de Desertores Cohorte {anio_n}", 
                annotations=[dict(text=f"No hay desertores en la Cohorte {anio_n}.", showarrow=False)]
            )
        chart_title = f'2. Distribución de Desertores: Cohorte {anio_n}{total_text}'

    # 2. Reestructurar el DataFrame a formato ancho (WIDE) para go.Bar
    # Para go.Bar, es más fácil trabajar con el formato WIDE, donde cada columna es una traza.
    # Aseguramos el orden del eje X
    df_plot['año_cohorte_ecas'] = df_plot['año_cohorte_ecas'].astype(str)
    df_plot.sort_values(by='año_cohorte_ecas', inplace=True)
    
    # 3. Creación del objeto Figure y las Traza (go.Bar)
    fig = go.Figure()
    
    # Definición de colores
    COLOR_FUGA = '#34A853'
    COLOR_ABANDONO = '#EA4335'
    
    # --- Traza 1: Fuga a Destino (Fuga_a_Destino) ---
    df_fuga = df_plot.copy()
    
    fig.add_trace(go.Bar(
        x=df_fuga['año_cohorte_ecas'],
        y=df_fuga['Fuga_a_Destino'],
        name='Fuga a Destino',
        marker_color=COLOR_FUGA,
        
        # Customdata para Fuga a Destino: [Total Cohorte, % Fuga, Tipo]
        customdata=df_fuga[['Total_Desertores', '%_Fuga_a_Destino']].values,
        
        hovertemplate=(
            "<b>Cohorte:</b> %{x}<br>"
            "<b>Total Desertores (Cohorte):</b> %{customdata[0]:,.0f}<br>" 
            "<hr>"
            "<b>Tipo:</b> Fuga a Destino<br>"
            "<b>Conteo:</b> %{y:,.0f} estudiantes<br>"
            "<b>Porcentaje:</b> %{customdata[1]:.1f}%"
            "<extra></extra>"
        )
    ))

    # --- Traza 2: Abandono Total (Abandono_Total) ---
    df_abandono = df_plot.copy()
    
    fig.add_trace(go.Bar(
        x=df_abandono['año_cohorte_ecas'],
        y=df_abandono['Abandono_Total'],
        name='Abandono Total',
        marker_color=COLOR_ABANDONO,
        
        # Customdata para Abandono Total: [Total Cohorte, % Abandono, Tipo]
        customdata=df_abandono[['Total_Desertores', '%_Abandono_Total']].values,
        
        hovertemplate=(
            "<b>Cohorte:</b> %{x}<br>"
            "<b>Total Desertores (Cohorte):</b> %{customdata[0]:,.0f}<br>" 
            "<hr>"
            "<b>Tipo:</b> Abandono Total<br>"
            "<b>Conteo:</b> %{y:,.0f} estudiantes<br>"
            "<b>Porcentaje:</b> %{customdata[1]:.1f}%"
            "<extra></extra>"
        )
    ))
    
    # 4. Ajustes de Layout Finales
    fig.update_layout(
        barmode='stack', # Apilar las barras
        title=chart_title,
        yaxis_title='Número de Desertores (MRUNs)',
        xaxis_title='Año de Ingreso (Cohorte)',
        template='plotly_white'
    )

    return fig

def create_titulacion_estimada_chart(df_final: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de barras para visualizar la estimación del conteo de estudiantes 
    titulados en instituciones de destino por cohorte.
    """
    if df_final.empty:
        return go.Figure().update_layout(title="11. Estimación de Titulados en Destino", annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    df_plot = df_final.copy()
    
    # 1. Preparación de datos para la visualización
    
    # Obtener el total general para el título
    total_general_row = df_plot[df_plot['año_cohorte_ecas'] == 'TOTAL GENERAL'].iloc[0]
    total_titulados_general = total_general_row['estudiantes_titulados']
    
    # Filtrar la vista para la gráfica
    if anio_n is not None:
        # Vista de una cohorte específica
        df_plot = df_plot[df_plot['año_cohorte_ecas'] != 'TOTAL GENERAL'].copy()
        df_plot = df_plot[df_plot['año_cohorte_ecas'] == anio_n].copy()
        
        if df_plot.empty:
             return go.Figure().update_layout(title=f"11. Estimación de Titulados (Cohorte {anio_n})", annotations=[dict(text=f"No hay estimados titulados en la Cohorte {anio_n}.", showarrow=False)])
             
        chart_title = f'11. Estimación de Titulados en Destino (Cohorte {anio_n}) - Total General: {total_titulados_general:,.0f}'
        
    else:
        # Vista de tendencia ('ALL' / Total)
        df_plot = df_plot[df_plot['año_cohorte_ecas'] != 'TOTAL GENERAL'].copy()
        chart_title = f'11. Estimación de Titulados en Destino por Cohorte - Total General: {total_titulados_general:,.0f}'

    # Asegurar que el año es string para el eje categórico
    df_plot['año_cohorte_ecas'] = df_plot['año_cohorte_ecas'].astype(str)

    # 2. Crear el gráfico de barras
    fig = px.bar(
        df_plot,
        x='año_cohorte_ecas',
        y='estudiantes_titulados',
        title=chart_title,
        labels={
            'año_cohorte_ecas': 'Año de Ingreso (Cohorte ECAS)',
            'estudiantes_titulados': 'Estudiantes (Estimado Titulados)'
        },
        template='plotly_white',
        color_discrete_sequence=['#ff9900'] # Color naranja/dorado para destacar finalización
    )
    
    # 3. Ajustes de Hover
    fig.update_traces(
        hovertemplate=(
            "<b>Cohorte:</b> %{x}<br>"
            "<b>Est. Titulados:</b> %{y:,.0f}<br>"
            "<extra></extra>"
        ),
        text=df_plot['estudiantes_titulados'].apply(lambda x: f'{x:,.0f}'), # Mostrar el conteo sobre la barra
        textposition='outside'
    )
    
    fig.update_layout(
        xaxis_type='category',
        yaxis_title='Número de Estudiantes'
    )
    
    return fig