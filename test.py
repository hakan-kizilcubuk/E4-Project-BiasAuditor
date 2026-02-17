import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import base64
import io

# Importation de vos fonctions personnalisées
from lecture_des_donné import (
    creation_de_ref, 
    sélection_valeur_ref_gen, 
    ratio, 
    Biai_moyen, 
    moyenne_par_colone_référance
)

# Configuration de l'affichage console
pd.set_option('display.max_columns', None)  
pd.set_option('display.width', 1000)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# --- CONSTANTES ---
BLEU_FONCE = "#424d6d"
ROSE_LOGO = "#d8627a"
ROUGE_ERREUR = "#ff4d4d"

styles = {
    'main_container': {
        'height': '100vh', 'width': '100vw', 'margin': '0', 'padding': '0',
        'background': 'linear-gradient(155deg, #424d6d 50%, #ffffff 50.2%)',
        'fontFamily': 'sans-serif', 'position': 'relative', 'overflow': 'hidden'
    },
    'navbar': {
        'display': 'flex', 'justifyContent': 'center', 'gap': '50px',
        'padding': '20px', 'backgroundColor': BLEU_FONCE, 'fontSize': '18px'
    },
    'nav_link': {'color': 'white', 'textDecoration': 'none', 'padding': '0 10px'},
    'title_text': {
        'color': ROSE_LOGO, 'fontSize': '26px', 'fontWeight': 'bold',
        'textDecoration': 'underline', 'textAlign': 'center'
    },
    'upload_box': {
        'borderRadius': '15px', 'width': '280px', 'height': '100px',
        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
        'boxShadow': '0px 4px 15px rgba(0,0,0,0.2)', 'cursor': 'pointer', 'border': 'none',
        'margin': '0 auto'
    },
    'label_underline': {
        'borderBottom': f'3px solid {ROSE_LOGO}', 'width': '150px', 
        'margin': '0 auto 15px auto', 'paddingBottom': '5px'
    }
}

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # Stockage des données (JSON)
    dcc.Store(id='df_real_store', storage_type='memory'),
    dcc.Store(id='df_gen_store', storage_type='memory'),
    
    html.Div(id='nav-container'),
    html.Div(id='page-content')
])

# --- LOGIQUE DE DÉCODAGE ---
def parse_contents(contents, filename):
    if contents is None: return None
    _, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            return df.to_dict('records')
    except Exception: return None
    return None

# --- PAGES ---

def render_navbar(active_page="/"):
    return html.Div(style=styles['navbar'], children=[
        html.A("Accueil", href="https://alia-sante.com/", style=styles['nav_link']),
        dcc.Link("Fichier", href="/", style={**styles['nav_link'], 'fontWeight': 'bold' if active_page=="/" else 'normal'}),
        dcc.Link("Graphique", href="/graphique", style={**styles['nav_link'], 'fontWeight': 'bold' if active_page=="/graphique" else 'normal'}),
    ])

def render_index():
    return html.Div(style=styles['main_container'], children=[
        html.Div(style={'paddingTop': '40px'}, children=[
            html.H1("Bias Auditor – Détection et quantification des biais", style=styles['title_text']),
            html.H2("données réelles et synthétiques", style=styles['title_text']),
        ]),
        dbc.Container([
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div(style=styles['label_underline'], children=[html.B("Fichier réel", style={'color': 'white', 'fontSize': '20px'})]),
                    dcc.Upload(id='upload-reel', children=html.Div(id='content-reel'), style={**styles['upload_box'], 'backgroundColor': 'white'}),
                ]), width=6),
                dbc.Col(html.Div([
                    html.Div(style=styles['label_underline'], children=[html.B("Fichier générer", style={'color': BLEU_FONCE, 'fontSize': '20px'})]),
                    dcc.Upload(id='upload-genere', children=html.Div(id='content-genere'), style={**styles['upload_box'], 'backgroundColor': BLEU_FONCE}),
                ]), width=6),
            ], style={'marginTop': '220px'}),
            dbc.Row(dbc.Col(html.Div([
                dcc.Link(html.Button("Suivant", style={'backgroundColor': ROSE_LOGO, 'color': 'white', 'border': 'none', 'borderRadius': '10px', 'padding': '12px 60px', 'fontSize': '20px', 'marginTop': '80px'}), href="/graphique")
            ], style={'textAlign': 'center'}), width=12))
        ], fluid=True)
    ])

def render_graph_page():
    return html.Div(style={'padding': '40px', 'backgroundColor': '#f8f9fa', 'minHeight': '100vh'}, children=[
        html.H1("Analyse Statistique des Biais", style={'color': BLEU_FONCE, 'textAlign': 'center', 'marginBottom': '30px'}),
        
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Label("Sélectionnez la colonne à visualiser :", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='dropdown-colonne',
                        placeholder="Attente de données...",
                        style={'marginBottom': '20px'}
                    ),
                ], width={'size': 6, 'offset': 3})
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='graph-biais-unique'), width=12),
            ]),
        ]),
        
        html.Div(style={'textAlign': 'center', 'marginTop': '30px'}, children=[
            dcc.Link("← Retour aux fichiers", href="/", style={'color': ROSE_LOGO, 'fontSize': '18px'})
        ])
    ])

# --- CALLBACKS ---

@app.callback(
    [Output('page-content', 'children'), Output('nav-container', 'children')],
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/graphique':
        return render_graph_page(), render_navbar("/graphique")
    return render_index(), render_navbar("/")

@app.callback(
    [Output('content-reel', 'children'), Output('df_real_store', 'data')],
    [Input('upload-reel', 'contents'), Input('upload-reel', 'filename')]
)
def update_reel(c, f):
    if c is None:
        return html.Div([html.Img(src="https://img.icons8.com/ios-filled/50/d8627a/file.png", style={'width': '30px'}), " déposer"]), None
    if f.lower().endswith('.csv'):
        return html.Div([html.Span("➔", style={'color': ROSE_LOGO, 'fontSize': '25px'}), " Fichier déposé"]), parse_contents(c, f)
    return html.Div([html.Span("✘", style={'color': ROUGE_ERREUR}), " CSV Requis"]), None

@app.callback(
    [Output('content-genere', 'children'), Output('df_gen_store', 'data')],
    [Input('upload-genere', 'contents'), Input('upload-genere', 'filename')]
)
def update_genere(c, f):
    if c is None:
        return html.Div([html.Img(src="https://img.icons8.com/ios-filled/50/d8627a/file.png", style={'width': '30px'}), " déposer"], style={'color': 'white'}), None
    if f.lower().endswith('.csv'):
        return html.Div([html.Span("➔", style={'color': ROSE_LOGO, 'fontSize': '25px'}), " Fichier déposé"], style={'color': ROSE_LOGO}), parse_contents(c, f)
    return html.Div([html.Span("✘", style={'color': ROUGE_ERREUR}), " CSV Requis"], style={'color': ROUGE_ERREUR}), None

@app.callback(
    [Output('graph-biais-unique', 'figure'),
     Output('dropdown-colonne', 'options'),
     Output('dropdown-colonne', 'value')],
    [Input('df_real_store', 'data'),
     Input('df_gen_store', 'data'),
     Input('dropdown-colonne', 'value')]
)
def update_analysis(data_reel, data_genere, selected_col):
    # Initialisation par défaut
    fig = px.scatter(title="Veuillez charger les deux fichiers (Réel et Généré)")
    options = []

    if not data_reel or not data_genere:
        return fig, options, None

    # Conversion en DataFrames
    Data_real = pd.DataFrame(data_reel)
    Data_gen = pd.DataFrame(data_genere)

    # --- VOTRE LOGIQUE DE CALCUL ---
    nom_colone_référance = Data_real.columns[0]
    
    # On prépare les données avec les références
    dg = creation_de_ref(Data_gen, nom_colone_référance)
    dr = creation_de_ref(Data_real, nom_colone_référance)
    
    # Suppression de la colonne d'origine pour ne garder que 'ref'
    dg_calc = dg.drop(nom_colone_référance, axis=1)
    dr_calc = dr.drop(nom_colone_référance, axis=1)

    Biais_tot = pd.DataFrame()

    # Calcul du biais pour chaque point de référence unique dans le généré
    for valeur_ref_gen in dg_calc["ref"].unique():
        df_sans_biais = sélection_valeur_ref_gen(valeur_ref_gen, dr_calc)
        
        if not df_sans_biais.empty:
            df_sans_biais["ratio"] = ratio(df_sans_biais, valeur_ref_gen)
            data_ref_current = dg_calc[dg_calc["ref"] == valeur_ref_gen].copy()
            
            biais_step = Biai_moyen(df_sans_biais, data_ref_current)
            biais_step["ref"] = valeur_ref_gen
            Biais_tot = pd.concat([Biais_tot, biais_step], ignore_index=True)

    if Biais_tot.empty:
        return fig, options, None

    # Agrégation finale
    Biais_tot = moyenne_par_colone_référance(Biais_tot)
    
    # --- MISE À JOUR DU DROPDOWN ---
    cols_numeriques = [c for c in Biais_tot.columns if c != 'ref']
    options = [{'label': c, 'value': c} for c in cols_numeriques]
    
    if not selected_col and cols_numeriques:
        selected_col = cols_numeriques[0]

    # --- CRÉATION DU GRAPHIQUE ---
    if selected_col in Biais_tot.columns:
        fig = px.line(
            Biais_tot, 
            x="ref", 
            y=selected_col,
            title=f"Biais moyen pour '{selected_col}' selon '{nom_colone_référance}'",
            markers=True,
            labels={"ref": nom_colone_référance, selected_col: "Biais Absolu"}
        )
        fig.update_traces(line_color=ROSE_LOGO, marker=dict(size=8))
        fig.update_layout(template="plotly_white", hovermode="x unified")
        # Ajout d'une ligne de référence à 0 (Biais nul)
        fig.add_hline(y=0, line_dash="dash", line_color=BLEU_FONCE, annotation_text="Biais nul")

    return fig, options, selected_col

if __name__ == '__main__':
    app.run(debug=True)