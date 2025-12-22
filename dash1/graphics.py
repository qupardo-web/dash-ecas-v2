import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Optional
from metrics import *
from dash import html

def crear_leyenda(df: pd.DataFrame, columna: str):

    colores = px.colors.qualitative.Plotly

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        style={
                            "display": "inline-block",
                            "width": "12px",
                            "height": "12px",
                            "backgroundColor": colores[i % len(colores)],
                            "marginRight": "8px",
                            "borderRadius": "2px"
                        }
                    ),
                    html.Span(
                        row[columna],
                        style={"fontSize": "13px"}
                    )
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": "6px"
                }
            )
            for i, row in df.iterrows()
        ],
        style={
            "maxHeight": "300px",
            "overflowY": "auto",
            "padding": "10px"
        }
    )

def create_top_destino_pie_chart(df, columna, orden, titulo_base, anio_n):
    fig = px.pie(
        df, 
        values="estudiantes_recibidos",
        names=columna, 
        hole=0.45)

    fig.update_traces(
        textinfo="percent",
        textposition="inside",)

    fig.update_layout(
        showlegend=False,
        width=600,
        height=600,
        title=dict(
            text=f"{orden}° {titulo_base}" + (f" ({anio_n})" if anio_n else " (Todas las Cohortes)"),
            x=0.5
            
        )
    )

    return fig