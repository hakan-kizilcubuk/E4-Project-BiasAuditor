import dash
from dash import dcc, html, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import base64
import io
import json
from scipy.stats import ks_2samp

# --- IMPORT CUSTOM MODULES ---
from src.utils import THEMES_COLORS, STATUS_COLORS, calculate_skewness, calculate_entropy, calculate_global_score
from src.auditor import run_fairness_audit
from src.reporting import generate_pdf_bytes
from src.pages.import_page import render_import_layout
from src.pages.dashboard_page import render_dashboard_layout, create_individual_card
from src.pages.admin_page import render_admin_layout
from fonction_des_donné import (
    creation_de_ref, 
    moyenne_par_colone_référance
)

# --- APP INITIALIZATION ---
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP], 
    suppress_callback_exceptions=True
)

# --- MAIN VIEWPORT LAYOUT ---
app.layout = html.Div(id="main-viewport", children=[
    dcc.Location(id='url', refresh=False),
    
    # Session & Local Storage
    dcc.Store(id='df_real_store', storage_type='session'),
    dcc.Store(id='df_gen_store', storage_type='session'),
    dcc.Store(id='selected-columns-store', data=['none'], storage_type='session'),
    dcc.Store(id='settings-store', data={'theme': 'sombre', 'thresholds': [15, 40]}, storage_type='local'),
    
    dcc.Download(id="download-pdf-report"),

    html.Div(id='nav-container'),
    html.Div(id='page-content', style={'minHeight': '92vh'})
])

# --- HELPER: DONUT CHART GENERATION ---
def generate_donut(value, color, text_color):
    """Generates the visual donut representation of bias."""
    fig = go.Figure(data=[go.Pie(
        values=[value, max(0.1, 100 - value)], 
        hole=.75, marker_colors=[color, "rgba(200, 200, 200, 0.2)"],
        textinfo='none', hoverinfo='none'
    )])
    fig.update_layout(
        showlegend=False, height=120, margin=dict(l=2, r=2, t=2, b=2),
        annotations=[dict(text=f"{value:.1f}%", x=0.5, y=0.5, font_size=16, showarrow=False, font_weight="bold", font_color=text_color)],
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- NAVIGATION BAR RENDERER ---
def render_navbar(active_page, theme_key):
    t = THEMES_COLORS[theme_key]
    alia_color = STATUS_COLORS[theme_key]["alia"]
    return html.Div(style={'backgroundColor': t['nav'], 'padding': '15px', 'display': 'flex', 'justifyContent': 'center', 'gap': '30px'}, children=[
        dcc.Link("📁 Importation", href="/", style={'color': alia_color if active_page == "/" else "white", 'textDecoration': 'none', 'fontWeight': '500'}),
        dcc.Link("📊 Dashboard", href="/graphique", style={'color': alia_color if active_page == "/graphique" else "white", 'textDecoration': 'none', 'fontWeight': '500'}),
        dcc.Link("⚙️ Admin", href="/admin", style={'color': alia_color if active_page == "/admin" else "white", 'textDecoration': 'none', 'fontWeight': '500'}),
    ])

# --- CALLBACKS: ROUTING ---
@app.callback(
    [Output('page-content', 'children'), Output('nav-container', 'children'), Output('main-viewport', 'style')],
    [Input('url', 'pathname'), Input('settings-store', 'data')]
)
def sync_ui(path, settings):
    tk = settings.get('theme', 'sombre')
    theme = THEMES_COLORS[tk]
    style = {'backgroundColor': theme['fond'], 'minHeight': '100vh', 'transition': '0.3s'}
    
    if path == '/graphique': content = render_dashboard_layout(tk)
    elif path == '/admin': content = render_admin_layout(settings)
    else: content = render_import_layout(tk)
    
    return content, render_navbar(path, tk), style

# --- CALLBACKS: DATA LOADING ---
def safe_parse(contents, filename):
    if not contents: return None, None
    content_string = contents.split(',')[1]
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    return "SUCCESS", df.to_dict('records')

@app.callback([Output('content-reel', 'children'), Output('df_real_store', 'data')], 
              Input('upload-reel', 'contents'), State('upload-reel', 'filename'))
def load_real_data(contents, filename):
    if not contents: return "Glisser CSV", dash.no_update
    res, data = safe_parse(contents, filename)
    return (f"✅ {filename}" if res else "❌ Erreur"), data

@app.callback([Output('content-genere', 'children'), Output('df_gen_store', 'data')], 
              Input('upload-genere', 'contents'), State('upload-genere', 'filename'))
def load_gen_data(contents, filename):
    if not contents: return "Glisser CSV", dash.no_update
    res, data = safe_parse(contents, filename)
    return (f"✅ {filename}" if res else "❌ Erreur"), data

# --- CALLBACKS: AUDIT & VISUALIZATION ---
@app.callback(
    [Output('individual-bias-cards', 'children'), Output('global-score-zone', 'children')],
    [Input('df_real_store', 'data'), Input('df_gen_store', 'data'), 
     Input('selected-columns-store', 'data'), Input('settings-store', 'data')]
)
def update_audit_results(data_r, data_g, selected, settings):
    if not data_r or not data_g: 
        return [html.Div("Veuillez importer les fichiers CSV pour commencer.", className="text-center mt-5", style={'color': '#94a3b8'})], ""
    
    tk = settings.get('theme', 'sombre')
    t, a = THEMES_COLORS[tk], STATUS_COLORS[tk]
    lim_v, lim_o = settings.get('thresholds', [15, 40])
    
    df_r, df_g = pd.DataFrame(data_r), pd.DataFrame(data_g)
    ref_col = df_r.columns[0]
    
    # Filtering columns
    num_cols = df_r.select_dtypes(include=['number']).columns
    targets = [c for c in num_cols if c in df_g.columns and c != ref_col]
    if 'none' not in selected:
        targets = [c for c in targets if c in selected]

    # Bias Calculation Logic
    df_r_ref = creation_de_ref(df_r[[ref_col] + targets], ref_col)
    df_g_ref = creation_de_ref(df_g[[ref_col] + targets], ref_col)
    df_m_r = moyenne_par_colone_référance(df_r_ref).set_index('ref')
    df_m_g = moyenne_par_colone_référance(df_g_ref).set_index('ref')
    
    common = df_m_r.index.intersection(df_m_g.index)
    df_bias = ((df_m_g.loc[common] - df_m_r.loc[common]).abs() / df_m_r.loc[common].replace(0, 1).abs()) * 100
    final_bias_scores = df_bias.mean()

    # Fairness Logic (Fairlearn)
    cat_cols = df_r.select_dtypes(include=['object']).columns
    sensitive = cat_cols[0] if len(cat_cols) > 0 else None
    spd = run_fairness_audit(df_r, targets[0], sensitive) if (sensitive and targets) else None

    # Global Score calculation
    g_score = calculate_global_score(final_bias_scores.mean(), 0.5, spd)
    
    score_widget = html.Div([
        html.Small("Score Global de Fidélité", style={'color': t['texte']}),
        html.H2(f"{g_score}%", style={'color': a['alia'], 'fontWeight': 'bold', 'margin': '0'})
    ], className="text-center p-2", style={'backgroundColor': t['card'], 'borderRadius': '10px', 'border': f'1px solid {t["border"]}'})

    # Card Generation
    cards = []
    for c in targets:
        bias = float(final_bias_scores[c])
        metrics = {
            'skewness': calculate_skewness(df_r[c]),
            'entropy': calculate_entropy(df_r[c]),
            'p_value': ks_2samp(df_r[c].dropna(), df_g[c].dropna())[1],
            'recommendation': "Stable" if bias < lim_v else ("Rééquilibrer" if bias < lim_o else "Action Requise")
        }
        
        status_color = a['ok'] if bias <= lim_v else (a['moy'] if bias <= lim_o else a['crit'])
        status_text = "OK" if bias <= lim_v else ("WARNING" if bias <= lim_o else "CRITIQUE")
        
        card = create_individual_card(c, bias, status_text, status_color, tk, metrics)
        # Inject the donut chart into the placeholder
        card.children.children.insert(2, dcc.Graph(figure=generate_donut(bias, status_color, t['texte']), config={'displayModeBar': False}))
        cards.append(card)
        
    return cards, score_widget

# --- CALLBACKS: EXPORT PDF ---
@app.callback(
    Output("download-pdf-report", "data"),
    Input("btn-pdf", "n_clicks"),
    [State('df_real_store', 'data'), State('selected-columns-store', 'data')],
    prevent_initial_call=True
)
def handle_pdf_export(n, data_r, selected):
    if not n or not data_r: return dash.no_update
    # Logic to bundle metrics for PDF
    report_data = [{'name': 'Audit Dataset', 'bias': 10.5, 'status': 'Warning', 'entropy': 1.1, 'skewness': 0.2}]
    pdf_content = generate_pdf_bytes(report_data)
    return dcc.send_bytes(pdf_content, "Alia_Bias_Audit_Report.pdf")

# --- CALLBACKS: ADMIN & SETTINGS ---
@app.callback([Output("admin-panel", "style"), Output("admin-lock-zone", "style"), Output("unlock-err", "children")],
              Input("btn-unlock", "n_clicks"), State("admin-pwd", "value"), prevent_initial_call=True)
def check_admin_pass(n, p):
    if p == "admin": return {"display": "block"}, {"display": "none"}, ""
    return {"display": "none"}, {"display": "block"}, "Mot de passe incorrect."

@app.callback(Output('settings-store', 'data'), Input('btn-save', 'n_clicks'), 
              [State('theme-sel', 'value'), State('admin-slider', 'value')], prevent_initial_call=True)
def update_settings(n, theme, thresholds):
    return {'theme': theme, 'thresholds': sorted(thresholds)}

if __name__ == '__main__':
    app.run(debug=True)