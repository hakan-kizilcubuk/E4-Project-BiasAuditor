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
    moyenne_par_colone_référance,
    generate_pdf_report
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# --- PALETTE & STYLES ---
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
        'backgroundColor': 'white', 'padding': '20px', 'height': '100%'
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

# --- UTILS ---
def create_donut_chart(label, value):
    percentage = min(max(value * 100, 0), 100)
    color = VERT_VALIDE
    if percentage > 20: color = "#f59e0b"
    if percentage > 50: color = ROUGE_CRITIQUE
    fig = go.Figure(data=[go.Pie(values=[percentage, 100 - percentage], hole=.75, marker_colors=[color, "#e2e8f0"], textinfo='none', hoverinfo='none')])
    fig.update_layout(showlegend=False, height=150, margin=dict(l=10, r=10, t=10, b=10),
        annotations=[dict(text=f"{percentage:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False, font_weight="bold", font_color=color)],
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def safe_parse(contents, filename):
    if not filename.lower().endswith('.csv'):
        return "ERROR_TYPE", None
    try:
        data = pd.read_csv(io.StringIO(base64.b64decode(contents.split(',')[1]).decode('utf-8'))).to_dict('records')
        return "SUCCESS", data
    except Exception as e:
        print(f"Erreur lecture: {e}")
        return "ERROR_READ", None

# --- VUES ---
def render_navbar(active_page="/"):
    return html.Div(style=styles['nav'], children=[
        dcc.Link("📁 Importation", href="/", style={**styles['nav_link'], 'color': ROSE_ALIA if active_page == "/" else "white"}),
        dcc.Link("📊 Dashboard de Biais", href="/graphique", style={**styles['nav_link'], 'color': ROSE_ALIA if active_page == "/graphique" else "white"}),
    ])

def render_index():
    return dbc.Container([
        html.Div([
            html.H2("Bias Auditor", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': BLEU_DARK, 'paddingTop': '30px'}),
            html.P("Système de validation de données synthétiques", style={'textAlign': 'center', 'color': '#64748b'}),
        ]),
        dbc.Row([
            dbc.Col([
                html.Label("📂 Fichier Réel (CSV)", style={'fontWeight': 'bold'}),
                dcc.Upload(id='upload-reel', children=html.Div(id='content-reel', children="Déposer le CSV"), 
                           style={'border': '2px dashed #cbd5e1', 'borderRadius': '10px', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': 'white', 'cursor': 'pointer'})
            ], width=6),
            dbc.Col([
                html.Label("📂 Fichier Généré (CSV)", style={'fontWeight': 'bold'}),
                dcc.Upload(id='upload-genere', children=html.Div(id='content-genere', children="Déposer le CSV"),
                           style={'border': '2px dashed #cbd5e1', 'borderRadius': '10px', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': 'white', 'cursor': 'pointer'})
            ], width=6),
        ], className="mt-4"),
        html.Div(id='menu-container', style={'maxWidth': '600px', 'margin': '40px auto'}, children=[
            html.H5("Variables à auditer :", style={'color': BLEU_DARK}),
            html.Div(id='dynamic-menu-content')
        ]),
        html.Div([dcc.Link(dbc.Button("Lancer l'Analyse →", color="danger", size="lg", style={'borderRadius': '30px'}), href="/graphique")], style={'textAlign': 'center', 'paddingBottom': '40px'})
    ])

def render_graph_page():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H3("Rapport d'Audit des Biais", style={'fontWeight': 'bold', 'color': BLEU_DARK}), width=9),
            dbc.Col(dbc.Button("📥 Télécharger PDF", id="btn-pdf", color="danger", className="w-100"), width=3),
        ], className="py-4 align-items-center"),
        dbc.Row(id='individual-bias-cards', className="g-4"),
        dbc.Row([
            dbc.Col(html.Div(style={**styles['card_dashboard'], 'marginTop': '30px'}, children=[
                html.H5("Analyse détaillée par point de référence", style={'fontWeight': 'bold'}),
                dcc.Dropdown(id='dropdown-colonne', className="my-3"),
                dcc.Graph(id='graph-biais-unique')
            ]), width=12)
        ], className="pb-5"),
        dcc.Download(id="download-pdf-report")
    ], fluid=True)

# --- CALLBACKS ---

@app.callback([Output('page-content', 'children'), Output('nav-container', 'children')], Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/graphique':
        return render_graph_page(), render_navbar("/graphique")
    return render_index(), render_navbar("/")

@app.callback([Output('content-reel', 'children'), Output('df_real_store', 'data')], [Input('upload-reel', 'contents')], [State('upload-reel', 'filename')])
def update_reel(c, f):
    if not c: return "Déposer le CSV", dash.no_update
    status, data = safe_parse(c, f)
    if status == "ERROR_TYPE": return html.B("❌ Format .csv requis", style={'color': ROUGE_CRITIQUE}), None
    if status == "ERROR_READ": return html.B("❌ CSV illisible", style={'color': ROUGE_CRITIQUE}), None
    return html.B(f"✅ {f}", style={'color': VERT_VALIDE}), data

@app.callback([Output('content-genere', 'children'), Output('df_gen_store', 'data')], [Input('upload-genere', 'contents')], [State('upload-genere', 'filename')])
def update_genere(c, f):
    if not c: return "Déposer le CSV", dash.no_update
    status, data = safe_parse(c, f)
    if status == "ERROR_TYPE": return html.B("❌ Format .csv requis", style={'color': ROUGE_CRITIQUE}), None
    if status == "ERROR_READ": return html.B("❌ CSV illisible", style={'color': ROUGE_CRITIQUE}), None
    return html.B(f"✅ {f}", style={'color': VERT_VALIDE}), data

@app.callback(Output('dynamic-menu-content', 'children'), [Input('df_real_store', 'data'), Input('selected-columns-store', 'data')])
def update_menu_ui(data, selected):
    if not data: return html.Div("Importez un fichier...", className="text-muted")
    df = pd.DataFrame(data)
    options = ['none'] + df.columns.tolist()
    return [html.Div("Tout selectionner" if c == 'none' else c, id={'type': 'menu-item', 'index': c},
                     style={**styles['menu_item'], **(styles['menu_item_selected'] if c in selected else {})}) for c in options]

@app.callback(
    Output('selected-columns-store', 'data'), 
    Input({'type': 'menu-item', 'index': ALL}, 'n_clicks'), 
    State('selected-columns-store', 'data'), 
    prevent_initial_call=True
)
def handle_click(n, current):
    ctx = dash.callback_context
    if not ctx.triggered: return current
    
    # Extraction sécurisée de l'ID cliqué
    try:
        target_id = ctx.triggered[0]['prop_id'].split('.')[0]
        clicked = json.loads(target_id)['index']
    except: return current

    if clicked == 'none': return ['none']
    
    new = [c for c in current if c != 'none']
    if clicked in new: new.remove(clicked)
    else: new.append(clicked)
    return new if new else ['none']

@app.callback(
    [Output('individual-bias-cards', 'children'), Output('graph-biais-unique', 'figure'), 
     Output('dropdown-colonne', 'options'), Output('dropdown-colonne', 'value')],
    [Input('df_real_store', 'data'), Input('df_gen_store', 'data'), 
     Input('selected-columns-store', 'data'), Input('dropdown-colonne', 'value')]
)
def update_dashboard(data_real, data_gen, selected, dropdown_val):
    if not data_real or not data_gen or not selected:
        return [], go.Figure(), [], None
    
    df_r, df_g = pd.DataFrame(data_real), pd.DataFrame(data_gen)
    ref = df_r.columns[0]
    
    # Logique "Tout sélectionner"
    if 'none' in selected:
        targets = [c for c in df_r.columns if c in df_g.columns and c != ref]
    else:
        targets = [c for c in selected if c in df_r.columns and c in df_g.columns and c != ref]
    
    if not targets: return [], go.Figure(), [], None

    try:
        dg_ref = creation_de_ref(df_g[[ref]+targets], ref)
        dr_ref = creation_de_ref(df_r[[ref]+targets], ref)
        bt = pd.DataFrame()
        for v in dg_ref["ref"].unique():
            sr = selection_valeur_ref_gen(v, dr_ref.drop(ref, axis=1))
            if not sr.empty:
                sr["ratio"] = calcul_ratio(sr, v)
                step = biais_moyen(sr, dg_ref[dg_ref["ref"] == v].drop(ref, axis=1))
                step["ref"] = v
                bt = pd.concat([bt, step])
        res = moyenne_par_colone_référance(bt)
    except Exception as e:
        print(f"Erreur calcul : {e}")
        return [], go.Figure(), [], None

    cols = [c for c in res.columns if c != 'ref']
    cards = []
    for c in cols:
        val = res[c].mean()
        critique = val > 0.5
        cards.append(dbc.Col(html.Div(style={**styles['card_dashboard'], 'border': f'2px solid {ROUGE_CRITIQUE}' if critique else 'none'}, children=[
            html.Div([html.B(c, style={'color': BLEU_DARK}), html.Span("CRITIQUE" if critique else "OK", style={'color': ROUGE_CRITIQUE if critique else VERT_VALIDE, 'fontSize': '12px', 'fontWeight': 'bold'})], style={'display': 'flex', 'justifyContent': 'space-between'}),
            dcc.Graph(figure=create_donut_chart(c, val), config={'displayModeBar': False})
        ]), width=12, md=6, lg=4))

    d_val = dropdown_val if dropdown_val in cols else cols[0]
    fig_line = px.line(res, x="ref", y=d_val, markers=True, color_discrete_sequence=[ROSE_ALIA])
    fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title=ref, yaxis_title="Indice de Biais")
    
    return cards, fig_line, [{'label': c, 'value': c} for c in cols], d_val

if __name__ == '__main__':
    app.run(debug=True)