import pandas as pd
import plotly.express as px

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

def generar_barras_institucion(df, titulo):
    if df.empty:
        return px.bar(title=f"{titulo}: Sin datos")

    # Tomamos el nombre de la primera columna (la institución)
    col_dimension = df.columns[0]

    max_val = df['cantidad'].max()
    rango_x = [0, max_val * 1.25]
    
    fig = px.bar(
        df, 
        x='cantidad', 
        y=col_dimension,
        orientation='h',
        title=titulo,
        text='porcentaje',
        # CAMBIO 1: Color asociado al nombre de la institución
        color=col_dimension, 
        labels={'cantidad': 'Alumnos', col_dimension: 'Institución'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig.update_traces(texttemplate='%{text}%', textposition='outside', cliponaxis=False)
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", 
            yanchor="top", 
            y=-0.2,          # Posición respecto al gráfico
            xanchor="center", 
            x=0.5,
            traceorder="normal",
            font=dict(size=12), # Tamaño de fuente ligeramente menor para que quepa mejor
            itemsizing="constant"
        ),
        xaxis=dict(
            showticklabels=False, 
            title=None,           
            showgrid=False,       
            zeroline=False,
            range=rango_x   
        ),
        yaxis={'categoryorder': 'total ascending', 'showticklabels': False},
        margin=dict(t=60, b=150, l=20, r=100), 
        height=500, # Altura fija para controlar el scroll en el dashboard
        coloraxis_showscale=False
    )

    return fig