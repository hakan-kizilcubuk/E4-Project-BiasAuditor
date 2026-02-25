import dash
from dash import dcc, html, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import base64
import io
import json

# Importation de vos fonctions
from fonction_des_donné import (
    creation_de_ref, 
    moyenne_par_colone_référance, 
    biais_moyen
)

# Configuration de l'app
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP], 
    suppress_callback_exceptions=True
)

# --- CONFIGURATION VISUELLE ---
BLEU_DARK = "#1e293b"
ROSE_ALIA = "#d8627a"
ROUGE_CRITIQUE = "#ef4444"
VERT_VALIDE = "#10b981"
ORANGE_MOYEN = "#f59e0b"
GRIS_FOND = "#f8fafc"

styles = {
    'nav': {'backgroundColor': BLEU_DARK, 'padding': '15px', 'display': 'flex', 'justifyContent': 'center', 'gap': '30px'},
    'nav_link': {'color': 'white', 'textDecoration': 'none', 'fontSize': '16px', 'fontWeight': '500'},
    'card_dashboard': {
        'borderRadius': '12px', 'boxShadow': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
        'backgroundColor': 'white', 'padding': '20px', 'height': '100%', 'textAlign': 'center',
        'position': 'relative', 'border': '2px solid transparent'
    },
    'menu_item': {
        'padding': '12px 20px', 'margin': '5px 0', 'borderRadius': '6px', 'cursor': 'pointer',
        'borderLeft': '5px solid transparent', 'transition': '0.3s', 'backgroundColor': '#f1f5f9'
    },
    'menu_item_selected': {
        'borderLeft': f'5px solid {ROSE_ALIA}', 'backgroundColor': '#fff1f2', 'color': ROSE_ALIA, 'fontWeight': 'bold'
    },
    'badge': {
        'position': 'absolute', 'top': '10px', 'right': '10px', 'fontSize': '10px', 
        'fontWeight': 'bold', 'padding': '2px 8px', 'borderRadius': '20px', 'color': 'white'
    }
}

# --- FONCTION GRAPHIQUE DONUT ---
def create_donut_chart(ecart_pourcent, color):  
    fig = go.Figure(data=[go.Pie(
        values=[ecart_pourcent, max(0.1, 100 - ecart_pourcent)], 
        hole=.75, 
        marker_colors=[color, "#e2e8f0"], 
        textinfo='none', 
        hoverinfo='none'
    )])
    fig.update_layout(
        showlegend=False, height=140, margin=dict(l=5, r=5, t=5, b=5),
        annotations=[dict(text=f"{ecart_pourcent:.1f}%", x=0.5, y=0.5, font_size=18, showarrow=False, font_weight="bold", font_color=color)],
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- LOGIQUE D'IMPORTATION ---
def safe_parse(contents, filename):
    if not filename or not filename.lower().endswith('.csv'): return "ERROR_TYPE", None
    try:
        content_string = contents.split(',')[1]
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        return "SUCCESS", df.to_dict('records')
    except Exception as e:
        print(f"Erreur lecture fichier: {e}")
        return "ERROR_READ", None

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='df_real_store', storage_type='session'),
    dcc.Store(id='df_gen_store', storage_type='session'),
    dcc.Store(id='selected-columns-store', data=['none'], storage_type='session'),
    html.Div(id='nav-container'),
    html.Div(id='page-content', style={'backgroundColor': GRIS_FOND, 'minHeight': '92vh'})
])

# --- VUES ---
def render_navbar(active_page="/"):
    return html.Div(style=styles['nav'], children=[
        dcc.Link("📁 Importation", href="/", style={**styles['nav_link'], 'color': ROSE_ALIA if active_page == "/" else "white"}),
        dcc.Link("📊 Dashboard de Biais", href="/graphique", style={**styles['nav_link'], 'color': ROSE_ALIA if active_page == "/graphique" else "white"}),
    ])

def render_index():
    return dbc.Container([
        html.H2("Alia Bias Auditor", className="text-center pt-5 fw-bold", style={'color': BLEU_DARK}),
        dbc.Row([
            dbc.Col([
                html.Label("📂 Fichier Réel (Source)", className="fw-bold"),
                dcc.Upload(id='upload-reel', children=html.Div(id='content-reel', children="Glisser CSV"), 
                           style={'border': '2px dashed #cbd5e1', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': 'white', 'borderRadius': '10px'})
            ], width=6),
            dbc.Col([
                html.Label("📂 Fichier Généré (IA)", className="fw-bold"),
                dcc.Upload(id='upload-genere', children=html.Div(id='content-genere', children="Glisser CSV"),
                           style={'border': '2px dashed #cbd5e1', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': 'white', 'borderRadius': '10px'})
            ], width=6),
        ], className="mt-4"),
        html.Div(id='dynamic-menu-content', style={'maxWidth': '600px', 'margin': '40px auto'}),
        html.Div(dcc.Link(dbc.Button("Lancer l'Audit", color="danger", size="lg", className="px-5"), href="/graphique"), className="text-center pb-5")
    ])

def render_graph_page():
    return dbc.Container([
        html.H3("Rapport d'Audit : Fidélité des Données", className="py-4 fw-bold", style={'color': BLEU_DARK}),
        
        html.Div(className="p-4 bg-white rounded-3 shadow-sm mb-4", children=[
            dbc.Row([
                dbc.Col([
                    html.Label("1. Méthode :", className="fw-bold"),
                    dcc.RadioItems(
                        id='methode-calcul',
                        options=[{'label': ' Strict', 'value': 'strict'}, {'label': ' Médical', 'value': 'medical'}],
                        value='medical', labelStyle={'display': 'inline-block', 'marginRight': '20px'}
                    ),
                ], width=4),
                dbc.Col([
                    html.Label("2. Seuils de criticité (%) :", className="fw-bold"),
                    dcc.RangeSlider(
                        id='bias-threshold-slider',
                        min=0, 
                        max=100, 
                        step=1, 
                        value=[15, 40],
                        allowCross=False,  # EMPECHE LES CURSEURS DE SE CROISER
                        marks={0: '0%', 15: 'OK', 40: 'Alerte', 100: '100%'},
                        tooltip={
                            "always_visible": True, 
                            "placement": "top", 
                            "style": {"color": ROSE_ALIA, "fontSize": "14px", "fontWeight": "bold"}
                        }
                    ),
                ], width=8),
            ])
        ]),

        dbc.Row(id='individual-bias-cards', className="g-4"),
        
        dbc.Row([
            dbc.Col(html.Div(className="p-4 bg-white rounded-3 shadow-sm mt-4", children=[
                html.H5("Comparaison des Distributions", className="fw-bold"),
                dcc.Dropdown(id='dropdown-colonne', className="my-3"),
                dcc.Graph(id='graph-biais-unique')
            ]), width=12)
        ], className="pb-5"),
    ], fluid=True)

# --- CALLBACKS GESTION ---
@app.callback([Output('page-content', 'children'), Output('nav-container', 'children')], Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/graphique': return render_graph_page(), render_navbar("/graphique")
    return render_index(), render_navbar("/")

@app.callback([Output('content-reel', 'children'), Output('df_real_store', 'data')], Input('upload-reel', 'contents'), State('upload-reel', 'filename'))
def up_reel(c, f):
    if not c: return "Glisser CSV", dash.no_update
    s, d = safe_parse(c, f)
    return (f"✅ {f}", d) if s == "SUCCESS" else ("❌ Erreur", None)

@app.callback([Output('content-genere', 'children'), Output('df_gen_store', 'data')], Input('upload-genere', 'contents'), State('upload-genere', 'filename'))
def up_gen(c, f):
    if not c: return "Glisser CSV", dash.no_update
    s, d = safe_parse(c, f)
    return (f"✅ {f}", d) if s == "SUCCESS" else ("❌ Erreur", None)

@app.callback(Output('dynamic-menu-content', 'children'), [Input('df_real_store', 'data'), Input('selected-columns-store', 'data')])
def update_menu(data, selected):
    if not data: return html.Div("Veuillez importer les fichiers...", className="text-muted text-center")
    df = pd.DataFrame(data)
    options = ['none'] + [c for c in df.columns if c != df.columns[0]]
    return [html.Div(c if c != 'none' else "Tout Sélectionner", id={'type': 'menu-item', 'index': c},
                     style={**styles['menu_item'], **(styles['menu_item_selected'] if c in selected else {})}) for c in options]

@app.callback(Output('selected-columns-store', 'data'), Input({'type': 'menu-item', 'index': ALL}, 'n_clicks'), State('selected-columns-store', 'data'), prevent_initial_call=True)
def handle_menu_click(n_clicks, current):
    ctx = dash.callback_context
    if not ctx.triggered or all(v is None for v in n_clicks): return current
    try:
        prop_id = ctx.triggered[0]['prop_id']
        clicked_id = json.loads(prop_id.split('.')[0])
        clicked = clicked_id['index']
    except: return current
    if clicked == 'none': return ['none']
    new = [c for c in current if c != 'none']
    if clicked in new: new.remove(clicked)
    else: new.append(clicked)
    return new if new else ['none']

# --- CALLBACK CALCUL ET AFFICHAGE ---
@app.callback(
    [Output('individual-bias-cards', 'children'), Output('graph-biais-unique', 'figure'), 
     Output('dropdown-colonne', 'options'), Output('dropdown-colonne', 'value')],
    [Input('df_real_store', 'data'), Input('df_gen_store', 'data'), 
     Input('selected-columns-store', 'data'), Input('dropdown-colonne', 'value'),
     Input('methode-calcul', 'value'), Input('bias-threshold-slider', 'value')]
)
def update_results(data_r, data_g, selected, drop_val, methode, thresholds):
    if not data_r or not data_g or not selected:
        return [], go.Figure(), [], None
    
    lim_v, lim_o = thresholds
    df_r_raw = pd.DataFrame(data_r)
    df_g_raw = pd.DataFrame(data_g)
    ref_name = df_r_raw.columns[0]
    
    if 'none' in selected:
        targets = [c for c in df_r_raw.columns if c in df_g_raw.columns and c != ref_name]
    else:
        targets = [c for c in selected if c in df_r_raw.columns and c in df_g_raw.columns and c != ref_name]
    
    if not targets: return [], go.Figure(), [], None

    try:
        df_r_ref = creation_de_ref(df_r_raw[[ref_name] + targets], ref_name)
        df_g_ref = creation_de_ref(df_g_raw[[ref_name] + targets], ref_name)
        df_moy_r = moyenne_par_colone_référance(df_r_ref).sort_values("ref")
        df_moy_g = moyenne_par_colone_référance(df_g_ref)
        df_moy_g_filtre = df_moy_g[df_moy_g["ref"].isin(df_moy_r["ref"].unique())].sort_values("ref")
        
        df_moy_g_filtre["ratio"] = 1.0 
        
        df_bias_res = biais_moyen(df_moy_g_filtre, df_moy_r, df_r_raw, df_g_raw, methode=methode)
    except Exception as e:
        print(f"Erreur calcul: {e}")
        return [], go.Figure(), [], None

    cards = []
    for c in targets:
        val_err = float(df_bias_res[c].iloc[0]) if c in df_bias_res.columns else 0.0
        color = VERT_VALIDE if val_err <= lim_v else (ORANGE_MOYEN if val_err <= lim_o else ROUGE_CRITIQUE)
        statut = "OK" if val_err <= lim_v else ("MOYEN" if val_err <= lim_o else "CRITIQUE")
        
        cards.append(dbc.Col(html.Div(style={**styles['card_dashboard'], 'borderColor': color if statut=="CRITIQUE" else "transparent"}, children=[
            html.Span(statut, style={**styles['badge'], 'backgroundColor': color}),
            html.B(c, style={'color': BLEU_DARK, 'fontSize': '0.9rem'}),
            dcc.Graph(figure=create_donut_chart(val_err, color), config={'displayModeBar': False}),
        ]), width=6, md=3))

    d_val = drop_val if (drop_val in targets) else targets[0]
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_moy_r["ref"], y=df_moy_r[d_val], name='Réel', line=dict(color=BLEU_DARK, width=3)))
    fig_line.add_trace(go.Scatter(x=df_moy_g_filtre["ref"], y=df_moy_g_filtre[d_val], name='IA', line=dict(color=ROSE_ALIA, dash='dash', width=3)))
    fig_line.update_layout(title=f"Tendance : {d_val}", template="plotly_white", hovermode="x unified")
    
    return cards, fig_line, [{'label': c, 'value': c} for c in targets], d_val

if __name__ == '__main__':
    app.run(debug=True, dev_tools_ui=False)