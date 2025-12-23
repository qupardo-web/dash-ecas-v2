import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def generar_pie_nivel_reingreso(df, titulo):
    fig = px.pie(
        df, values='cantidad', names='nivel_global',
        title=titulo, hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=40, b=80, l=10, r=10) # Espacio para la leyenda abajo
    )
    return fig

def generar_barras_categoricas(df, titulo, color_map=None):
    if df.empty:
        return px.bar(title=f"{titulo}: Sin datos")

    col_dimension = df.columns[0]
    max_val = df['cantidad'].max()
    rango_x = [0, max_val * 1.35]
    
    # Usamos template=None para evitar que herede estilos que causan el crash
    fig = px.bar(
        df, 
        x='cantidad', 
        y=col_dimension,
        orientation='h',
        title=titulo,
        text='porcentaje',
        color=col_dimension, 
        labels={'cantidad': 'Alumnos', col_dimension: 'Categoría'},
        color_discrete_map=color_map,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        template=None 
    )

    # Forzamos la limpieza de cualquier patrón que cause el error
    fig.update_traces(
        marker_pattern_shape=None, 
        texttemplate='%{text}%', 
        textposition='outside', 
        cliponaxis=False
    )
    
    fig.update_layout(
        showlegend=True,
        # Forzamos un fondo blanco manual para compensar la falta de template
        paper_bgcolor='white',
        plot_bgcolor='white',
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.2,
            xanchor="center", 
            x=0.5,
            traceorder="normal",
            font=dict(size=12),
            itemsizing="constant"
        ),
        xaxis=dict(
            showticklabels=False, 
            title=None,           
            showgrid=False,       
            zeroline=False,
            range=rango_x,
            linecolor='lightgray' # Línea base del eje
        ),
        yaxis={'categoryorder': 'total ascending', 'showticklabels': False},
        margin=dict(t=60, b=150, l=20, r=100), 
        height=500,
        coloraxis_showscale=False
    )

    return fig

def generar_scatter_tiempo_demora(df, titulo):
    if df.empty:
        return px.scatter(title=f"{titulo}: Sin datos")

    # Ordenamos para asegurar coherencia visual
    df = df.sort_values("demora_anios")
    
    fig = px.scatter(
        df, 
        x="demora_anios", 
        y="cantidad_alumnos",
        title=titulo,
        size="cantidad_alumnos", # El tamaño del punto depende de la cantidad
        color="cantidad_alumnos", # El color también varía con la intensidad
        color_continuous_scale="Viridis",
        labels={
            "demora_anios": "Años tras titulación",
            "cantidad_alumnos": "N° Estudiantes"
        }
    )

    fig.update_layout(
        xaxis=dict(
            dtick=1, 
            range=[-0.5, df["demora_anios"].max() + 1],
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(gridcolor='rgba(0,0,0,0.1)'),
        margin=dict(t=50, b=50, l=40, r=40),
        height=350, 
        coloraxis_showscale=False, # Ocultamos la barra de color para ahorrar espacio
        plot_bgcolor='white'
    )
    
    # Añadimos una línea suave de conexión para guiar la vista
    fig.update_traces(mode='markers+lines', line=dict(width=1, color='lightgray'))
    
    return fig

def generar_pictograma_rutas(df, titulo):
    if df.empty:
        return go.Figure().update_layout(title=f"{titulo}: Sin datos")

    # 1. Filtramos y preparamos las rutas de interés (las 5 que mencionaste)
    # Ordenamos por porcentaje para asegurar el llenado correcto de la cuadrícula
    df_plot = df.head(5).copy()
    
    fig = go.Figure()

    # Cuadrícula 10x10 (100 puntos = 100%)
    x_coords = np.tile(np.arange(10), 10)
    y_coords = np.repeat(np.arange(10), 10)
    
    # Definimos un mapa de estilos para que siempre sean consistentes
    # Nombre de ruta -> (Color, Símbolo)
    estilos = {
        "Pregrado": ("#E5ECF6", "square"),                   # Gris claro (Base)
        "Pregrado → Pregrado": ("#636EFA", "circle"),        # Azul
        "Pregrado → Postítulo": ("#00CC96", "diamond"),       # Verde
        "Pregrado → Postgrado": ("#EF553B", "star"),          # Rojo/Naranja
        "Pregrado → Postítulo → Postgrado": ("#AB63FA", "hexagram") # Morado
    }
    
    current_idx = 0
    
    for _, row in df_plot.iterrows():
        ruta = row['ruta_secuencial']
        porcentaje = row['porcentaje']
        
        # Calculamos cuántos iconos (puntos porcentuales)
        num_icons = int(round(porcentaje))
        if num_icons == 0 and porcentaje > 0: num_icons = 1 # Asegurar que se vea si es > 0
        
        end_idx = min(current_idx + num_icons, 100)
        
        if end_idx > current_idx:
            # Obtener estilo (o usar uno por defecto si no está en el mapa)
            color, simbolo = estilos.get(ruta, ("#FECB52", "triangle-up"))
            
            fig.add_trace(go.Scatter(
                x=x_coords[current_idx:end_idx],
                y=y_coords[current_idx:end_idx],
                mode="markers",
                name=f"{ruta} ({porcentaje}%)",
                marker=dict(
                    symbol=simbolo,
                    size=14 if simbolo != "square" else 12,
                    color=color,
                    line=dict(width=1, color="white") if simbolo == "square" else None
                ),
                hovertemplate=f"<b>{ruta}</b><br>{porcentaje}% de la cohorte<extra></extra>"
            ))
            current_idx = end_idx

    # Rellenar el resto si sobra espacio (rutas minoritarias no listadas)
    if current_idx < 100:
        fig.add_trace(go.Scatter(
            x=x_coords[current_idx:100],
            y=y_coords[current_idx:100],
            mode="markers",
            name="Otras rutas",
            marker=dict(symbol="square", size=10, color="#F3F3F3"),
            hoverinfo="skip"
        ))

    fig.update_layout(
        title=titulo,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 9.5]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 9.5]),
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.05, 
            xanchor="center", 
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(t=80, b=120, l=20, r=20),
        height=600,
        plot_bgcolor='white'
    )

    return fig