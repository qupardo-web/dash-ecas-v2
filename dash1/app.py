from dash import Dash, html, dcc, ctx
from dash.dependencies import Input, Output, ALL
from graphics import *
from metrics import *
import pandas as pd
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Inicio", href="#")),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Ingresos por MRUN", header=True),
                dbc.DropdownMenuItem("Destino ECAS", href="#"),
                dbc.DropdownMenuItem("Continuidad", href="#"),
            ],
            nav=True,
            in_navbar=True,
            label="Más",
        ),

        dbc.DropdownMenu(
                    label="Cohorte",
                    id="cohorte-dropdown-menu",
                    className="m-3",
                    align_end=True,  # ⬅️ clave para alinearlo a la derecha
                    children=[
                        dbc.DropdownMenuItem(
                            "Todas las Cohortes",
                            id={"type": "cohorte-item", "value": "ALL"}
                        ),
                        dbc.DropdownMenuItem(divider=True),
                        *[
                            dbc.DropdownMenuItem(
                                str(a),
                                id={"type": "cohorte-item", "value": a}
                            )
                            for a in range(2007, 2026)
                        ]
                    ],
        )
    ],

    brand="Dashboard Desertores de ECAS",
    brand_href="#",
    color="primary",
    dark=True,
)

app.layout = html.Div( 
    style={
        "padding": "20px",
        "maxWidth": "1200px",
        "margin": "0 auto"
    },
    children=[

        navbar,

        # ---------- GRÁFICO + LEYENDA ----------
        html.Div(
            children=[

                dbc.Tabs(
                    id="tabs-destino",
                    active_tab="institucion",
                    className="mb-4 mt-1",
                    children=[
                        dbc.Tab(label="Instituciones", tab_id="institucion"),
                        dbc.Tab(label="Carreras", tab_id="carrera"),
                        dbc.Tab(label="Áreas", tab_id="area"),
                    ],
                ),

                dbc.ButtonGroup(
                    className="mb-2",
                    size="lg",
                    children=[
                        dbc.Button("Primer destino", id="btn-orden-1", n_clicks=0, color="warning"),
                        dbc.Button("Segundo destino", id="btn-orden-2", n_clicks=0, color="warning"),
                        dbc.Button("Tercer destino", id="btn-orden-3", n_clicks=0, color="warning"),
                    ],
                    
                ),
            ]
        ),

        html.Div(
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "gap": "30px",
                "marginTop": "20px"
            },
            children=[

                # 🎯 GRÁFICO CENTRADO
                html.Div(
                    dcc.Graph(
                        id="grafico-destino",
                        config={"displayModeBar": False}
                    ),
                    style={
                        "width": "600px",
                        "display": "flex",
                        "justifyContent": "center"
                    }
                ),

                # 📜 LEYENDA SCROLL
                html.Div(
                    id="leyenda-destino",
                    style={
                        "width": "280px",
                        "justifycontent": "center",
                        "borderLeft": "1px solid #ddd",
                        "display": "flex"
                    }
                )
            ]
        ),

        dcc.Store(id="orden-destino-store", data=1),
        dcc.Store(id="cohorte-store", data="ALL"),
    ]
)

@app.callback(
    Output("cohorte-store", "data"),
    Input({"type": "cohorte-item", "value": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def update_cohorte_store(n_clicks):
    triggered = ctx.triggered_id

    if triggered is None:
        return "ALL"

    return triggered["value"]

TAB_MAP = {
    "institucion": "institucion_destino",
    "carrera": "carrera_destino",
    "area": "area_conocimiento_destino"
}

TITULO_MAP = {
    "institucion": "Instituciones de Destino",
    "carrera": "Carreras de Destino",
    "area": "Áreas de Conocimiento"
}

@app.callback(
    Output("orden-destino-store", "data"),
    [
        Input("btn-orden-1", "n_clicks"),
        Input("btn-orden-2", "n_clicks"),
        Input("btn-orden-3", "n_clicks"),
    ],
    prevent_initial_call=True
)
def update_orden_destino(btn1, btn2, btn3):
    triggered = ctx.triggered_id

    if triggered == "btn-orden-1":
        return 1
    if triggered == "btn-orden-2":
        return 2
    if triggered == "btn-orden-3":
        return 3

    return 1

@app.callback(
    [
        Output("btn-orden-1", "color"),
        Output("btn-orden-2", "color"),
        Output("btn-orden-3", "color"),
    ],
    Input("orden-destino-store", "data")
)
def marcar_boton_activo(orden):
    return (
        "warning" if orden == 1 else "secondary",
        "warning" if orden == 2 else "secondary",
        "warning" if orden == 3 else "secondary",
    )

@app.callback(
    [
        Output("grafico-destino", "figure"),
        Output("leyenda-destino", "children"),
    ],
    [
        Input("tabs-destino", "active_tab"),
        Input("orden-destino-store", "data"),
        Input("cohorte-store", "data"),
    ]
)
def update_grafico_destino(tab_activo, orden, cohorte):

    anio_n = None if cohorte == "ALL" else int(cohorte)

    columna = TAB_MAP[tab_activo]
    titulo = TITULO_MAP[tab_activo]

    df = get_top_fuga_por_orden(
        columna=columna,
        orden=orden,
        top_n=10,
        anio_n=anio_n
    )

    fig = create_top_destino_pie_chart(
        df=df,
        columna=columna,
        orden=orden,
        titulo_base=titulo,
        anio_n=anio_n
    )

    leyenda = crear_leyenda(df, columna)

    return fig, leyenda

if __name__ == "__main__":
    app.run(debug=True)