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

def create_tiempo_descanso_chart(df_pivot: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de barras (o pastel si es un solo año) mostrando la distribución 
    porcentual del tiempo de descanso antes de volver a estudiar.
    """
    
    if df_pivot.empty:
        title = f"10. Distribución de Tiempo de Descanso (Cohorte {anio_n})" if anio_n else "10. Distribución de Tiempo de Descanso"
        return go.Figure().update_layout(title=title, annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    df_plot = df_pivot.reset_index().rename(columns={'rango_descanso': 'Rango_de_Descanso'})
    
    # Decidir si mostramos todas las cohortes o solo el Total General/un año
    if anio_n is not None or len(df_plot.columns) == 2:
        # Vista de una sola columna (Cohorte específica o TOTAL GENERAL)
        
        # Si anio_n está presente, usamos esa columna; si no, usamos 'TOTAL GENERAL'
        columna_target = anio_n if anio_n is not None and anio_n in df_plot.columns else 'TOTAL GENERAL'
        
        # Eliminar las filas donde el porcentaje es 0 para limpiar el pastel
        df_plot_single = df_plot[['Rango_de_Descanso', columna_target]].copy()
        df_plot_single.rename(columns={columna_target: 'Porcentaje'}, inplace=True)
        df_plot_single = df_plot_single[df_plot_single['Porcentaje'] > 0]
        
        total_reingreso = df_plot_single['Porcentaje'].sum()
        
        title = f"10. Distribución del Tiempo de Descanso (Cohorte {anio_n} | Reingreso: {total_reingreso:.1f}%)" if anio_n else f"10. Distribución del Tiempo de Descanso (Total General | Reingreso: {total_reingreso:.1f}%)"

        # Usamos PIE CHART para una distribución de un solo conjunto
        fig = px.pie(
            df_plot_single,
            values='Porcentaje',
            names='Rango_de_Descanso',
            title=title,
            template='plotly_white',
            hole=0.4
        )
        fig.update_traces(
            textinfo='label+percent',
            hovertemplate="<b>Rango:</b> %{label}<br><b>Porcentaje:</b> %{value:.1f}%<extra></extra>"
        )

    else:
        # Vista de Múltiples Cohortes (Si anio_n es None y queremos ver la evolución de varias cohortes)
        
        # Reestructurar el DataFrame para Plotly Express (de ancho a largo)
        df_long = df_plot.melt(
            id_vars=['Rango_de_Descanso'],
            var_name='Cohorte',
            value_name='Porcentaje',
            ignore_index=False
        )
        
        # Excluir la columna 'TOTAL GENERAL' para esta vista, ya que es la media
        df_long = df_long[df_long['Cohorte'] != 'TOTAL GENERAL']
        
        title = '10. Distribución del Tiempo de Descanso por Cohorte (Evolución)'

        # Usamos BARRAS AGRUPADAS para comparar cohortes
        fig = px.bar(
            df_long,
            x='Rango_de_Descanso',
            y='Porcentaje',
            color='Cohorte',
            barmode='group',
            title=title,
            labels={'Porcentaje': 'Porcentaje de Estudiantes (%)', 'Rango_de_Descanso': 'Tiempo de Descanso'},
            template='plotly_white'
        )
        
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    
    return fig

def create_total_fugados_chart(df_final: pd.DataFrame, anio_n: Optional[int] = None) -> go.Figure:
    """
    Crea un gráfico de barras apiladas (Stacked Bar Chart) mostrando el total de desertores 
    por cohorte, desglosado en Fuga a Destino y Abandono Total.
    """
    if df_final.empty:
        return go.Figure().update_layout(title="2. Total de Desertores y Distribución", annotations=[dict(text="No hay datos disponibles.", showarrow=False)])

    df_plot = df_final.copy()

    df_cohorts = df_plot[df_plot['año_cohorte_ecas'] != 'TOTAL GENERAL'].copy()
    
    total_desertores_general = df_cohorts['Total_Desertores'].sum()
    
    total_text = f" (Total General: {total_desertores_general:,.0f} alumnos)"
    
    # 1. Limpieza y preparación para el gráfico de tendencia
    if anio_n is None:
        # Usamos el DataFrame solo de cohortes para el gráfico de tendencia
        df_plot = df_cohorts
        chart_title = f'2. Total de Desertores por Cohorte y Distribución{total_text}'
    else:
        # Filtramos el DataFrame solo por el año específico
        df_plot = df_cohorts[df_cohorts['año_cohorte_ecas'] == anio_n].copy()
        
        if df_plot.empty:
            # Si el filtro resulta en un DataFrame vacío, devolvemos la figura sin datos
            return go.Figure().update_layout(
                title=f"2. Total de Desertores Cohorte {anio_n}", 
                annotations=[dict(text=f"No hay desertores en la Cohorte {anio_n}.", showarrow=False)]
            )
        # Para un año específico, incluimos el total general para mantener la coherencia solicitada
        chart_title = f'2. Distribución de Desertores: Cohorte {anio_n}{total_text}'

    # 2. Reestructurar el DataFrame para apilamiento (de ancho a largo)
    df_long = pd.melt(
        df_plot,
        id_vars=['año_cohorte_ecas', 'Total_Desertores', '%_Fuga_a_Destino', '%_Abandono_Total'],
        value_vars=['Fuga_a_Destino', 'Abandono_Total'],
        var_name='Tipo_Desercion',
        value_name='Conteo_MRUNs'
    )
    
    df_long['Porcentaje_Fila'] = df_long.apply(
        lambda row: row['%_Fuga_a_Destino'] if row['Tipo_Desercion'] == 'Fuga_a_Destino' else row['%_Abandono_Total'], 
        axis=1
    )
    
    # 3. Crear el gráfico de barras apiladas
    fig = px.bar(
        df_long,
        x='año_cohorte_ecas',
        y='Conteo_MRUNs',
        color='Tipo_Desercion',
        title=chart_title, # <-- Usa el título modificado con el Total General
        labels={
            'año_cohorte_ecas': 'Año de Ingreso (Cohorte)',
            'Conteo_MRUNs': 'Número de Desertores (MRUNs)',
            'Tipo_Desercion': 'Tipo de Deserción'
        },
        template='plotly_white',
        color_discrete_map={
            'Fuga_a_Destino': '#34A853',
            'Abandono_Total': '#EA4335'
        }
    )
    
    # 4. Añadir porcentajes y TOTAL DE COHORTE al hover
    fig.update_traces(
        hovertemplate=(
            "<b>Cohorte:</b> %{x}<br>"
            "<b>Total Desertores (Cohorte):</b> %{customdata[2]:,.0f}<br>" # Total solo de la cohorte
            "<hr>"
            "<b>Tipo:</b> %{customdata[0]}<br>"
            "<b>Conteo:</b> %{y:,.0f} estudiantes<br>"
            "<b>Porcentaje:</b> %{customdata[1]:.1f}%"
            "<extra></extra>"
        ),
        # customdata contiene [Tipo_Desercion, Porcentaje_Fila, Total_Desertores (de la cohorte)]
        customdata=df_long[['Tipo_Desercion', 'Porcentaje_Fila', 'Total_Desertores']]
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