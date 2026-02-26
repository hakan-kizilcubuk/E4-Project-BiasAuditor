import dash
from dash import dcc, html, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import base64
import io
import json
from fpdf import FPDF  # Pour le rapport PDF
from scipy.stats import ks_2samp  # Pour la significativité (p-value)

# --- IMPORTATION DES FONCTIONS ---
try:
    from fonction_des_donné import (
        creation_de_ref, 
        moyenne_par_colone_référance, 
        biais_moyen
    )
except ImportError:
    print("ERREUR: Impossible d'importer les fonctions. Utilisation de fonctions factices.")
    def creation_de_ref(*args): return pd.DataFrame({'ref': [1,2], 'col': [3,4]})
    def moyenne_par_colone_référance(*args): return pd.DataFrame({'ref': [1,2], 'col': [3,4]})
    def biais_moyen(*args): return pd.DataFrame({'col': [0.1]})

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# --- CONFIGURATION DES PALETTES ---
THEMES_COLORS = {
    "clair": {"fond": "#f8fafc", "texte": "#1e293b", "card": "white", "nav": "#1e293b", "border": "#cbd5e1"},
    "sombre": {"fond": "#0a192f", "texte": "#e2e8f0", "card": "#112240", "nav": "#020c1b", "border": "#1d2d50"},
    "daltonien": {"fond": "#fdf6e3", "texte": "#002b36", "card": "#eee8d5", "nav": "#073642", "border": "#93a1a1"}
}

STATUS_COLORS = {
    "clair": {"ok": "#10b981", "moy": "#f59e0b", "crit": "#ef4444", "alia": "#d8627a"},
    "sombre": {"ok": "#34d399", "moy": "#fbbf24", "crit": "#f87171", "alia": "#fb7185"},
    "daltonien": {"ok": "#268bd2", "moy": "#b58900", "crit": "#dc322f", "alia": "#d33682"}
}

def create_donut_chart(ecart_pourcent, color, text_color):
    fig = go.Figure(data=[go.Pie(
        values=[ecart_pourcent, max(0.1, 100 - ecart_pourcent)], 
        hole=.75, marker_colors=[color, "rgba(200, 200, 200, 0.2)"],
        textinfo='none', hoverinfo='none'
    )])
    fig.update_layout(
        showlegend=False, height=120, margin=dict(l=2, r=2, t=2, b=2),
        annotations=[dict(text=f"{ecart_pourcent:.1f}%", x=0.5, y=0.5, font_size=16, showarrow=False, font_weight="bold", font_color=text_color)],
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def safe_parse(contents, filename):
    if not filename or not filename.lower().endswith('.csv'): return "ERROR_TYPE", None
    try:
        content_string = contents.split(',')[1]
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        return "SUCCESS", df.to_dict('records')
    except Exception: return "ERROR_READ", None

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div(id="main-viewport", children=[
    dcc.Location(id='url', refresh=False),
    html.Div(id={'type': 'menu-item', 'index': '_permanent_placeholder'}, style={'display': 'none'}),
    
    dcc.Store(id='df_real_store', storage_type='session'),
    dcc.Store(id='df_gen_store', storage_type='session'),
    dcc.Store(id='selected-columns-store', data=['none'], storage_type='session'),
    dcc.Store(id='settings-store', data={'theme': 'sombre', 'thresholds': [15, 40]}, storage_type='local'),
    
    dcc.Download(id="download-pdf-report"), # Composant pour l'export

    html.Div(id='nav-container'),
    html.Div(id='page-content', style={'minHeight': '92vh'})
])

def render_navbar(active_page, theme_key):
    t = THEMES_COLORS[theme_key]
    alia_color = STATUS_COLORS[theme_key]["alia"]
    return html.Div(style={'backgroundColor': t['nav'], 'padding': '15px', 'display': 'flex', 'justifyContent': 'center', 'gap': '30px'}, children=[
        dcc.Link("📁 Importation", href="/", style={'color': alia_color if active_page == "/" else "white", 'textDecoration': 'none', 'fontSize': '16px', 'fontWeight': '500'}),
        dcc.Link("📊 Dashboard", href="/graphique", style={'color': alia_color if active_page == "/graphique" else "white", 'textDecoration': 'none', 'fontSize': '16px', 'fontWeight': '500'}),
        dcc.Link("⚙️ Admin", href="/admin", style={'color': alia_color if active_page == "/admin" else "white", 'textDecoration': 'none', 'fontSize': '16px', 'fontWeight': '500'}),
    ])

def render_index(theme_key):
    t = THEMES_COLORS[theme_key]
    return dbc.Container([
        html.H2("Alia Bias Auditor", className="text-center pt-5 fw-bold", style={'color': t['texte']}),
        dbc.Row([
            dbc.Col([
                html.Label("📂 Fichier Réel (Source)", className="fw-bold", style={'color': t['texte']}),
                dcc.Upload(id='upload-reel', children=html.Div(id='content-reel', children="Glisser CSV", style={'color': t['texte']}), 
                           style={'border': f'2px dashed {t["border"]}', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': t['card'], 'borderRadius': '10px'})
            ], width=6),
            dbc.Col([
                html.Label("📂 Fichier Généré (IA)", className="fw-bold", style={'color': t['texte']}),
                dcc.Upload(id='upload-genere', children=html.Div(id='content-genere', children="Glisser CSV", style={'color': t['texte']}),
                           style={'border': f'2px dashed {t["border"]}', 'padding': '30px', 'textAlign': 'center', 'backgroundColor': t['card'], 'borderRadius': '10px'})
            ], width=6),
        ], className="mt-4"),
        html.Div(id='dynamic-menu-content', style={'maxWidth': '600px', 'margin': '40px auto'}),
        html.Div(dcc.Link(dbc.Button("Lancer l'Audit", color="danger", size="lg", className="px-5"), href="/graphique"), className="text-center pb-5")
    ])

def render_admin_page(settings):
    tk = settings['theme']
    t = THEMES_COLORS[tk]
    return dbc.Container([
        html.H2("🔐 Administration", className="text-center pt-5", style={'color': t['texte']}),
        html.Div(id="admin-lock-zone", style={"maxWidth": "400px", "margin": "auto"}, children=[
            dbc.Input(id="admin-pwd", type="password", placeholder="Code 'admin'...", className="mb-2"),
            dbc.Button("Accéder", id="btn-unlock", color="primary", className="w-100"),
            html.Div(id="unlock-err", className="text-danger mt-2")
        ]),
        html.Div(id="admin-panel", style={"display": "none"}, children=[
            html.Hr(style={'borderColor': t['border']}),
            dbc.Row([
                dbc.Col([
                    html.Label("Mode d'affichage", style={'color': t['texte']}),
                    dcc.Dropdown(id='theme-sel', options=[
                        {'label': '☀️ Clair', 'value': 'clair'},
                        {'label': '🌙 Sombre', 'value': 'sombre'},
                        {'label': '👁️ Daltonien', 'value': 'daltonien'}
                    ], value=tk)
                ], width=4),
                dbc.Col([
                    html.Label("Seuils par défaut (%)", style={'color': t['texte']}),
                    dcc.RangeSlider(
                        id='admin-slider', min=0, max=100, value=settings['thresholds'], 
                        allowCross=False, step=1, pushable=1,
                        marks={i: {'label': f'{i}%', 'style': {'color': t['texte']}} for i in [0, 25, 50, 75, 100]},
                        tooltip={"always_visible": True, "placement": "top"}
                    )
                ], width=8)
            ]),
            dbc.Button("Enregistrer les réglages", id="btn-save", color="success", className="mt-4 w-100")
        ])
    ])

def render_graph_page(theme_key):
    t = THEMES_COLORS[theme_key]
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H3("Rapport d'Audit : Fidélité par Référence", className="py-4 fw-bold", style={'color': t['texte']}), width=8),
            dbc.Col(dbc.Button("📄 Exporter PDF", id="btn-pdf", color="info", className="mt-4"), width=4, className="text-end")
        ]),
        dbc.Row(id='individual-bias-cards', className="g-4 pb-5"), 
    ], fluid=True)

# --- CALLBACKS ---

@app.callback(
    [Output('page-content', 'children'), Output('nav-container', 'children'), Output('main-viewport', 'style')],
    [Input('url', 'pathname'), Input('settings-store', 'data')]
)
def sync_ui(path, settings):
    tk = settings.get('theme', 'sombre')
    theme = THEMES_COLORS[tk]
    style = {'backgroundColor': theme['fond'], 'minHeight': '100vh', 'transition': '0.3s'}
    if path == '/graphique': content = render_graph_page(tk)
    elif path == '/admin': content = render_admin_page(settings)
    else: content = render_index(tk)
    return content, render_navbar(path, tk), style

@app.callback(Output('dynamic-menu-content', 'children'), [Input('df_real_store', 'data'), Input('selected-columns-store', 'data'), Input('settings-store', 'data')])
def update_menu(data, selected, settings):
    if not data: return html.Div("Veuillez importer les fichiers...", className="text-center", style={'color': '#94a3b8'})
    df = pd.DataFrame(data)
    tk = settings['theme']
    t = THEMES_COLORS[tk]
    alia = STATUS_COLORS[tk]["alia"]
    options = ['none'] + [c for c in df.columns if c != df.columns[0]]
    
    items = []
    for c in options:
        is_sel = c in selected
        if tk == "sombre":
            bg_color = alia if is_sel else t['card']
            text_col = "white" if is_sel else t['texte']
        else:
            bg_color = "#ffe4e6" if is_sel else "#ffffff"
            text_col = alia if is_sel else "#1e293b"
        
        style = {
            'padding': '12px 20px', 'margin': '5px 0', 'borderRadius': '6px', 'cursor': 'pointer',
            'border': f'1px solid {alia if is_sel else t["border"]}',
            'backgroundColor': bg_color, 'color': text_col,
            'fontWeight': 'bold' if is_sel else 'normal', 'transition': '0.2s',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.05)' if not is_sel else 'none'
        }
        items.append(html.Div(c if c != 'none' else "Tout Sélectionner", id={'type': 'menu-item', 'index': c}, style=style))
    return items

@app.callback(
    Output('individual-bias-cards', 'children'),
    [Input('df_real_store', 'data'), Input('df_gen_store', 'data'), 
     Input('selected-columns-store', 'data'), Input('settings-store', 'data')]
)
def update_results(data_r, data_g, selected, settings):
    if not data_r or not data_g: 
        return [html.Div("Veuillez importer les fichiers CSV.", className="text-center mt-5")]
    
    tk = settings.get('theme', 'sombre')
    t, a = THEMES_COLORS[tk], STATUS_COLORS[tk]
    lim_v, lim_o = settings.get('thresholds', [15, 40])
    inner_bg = "#1a2f50" if tk == "sombre" else "#f8f9fa"
    
    df_r, df_g = pd.DataFrame(data_r), pd.DataFrame(data_g)
    ref = df_r.columns[0]

    try:
        # --- 1. SÉCURITÉ ENCODAGE TEXTE ---
        df_r_proc, df_g_proc = df_r.copy(), df_g.copy()
        label_mapping = {}
        if df_r_proc[ref].dtype == 'object' or df_r_proc[ref].dtype.name == 'category':
            labels = sorted(df_r_proc[ref].unique())
            label_mapping = {i: lbl for i, lbl in enumerate(labels)}
            rev_map = {lbl: i for i, lbl in enumerate(labels)}
            df_r_proc[ref] = df_r_proc[ref].map(rev_map)
            df_g_proc[ref] = df_g_proc[ref].map(rev_map)

        # --- 2. FILTRAGE ---
        numeric_cols = df_r_proc.select_dtypes(include=['number']).columns
        available_cols = [c for c in numeric_cols if c in df_g_proc.columns and c != ref]
        targets = available_cols if ('none' in selected or not selected) else [c for c in selected if c in available_cols]

        # --- 3. CALCULS ---
        df_r_ref = creation_de_ref(df_r_proc[[ref] + targets], ref)
        df_g_ref = creation_de_ref(df_g_proc[[ref] + targets], ref)
        df_m_r = moyenne_par_colone_référance(df_r_ref).sort_values(ref).set_index(ref).select_dtypes(include=['number'])
        df_m_g = moyenne_par_colone_référance(df_g_ref).sort_values(ref).set_index(ref).select_dtypes(include=['number'])
        
        common_idx = df_m_r.index.intersection(df_m_g.index)
        df_m_r_f, df_m_g_f = df_m_r.loc[common_idx], df_m_g.loc[common_idx]
        
        df_biais_local = ((df_m_g_f - df_m_r_f).abs() / df_m_r_f.replace(0, 1).abs()) * 100
        df_final_scores = df_biais_local.mean()
        display_idx = [label_mapping.get(i, i) for i in common_idx]

    except Exception as e:
        return [html.Div(f"Erreur : {str(e)}", className="text-danger mt-5")]

    cards = []
    for c in targets:
        val_moyen = float(df_final_scores[c])
        stat, p_val = ks_2samp(df_r[c].dropna(), df_g[c].dropna())
        std_r, std_g = df_r[c].std(), df_g[c].std()
        
        color = a['ok'] if val_moyen <= lim_v else (a['moy'] if val_moyen <= lim_o else a['crit'])
        statut = "OK" if val_moyen <= lim_v else ("WARNING" if val_moyen <= lim_o else "CRITIQUE")
        
        # --- TRANSPARENCE ULTRA-LÉGÈRE (0.1) ---
        # On s'assure que la couleur est bien convertie en RGBA
        import re
        rgba_match = re.search(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
        if rgba_match:
            r, g, b = rgba_match.groups()
            bias_rgba = f"rgba({r}, {g}, {b}, 0.1)"
        else:
            bias_rgba = color # Backup au cas où

        # --- GRAPHIQUE ---
        
        fig_detail = go.Figure()
        
        # Courbe Réelle
        fig_detail.add_trace(go.Scatter(x=display_idx, y=df_m_r_f[c], name='Réel',
                                        line=dict(color=t['texte'], width=2)))
        
        # Courbe IA
        fig_detail.add_trace(go.Scatter(x=display_idx, y=df_m_g_f[c], name='IA',
                                        line=dict(color=a['alia'], width=2, dash='dash')))
        
        # Ligne de Biais ULTRA TRANSPARENTE
        fig_detail.add_trace(go.Scatter(
            x=display_idx, y=df_biais_local[c], name='Biais %',
            line=dict(color=bias_rgba, width=1.5), # Ligne plus fine
            yaxis="y2", mode='lines', # On enlève les markers pour plus de légèreté
            hoverinfo="y+name",
            hovertemplate="Biais: %{y:.1f}%<extra></extra>"
        ))
        
        fig_detail.update_layout(
            height=250, margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=t['texte'], size=10),
            template="plotly_dark" if tk=="sombre" else "plotly_white",
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
            yaxis=dict(title="Valeur", showgrid=False),
            yaxis2=dict(title="Biais %", overlaying="y", side="right", showgrid=True, 
                        gridcolor='rgba(200,200,200,0.03)', # Grille quasi invisible
                        range=[0, max(100, df_biais_local[c].max()*1.1)])
        )

        # --- CARTE ---
        card_content = html.Div(style={
            'borderRadius': '15px', 'backgroundColor': t['card'], 'padding': '15px', 'textAlign': 'center', 'position': 'relative',
            'border': f'2px solid {color}' if statut == "CRITIQUE" else f'1px solid {t["border"]}',
            'boxShadow': '0 4px 12px rgba(0,0,0,0.2)'
        }, children=[
            html.Span(statut, style={'position': 'absolute', 'top': '10px', 'right': '10px', 'fontSize': '9px', 'fontWeight': 'bold', 
                                     'padding': '2px 10px', 'borderRadius': '20px', 'color': 'white', 'backgroundColor': color}),
            
            html.B(c, style={'color': t['texte'], 'fontSize': '1.1rem', 'display': 'block', 'marginBottom': '10px'}),
            
            dcc.Graph(figure=create_donut_chart(val_moyen, color, t['texte']), config={'displayModeBar': False}),
            
            html.Div([
                html.Small("Test Stat : ", style={'color': '#94a3b8'}),
                html.B("Fidèle" if p_val > 0.05 else "Divergent", style={'color': a['ok'] if p_val > 0.05 else a['crit'], 'fontSize': '11px'})
            ], className="mb-2"),

            dbc.Accordion([
                dbc.AccordionItem(title="🔍 Détails & Courbe de Biais", children=[
                    html.Div(style={'backgroundColor': inner_bg, 'padding': '12px', 'borderRadius': '10px'}, children=[
                        dbc.Row([
                            dbc.Col([html.Small("StdDev Réel", style={'fontSize': '10px'}), html.B(f"{std_r:.2f}", style={'display': 'block'})], width=6),
                            dbc.Col([html.Small("StdDev IA", style={'fontSize': '10px'}), html.B(f"{std_g:.2f}", style={'display': 'block', 'color': a['alia']})], width=6),
                        ], className="mb-3 text-center"),
                        dcc.Graph(figure=fig_detail, config={'displayModeBar': False})
                    ])
                ])
            ], start_collapsed=True, flush=True)
        ])
        
        cards.append(dbc.Col(card_content, width=12, md=6, lg=4, className="mb-4"))
        
    return cards

# --- CALLBACK EXPORT PDF ---
# --- CALLBACK EXPORT PDF (CORRIGÉ) ---
@app.callback(
    Output("download-pdf-report", "data"),
    Input("btn-pdf", "n_clicks"),
    [State('df_real_store', 'data'), 
     State('df_gen_store', 'data'), 
     State('selected-columns-store', 'data')],
    prevent_initial_call=True  # Empêche l'exécution au chargement de la page
)
def generate_pdf(n_clicks, data_r, data_g, selected):
    # Sécurité supplémentaire : si n_clicks est None ou 0, on ne fait rien
    if n_clicks is None or n_clicks == 0:
        return dash.no_update
        
    if not data_r or not data_g:
        return dash.no_update

    df_r, df_g = pd.DataFrame(data_r), pd.DataFrame(data_g)
    targets = [c for c in (df_r.columns[1:] if 'none' in selected else selected) if c in df_g.columns]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Rapport d'Audit - Alia Bias Auditor", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Variables analysees : {len(targets)}", ln=True)
    pdf.ln(5)

    for c in targets:
        # Calcul simple pour le rapport PDF
        mean_r = df_r[c].mean()
        biais = ((df_g[c].mean() - mean_r) / mean_r * 100) if mean_r != 0 else 0
        _, p_val = ks_2samp(df_r[c].dropna(), df_g[c].dropna())
        statut_p = "FIDELE" if p_val > 0.05 else "DIVERGENT"
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"Variable : {c}", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f" - Biais Relatif Moyen : {biais:.2f}%", ln=True)
        pdf.cell(0, 6, f" - Significativite (P-Value) : {p_val:.4f}", ln=True)
        pdf.cell(0, 6, f" - Conclusion Statistique : {statut_p}", ln=True)
        pdf.ln(4)

    # On retourne le flux binaire pour le téléchargement
    return dcc.send_bytes(pdf.output(dest='S').encode('latin-1'), "rapport_alia_bias.pdf")

@app.callback([Output('content-reel', 'children'), Output('df_real_store', 'data')], 
              Input('upload-reel', 'contents'), State('upload-reel', 'filename'), State('settings-store', 'data'))
def up_r(c, f, s):
    tk = s.get('theme', 'sombre')
    text_color = THEMES_COLORS[tk]['texte']
    if not c: return html.Div("Glisser CSV", style={'color': text_color}), dash.no_update
    res, d = safe_parse(c, f)
    color = STATUS_COLORS[tk]["ok"] if res == "SUCCESS" else STATUS_COLORS[tk]["crit"]
    return (html.Span(f"✅ {f}" if res == "SUCCESS" else f"❌ Erreur", style={'color': color, 'fontWeight': 'bold'}), d)

@app.callback([Output('content-genere', 'children'), Output('df_gen_store', 'data')], 
              Input('upload-genere', 'contents'), State('upload-genere', 'filename'), State('settings-store', 'data'))
def up_g(c, f, s):
    tk = s.get('theme', 'sombre')
    text_color = THEMES_COLORS[tk]['texte']
    if not c: return html.Div("Glisser CSV", style={'color': text_color}), dash.no_update
    res, d = safe_parse(c, f)
    color = STATUS_COLORS[tk]["ok"] if res == "SUCCESS" else STATUS_COLORS[tk]["crit"]
    return (html.Span(f"✅ {f}" if res == "SUCCESS" else f"❌ Erreur", style={'color': color, 'fontWeight': 'bold'}), d)

@app.callback(
    Output('selected-columns-store', 'data'), 
    Input({'type': 'menu-item', 'index': ALL}, 'n_clicks'), 
    State('selected-columns-store', 'data'), 
    prevent_initial_call=True
)
def handle_click(n, current):
    ctx = dash.callback_context
    if not ctx.triggered: return current
    clicked_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = json.loads(clicked_id_str)['index']
    
    if clicked_index == '_permanent_placeholder': return current
    if clicked_index == 'none': return ['none']
    
    new = [c for c in current if c != 'none']
    if clicked_index in new: new.remove(clicked_index)
    else: new.append(clicked_index)
    return new if new else ['none']

@app.callback([Output("admin-panel", "style"), Output("admin-lock-zone", "style"), Output("unlock-err", "children")],
              Input("btn-unlock", "n_clicks"), State("admin-pwd", "value"), prevent_initial_call=True)
def unlock(n, p):
    if p == "admin": return {"display": "block"}, {"display": "none"}, ""
    return {"display": "none"}, {"display": "block"}, "Accès refusé"

@app.callback(Output('settings-store', 'data'), Input('btn-save', 'n_clicks'), 
              [State('theme-sel', 'value'), State('admin-slider', 'value')], prevent_initial_call=True)
def save_config(n, th, sl):
    return {'theme': th, 'thresholds': sorted(sl)}

# Reset de la sélection quand un nouveau fichier est importé
@app.callback(
    Output('selected-columns-store', 'data', allow_duplicate=True),
    Input('df_real_store', 'data'),
    prevent_initial_call=True
)
def reset_selection(data):
    # Quand on charge un nouveau fichier, on remet la sélection sur "Tout Sélectionner"
    return ['none']


if __name__ == '__main__':
    app.run(debug=True, dev_tools_ui=False)