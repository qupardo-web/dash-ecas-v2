import plotly.express as px
import plotly.graph_objects as go

def generar_figura_permanencia(df, jornada, cohorte=None):
    """Genera el gráfico de dona para la permanencia."""
    df_plot = df.copy()
    title_suffix = f"(Cohorte {cohorte})" if cohorte else "(Histórico)"
    
    if cohorte is None:
        df_plot = df_plot.groupby(["años_permanencia", "origen"])["cantidad_alumnos"].sum().reset_index()

    df_plot["label"] = df_plot["años_permanencia"].astype(str) + " años - " + df_plot["origen"]
    
    fig = px.pie(
        df_plot, 
        values='cantidad_alumnos', 
        names='label', 
        hole=0.4,
        title=f"Jornada {jornada} {title_suffix}",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig

def generar_figura_barras_destino(df, titulo, color_scale='Blues'):
    """Genera un gráfico de barras horizontal personalizado."""
    # Aquí puedes personalizar qué gráfico quieres según el título
    # Por ejemplo, si el título es 'Instituciones', podrías usar otro color
    
    fig = px.bar(
        df, 
        x='cantidad', 
        y=df.columns[0], # Toma la primera columna (la dimensión)
        orientation='h', 
        text='porcentaje',
        title=titulo,
        labels={'cantidad': 'Alumnos'},
        color='cantidad', 
        color_continuous_scale=color_scale
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'}, 
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10), 
        height=300
    )
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    return fig