# src/pages/import_page.py
from dash import dcc, html
import dash_bootstrap_components as dbc
# Importing theme and color settings from utils
from src.utils import THEMES_COLORS, STATUS_COLORS

def render_import_layout(theme_key):
    """
    Renders the data importation page with the original visual style.
    This includes the file upload zones, column selection menu, and the audit trigger button.
    """
    t = THEMES_COLORS[theme_key]
    alia_color = STATUS_COLORS[theme_key]["alia"]
    
    return dbc.Container([
        # Main Title
        html.H2("Alia Bias Auditor", className="text-center pt-5 fw-bold", style={'color': t['texte']}),
        
        # File Upload Section (Real and Synthetic)
        dbc.Row([
            dbc.Col([
                html.Label("📂 Fichier Réel (Source)", className="fw-bold", style={'color': t['texte']}),
                dcc.Upload(
                    id='upload-reel', 
                    children=html.Div(id='content-reel', children="Glisser CSV", style={'color': t['texte']}), 
                    style={
                        'border': f'2px dashed {t["border"]}', 
                        'padding': '30px', 
                        'textAlign': 'center', 
                        'backgroundColor': t['card'], 
                        'borderRadius': '10px'
                    }
                )
            ], width=6),
            dbc.Col([
                html.Label("📂 Fichier Généré (IA)", className="fw-bold", style={'color': t['texte']}),
                dcc.Upload(
                    id='upload-genere', 
                    children=html.Div(id='content-genere', children="Glisser CSV", style={'color': t['texte']}),
                    style={
                        'border': f'2px dashed {t["border"]}', 
                        'padding': '30px', 
                        'textAlign': 'center', 
                        'backgroundColor': t['card'], 
                        'borderRadius': '10px'
                    }
                )
            ], width=6),
        ], className="mt-4"),
        
        # Dynamic Menu for column selection (Populated via callback in app.py)
        html.Div(
            id='dynamic-menu-content', 
            style={'maxWidth': '600px', 'margin': '40px auto'}
        ),
        
        # Launch Audit Button
        html.Div(
            dcc.Link(
                dbc.Button(
                    "Lancer l'Audit", 
                    color="danger", 
                    size="lg", 
                    className="px-5",
                    style={'backgroundColor': alia_color, 'border': 'none'}
                ), 
                href="/graphique"
            ), 
            className="text-center pb-5"
        )
    ])