import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output

# Importamos el layout de cada página
from pages import desertores, titulados_ecas

FONT_AWESOME = "https://use.fontawesome.com/releases/v5.15.4/css/all.css"

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, FONT_AWESOME],suppress_callback_exceptions=True)

# Diseño base con Navbar y un contenedor vacío para el contenido
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Desertores", href="/desertores")),
            dbc.NavItem(dbc.NavLink("Titulados ECAS", href="/titulados_ecas")),
        ],
        brand="Dashboard ECAS",
        color="primary",
        dark=True,
    ),
    dbc.Container(id='page-content', className="pt-4")
])

# Callback para cambiar de página
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/desertores':
        return desertores.layout
    elif pathname == '/titulados_ecas':
        return titulados_ecas.layout
    else:
        return "404 Page Not Found"

if __name__ == '__main__':
    app.run(debug=True)