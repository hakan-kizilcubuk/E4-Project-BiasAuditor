# src/pages/admin_page.py
from dash import dcc, html
import dash_bootstrap_components as dbc
# Importing theme settings from utils
from src.utils import THEMES_COLORS

def render_admin_layout(settings):
    """
    Renders the Administration page.
    Features a password lock zone and a settings panel for themes and bias thresholds.
    """
    tk = settings.get('theme', 'sombre')
    t = THEMES_COLORS[tk]
    
    return dbc.Container([
        # Page Title
        html.H2("🔐 Administration", className="text-center pt-5", style={'color': t['texte']}),
        
        # Password Lock Zone
        html.Div(id="admin-lock-zone", style={"maxWidth": "400px", "margin": "auto"}, children=[
            dbc.Input(id="admin-pwd", type="password", placeholder="Entrez le code 'admin'...", className="mb-2"),
            dbc.Button("Accéder aux réglages", id="btn-unlock", color="primary", className="w-100"),
            html.Div(id="unlock-err", className="text-danger mt-2")
        ]),
        
        # Hidden Settings Panel (Revealed upon correct password)
        html.Div(id="admin-panel", style={"display": "none"}, children=[
            html.Hr(style={'borderColor': t['border']}),
            
            dbc.Row([
                # Theme Selection
                dbc.Col([
                    html.Label("Mode d'affichage (Theme)", style={'color': t['texte'], 'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='theme-sel', 
                        options=[
                            {'label': '☀️ Clair', 'value': 'clair'},
                            {'label': '🌙 Sombre', 'value': 'sombre'},
                            {'label': '👁️ Daltonien', 'value': 'daltonien'}
                        ], 
                        value=tk,
                        style={'color': '#000'} # Dropdown text color for visibility
                    )
                ], width=12, lg=4, className="mb-4"),
                
                # Threshold Range Slider
                dbc.Col([
                    html.Label("Seuils de Biais par défaut (%)", style={'color': t['texte'], 'fontWeight': 'bold'}),
                    html.P("Définissez les limites pour les alertes (Vigilance vs Critique)", 
                           style={'color': '#94a3b8', 'fontSize': '12px'}),
                    dcc.RangeSlider(
                        id='admin-slider', 
                        min=0, max=100, 
                        value=settings.get('thresholds', [15, 40]), 
                        allowCross=False, 
                        step=1, 
                        pushable=1,
                        marks={i: {'label': f'{i}%', 'style': {'color': t['texte']}} for i in [0, 25, 50, 75, 100]},
                        tooltip={"always_visible": True, "placement": "top"}
                    )
                ], width=12, lg=8)
            ], className="mt-4"),
            
            # Save Button
            dbc.Button(
                "Enregistrer les réglages", 
                id="btn-save", 
                color="success", 
                className="mt-5 w-100 fw-bold",
                style={'padding': '12px'}
            )
        ])
    ])