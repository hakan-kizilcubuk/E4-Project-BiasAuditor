import dash
from dash import dcc, html, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import io
import json

# Importation de vos fonctions
from fonction_des_donné import (
    creation_de_ref, 
    selection_valeur_ref_gen, 
    calcul_ratio, 
    biais_moyen, 
    moyenne_par_colone_référance
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# --- CONFIGURATION VISUELLE ---
BLEU_DARK = "#1e293b"
ROSE_ALIA = "#d8627a"
ROUGE_CRITIQUE = "#ef4444"
VERT_VALIDE = "#10b981"
GRIS_FOND = "#f8fafc"

styles = {
    'nav': {'backgroundColor': BLEU_DARK, 'padding': '15px', 'display': 'flex', 'justifyContent': 'center', 'gap': '30px'},
    'nav_link': {'color': 'white', 'textDecoration': 'none', 'fontSize': '16px', 'fontWeight': '500'},
    'card_dashboard': {
        'borderRadius': '12px', 'border': 'none', 'boxShadow': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
        'backgroundColor': 'white', 'padding': '20px', 'height': '100%', 'textAlign': 'center'
    },
    'menu_item': {
        'padding': '12px 20px', 'margin': '5px 0', 'borderRadius': '6px', 'cursor': 'pointer',
        'borderLeft': '5px solid transparent', 'transition': '0.3s', 'backgroundColor': '#f1f5f9'
    },
    'menu_item_selected': {
        'borderLeft': f'5px solid {ROSE_ALIA}', 'backgroundColor': '#fff1f2', 'color': ROSE_ALIA, 'fontWeight': 'bold'
    }
}

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='df_real_store', storage_type='session'),
    dcc.Store(id='df_gen_store', storage_type='session'),
    dcc.Store(id='selected-columns-store', data=['none'], storage_type='session'),
    html.Div(id='nav-container'),
    html.Div(id='page-content', style={'backgroundColor': GRIS_FOND, 'minHeight': '92vh'})
])

# --- FONCTION GRAPHIQUE DONUT (MODIFIÉE POUR % ÉCART) ---
def create_donut_chart(value):
    """ 
    Affiche l'écart en % par rapport à la moyenne globale.
    Ex: value = 1.25 -> Affiche +25%
    """
    ecart_pourcent = (value - 1) * 100
    color = VERT_VALIDE
    if ecart_pourcent > 15: color = "#f59e0b"
    if ecart_pourcent > 40: color = ROUGE_CRITIQUE
    
    # Texte d'affichage (Ajoute un '+' si positif)
    display_text = f"{'+' if ecart_pourcent >= 0 else ''}{ecart_pourcent:.1f}%"
    
    # Pour le visuel du donut, on normalise l'affichage
    fig = go.Figure(data=[go.Pie(values=[abs(ecart_pourcent), 100], hole=.75, 
                                 marker_colors=[color, "#e2e8f0"], textinfo='none', hoverinfo='none')])
    fig.update_layout(showlegend=False, height=140, margin=dict(l=5, r=5, t=5, b=5),
        annotations=[dict(text=display_text, x=0.5, y=0.5, font_size=18, showarrow=False, font_weight="bold", font_color=color)],
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# --- LOGIQUE D'IMPORTATION ---
def safe_parse(contents, filename):
    if not filename.lower().endswith('.csv'): return "ERROR_TYPE", None
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        return "SUCCESS", df.to_dict('records')
    except Exception: return "ERROR_READ", None

# --- VUES ---
def render_navbar(active_page="/"):
    return html.Div(style=styles['nav'], children=[
        dcc.Link("📁 Importation", href="/", style={**styles['nav_link'], 'color': ROSE_ALIA if active_page == "/" else "white"}),
        dcc.Link("📊 Dashboard de Biais", href="/graphique", style={**styles['nav_link'], 'color': ROSE_ALIA if active_page == "/graphique" else "white"}),
    ])

def render_index():
    return dbc.Container([
        html.H2("Bias Auditor", className="text-center pt-5 fw-bold", style={'color': BLEU_DARK}),
        html.P("Écart de biais par rapport à la moyenne globale (%)", className="text-center text-muted"),
        dbc.Row([
            dbc.Col([
                html.Label("📂 Fichier Réel", className="fw-bold"),
                dcc.Upload(id='upload-reel', children=html.Div(id='content-reel', children="Glisser-déposer CSV"), 
                           style={'border': '2px dashed #cbd5e1', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': 'white'})
            ], width=6),
            dbc.Col([
                html.Label("📂 Fichier Généré", className="fw-bold"),
                dcc.Upload(id='upload-genere', children=html.Div(id='content-genere', children="Glisser-déposer CSV"),
                           style={'border': '2px dashed #cbd5e1', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': 'white'})
            ], width=6),
        ], className="mt-4"),
        html.Div(id='dynamic-menu-content', style={'maxWidth': '600px', 'margin': '40px auto'}),
        html.Div(dcc.Link(dbc.Button("Lancer l'Analyse", color="danger", size="lg"), href="/graphique"), className="text-center pb-5")
    ])

def render_graph_page():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H3("Rapport d'Audit : Écart de Biais", className="fw-bold", style={'color': BLEU_DARK}), width=9),
            dbc.Col(dbc.Button("📥 Rapport PDF", id="btn-pdf", color="danger", className="w-100"), width=3),
        ], className="py-4 align-items-center"),
        dbc.Row(id='individual-bias-cards', className="g-4"),
        dbc.Row([
            dbc.Col(html.Div(style={**styles['card_dashboard'], 'marginTop': '30px', 'textAlign': 'left'}, children=[
                html.H5("Évolution du Biais Relatif", className="fw-bold"),
                html.P("0% signifie que le biais est égal à la moyenne. Un score positif indique un biais plus élevé que la normale.", className="text-muted small"),
                dcc.Dropdown(id='dropdown-colonne', className="my-3"),
                dcc.Graph(id='graph-biais-unique')
            ]), width=12)
        ], className="pb-5"),
        dcc.Download(id="download-pdf-report")
    ], fluid=True)

# --- CALLBACKS GESTION PAGES & UPLOAD ---
@app.callback([Output('page-content', 'children'), Output('nav-container', 'children')], Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/graphique': return render_graph_page(), render_navbar("/graphique")
    return render_index(), render_navbar("/")

@app.callback([Output('content-reel', 'children'), Output('df_real_store', 'data')], Input('upload-reel', 'contents'), State('upload-reel', 'filename'))
def up_reel(c, f):
    if not c: return "Glisser-déposer CSV", dash.no_update
    s, d = safe_parse(c, f)
    return (html.B(f"✅ {f}", style={'color': VERT_VALIDE}), d) if s == "SUCCESS" else (html.B("❌ Erreur", style={'color': ROUGE_CRITIQUE}), None)

@app.callback([Output('content-genere', 'children'), Output('df_gen_store', 'data')], Input('upload-genere', 'contents'), State('upload-genere', 'filename'))
def up_gen(c, f):
    if not c: return "Glisser-déposer CSV", dash.no_update
    s, d = safe_parse(c, f)
    return (html.B(f"✅ {f}", style={'color': VERT_VALIDE}), d) if s == "SUCCESS" else (html.B("❌ Erreur", style={'color': ROUGE_CRITIQUE}), None)

# --- CALLBACK MENU DE SÉLECTION ---
@app.callback(Output('dynamic-menu-content', 'children'), [Input('df_real_store', 'data'), Input('selected-columns-store', 'data')])
def update_menu(data, selected):
    if not data: return html.Div("Veuillez importer les fichiers...", className="text-muted text-center")
    df = pd.DataFrame(data)
    options = ['none'] + [c for c in df.columns if c != df.columns[0]]
    return [html.Div("Tout Sélectionner" if c == 'none' else c, id={'type': 'menu-item', 'index': c},
                     style={**styles['menu_item'], **(styles['menu_item_selected'] if c in selected else {})}) for c in options]

@app.callback(Output('selected-columns-store', 'data'), Input({'type': 'menu-item', 'index': ALL}, 'n_clicks'), State('selected-columns-store', 'data'), prevent_initial_call=True)
def handle_menu_click(n, current):
    ctx = dash.callback_context
    if not ctx.triggered: return current
    try:
        clicked = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])['index']
    except: return current
    if clicked == 'none': return ['none']
    new = [c for c in current if c != 'none']
    if clicked in new: new.remove(clicked)
    else: new.append(clicked)
    return new if new else ['none']

# --- CALLBACK DASHBOARD ---
@app.callback(
    [Output('individual-bias-cards', 'children'), Output('graph-biais-unique', 'figure'), 
     Output('dropdown-colonne', 'options'), Output('dropdown-colonne', 'value')],
    [Input('df_real_store', 'data'), Input('df_gen_store', 'data'), 
     Input('selected-columns-store', 'data'), Input('dropdown-colonne', 'value')]
)
def update_results(data_r, data_g, selected, drop_val):
    if not data_r or not data_g or not selected: return [], go.Figure(), [], None
    
    df_r, df_g = pd.DataFrame(data_r), pd.DataFrame(data_g)
    ref_name = df_r.columns[0]
    
    if 'none' in selected:
        targets = [c for c in df_r.columns if c in df_g.columns and c != ref_name]
    else:
        targets = [c for c in selected if c in df_r.columns and c in df_g.columns and c != ref_name]
    
    if not targets: return [], go.Figure(), [], None

    try:
        dg_ref = creation_de_ref(df_g[[ref_name]+targets], ref_name)
        dr_ref = creation_de_ref(df_r[[ref_name]+targets], ref_name)
        
        bt = pd.DataFrame()
        for v in dg_ref["ref"].unique():
            sr = selection_valeur_ref_gen(v, dr_ref.drop(ref_name, axis=1))
            if not sr.empty:
                sr["ratio"] = calcul_ratio(sr, v)
                step = biais_moyen(
                    data_sans_biais=sr, 
                    data_ref=dg_ref[dg_ref["ref"] == v].drop(ref_name, axis=1),
                    df_reel_complet=df_r,
                    df_gen_complet=df_g
                )
                step["ref"] = v
                bt = pd.concat([bt, step])
        
        res = bt.groupby("ref", as_index=False).mean(numeric_only=True)
    except Exception as e:
        return [], go.Figure(), [], None

    cols = [c for c in res.columns if c != 'ref']
    cards = []
    for c in cols:
        val_moyenne = res[c].mean()
        cards.append(dbc.Col(html.Div(style=styles['card_dashboard'], children=[
            html.B(c, style={'color': BLEU_DARK}),
            dcc.Graph(figure=create_donut_chart(val_moyenne), config={'displayModeBar': False}),
            html.P("Écart vs Moyenne Globale", className="text-muted small")
        ]), width=12, md=4))

    d_val = drop_val if drop_val in cols else cols[0]
    
    # Transformation des données pour le graphique linéaire : (valeur - 1) * 100
    res_plot = res.copy()
    res_plot[d_val] = (res_plot[d_val] - 1) * 100
    
    fig_line = px.line(res_plot, x="ref", y=d_val, markers=True, color_discrete_sequence=[ROSE_ALIA])
    fig_line.add_hline(y=0, line_dash="dash", line_color=VERT_VALIDE, annotation_text="Moyenne Globale (0%)")
    fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                           xaxis_title=f"Référence ({ref_name})", yaxis_title="Écart de Biais (%)")
    
    return cards, fig_line, [{'label': c, 'value': c} for c in cols], d_val

if __name__ == '__main__':
    app.run(debug=True)