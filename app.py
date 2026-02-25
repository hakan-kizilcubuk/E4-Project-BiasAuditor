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
ORANGE_MOYEN = "#f59e0b"
GRIS_FOND = "#f8fafc"

styles = {
    'nav': {'backgroundColor': BLEU_DARK, 'padding': '15px', 'display': 'flex', 'justifyContent': 'center', 'gap': '30px'},
    'nav_link': {'color': 'white', 'textDecoration': 'none', 'fontSize': '16px', 'fontWeight': '500'},
    'card_dashboard': {
        'borderRadius': '12px', 'boxShadow': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
        'backgroundColor': 'white', 'padding': '20px', 'height': '100%', 'textAlign': 'center',
        'position': 'relative', 'border': '2px solid transparent' # Border par défaut
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

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='df_real_store', storage_type='session'),
    dcc.Store(id='df_gen_store', storage_type='session'),
    dcc.Store(id='selected-columns-store', data=['none'], storage_type='session'),
    html.Div(id='nav-container'),
    html.Div(id='page-content', style={'backgroundColor': GRIS_FOND, 'minHeight': '92vh'})
])

# --- FONCTION GRAPHIQUE DONUT ---
def create_donut_chart(ecart_pourcent, color):  
    fig = go.Figure(data=[go.Pie(
        values=[ecart_pourcent, max(0, 100 - ecart_pourcent)], 
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
        html.P("Analyse de l'écart de biais absolu (%)", className="text-center text-muted"),
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
                html.P("Analyse temporelle/séquentielle de l'écart.", className="text-muted small"),
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
    if not data_r or not data_g or not selected:
        return [], go.Figure(), [], None
    
    df_r, df_g = pd.DataFrame(data_r), pd.DataFrame(data_g)
    
    # Pour l'audit, on utilise la première colonne (souvent 'age') comme référence
    ref_name = df_r.columns[0]
    
    # Sélection des colonnes cibles (on retire la référence)
    if 'none' in selected:
        targets = [c for c in df_r.columns if c in df_g.columns and c != ref_name]
    else:
        targets = [c for c in selected if c in df_r.columns and c in df_g.columns and c != ref_name]
    
    if not targets:
        return [], go.Figure(), [], None

    try:
        # 1. Préparation des références
        dg_ref = creation_de_ref(df_g[[ref_name]+targets], ref_name)
        dr_ref = creation_de_ref(df_r[[ref_name]+targets], ref_name)
        
        # 2. Calcul des scores de biais pour les cartes (Donuts)
        bt = pd.DataFrame()
        comparison_list = [] # Pour stocker les moyennes de comparaison

        for v in dg_ref["ref"].unique():
            # Trouver les correspondances dans le réel pour cette référence
            sr = selection_valeur_ref_gen(v, dr_ref.drop(ref_name, axis=1)).copy()
            
            if not sr.empty:
                # Calcul du ratio hybride (Exact ou Voisins)
                sr.loc[:, "ratio"] = calcul_ratio(sr, v)
                
                # Calcul de l'erreur adaptative
                step = biais_moyen(
                    data_sans_biais=sr, 
                    data_ref=dg_ref[dg_ref["ref"] == v].drop(ref_name, axis=1),
                    df_reel_complet=df_r,
                    df_gen_complet=df_g
                )
                step["ref"] = v
                bt = pd.concat([bt, step], ignore_index=True)

                # --- PRÉPARATION DES MOYENNES POUR LE GRAPHIQUE ---
                real_rows = dr_ref[dr_ref["ref"] == v]
                gen_rows = dg_ref[dg_ref["ref"] == v]
                
                row_stats = {"ref": v}
                for col in targets:
                    row_stats[f"{col}_Réel"] = real_rows[col].mean()
                    row_stats[f"{col}_Généré"] = gen_rows[col].mean()
                comparison_list.append(row_stats)
        
        # Moyenne globale des erreurs pour les Donuts
        res_errors = bt.groupby("ref", as_index=False).mean(numeric_only=True)
        # DataFrame pour les courbes de comparaison
        df_comp = pd.DataFrame(comparison_list).sort_values("ref")

    except Exception as e:
        print(f"Erreur de calcul : {e}")
        return [], go.Figure(), [], None

    # --- GÉNÉRATION DES CARTES (DONUTS) ---
    cards = []
    for c in targets:
        val_erreur_moyenne = res_errors[c].mean() if c in res_errors.columns else 0
        
        if val_erreur_moyenne <= 15:
            statut, color, border = "OK", VERT_VALIDE, "transparent"
        elif val_erreur_moyenne <= 40:
            statut, color, border = "MOYEN", ORANGE_MOYEN, "transparent"
        else:
            statut, color, border = "CRITIQUE", ROUGE_CRITIQUE, ROUGE_CRITIQUE
        
        cards.append(dbc.Col(html.Div(style={**styles['card_dashboard'], 'borderColor': border}, children=[
            html.Span(statut, style={**styles['badge'], 'backgroundColor': color}),
            html.B(c, style={'color': BLEU_DARK}),
            dcc.Graph(figure=create_donut_chart(val_erreur_moyenne, color), config={'displayModeBar': False}),
            html.P("Écart de Fidélité Moyen", className="text-muted small")
        ]), width=12, md=4))

    # --- GÉNÉRATION DU GRAPHIQUE LINÉAIRE COMPARATIF ---
    d_val = drop_val if (drop_val and f"{drop_val}_Réel" in df_comp.columns) else targets[0]
    
    fig_line = go.Figure()
    
    # Courbe RÉELLE (Vérité terrain)
    fig_line.add_trace(go.Scatter(
        x=df_comp["ref"], y=df_comp[f"{d_val}_Réel"],
        mode='lines+markers', name='Réel (Source)',
        line=dict(color=BLEU_DARK, width=3),
        hovertemplate="Âge: %{x}<br>Réel: %{y:.2f}"
    ))

    # Courbe GÉNÉRÉE (Production IA)
    fig_line.add_trace(go.Scatter(
        x=df_comp["ref"], y=df_comp[f"{d_val}_Généré"],
        mode='lines+markers', name='Généré (Synthétique)',
        line=dict(color=ROSE_ALIA, width=3, dash='dash'),
        hovertemplate="Âge: %{x}<br>Généré: %{y:.2f}"
    ))

    fig_line.update_layout(
        title=f"Comparaison des distributions : {d_val}",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        xaxis_title=f"Référence ({ref_name})", 
        yaxis_title="Valeur Moyenne",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Ajout d'une grille légère pour la lisibilité
    fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e2e8f0')
    fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e2e8f0')
    
    return cards, fig_line, [{'label': c, 'value': c} for c in targets], d_val
if __name__ == '__main__':
    app.run(debug=True)