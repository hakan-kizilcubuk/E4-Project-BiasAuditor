# src/pages/dashboard_page.py
from dash import dcc, html
import dash_bootstrap_components as dbc
# Importing theme and color settings from utils
from src.utils import THEMES_COLORS, STATUS_COLORS

def render_dashboard_layout(theme_key):
    """
    Renders the main Audit Dashboard.
    Contains the Global Score widget, the PDF export button, 
    and the container for individual variable analysis cards.
    """
    t = THEMES_COLORS[theme_key]
    
    return dbc.Container([
        # Header Section: Title, Global Score, and Export Button
        dbc.Row([
            # Title
            dbc.Col(
                html.H3(
                    "Rapport d'Audit : Fidélité & Équité", 
                    className="py-4 fw-bold", 
                    style={'color': t['texte']}
                ), 
                width=12, lg=6
            ),
            
            # Global Score Display (Populated via callback in app.py)
            dbc.Col(
                html.Div(id="global-score-zone"), 
                width=6, lg=3, 
                className="d-flex align-items-center justify-content-center"
            ),
            
            # PDF Export Button
            dbc.Col(
                dbc.Button(
                    "📄 Exporter PDF", 
                    id="btn-pdf", 
                    color="info", 
                    className="mt-4 px-4 fw-bold",
                    style={'borderRadius': '10px'}
                ), 
                width=6, lg=3, 
                className="text-end"
            )
        ], className="align-items-center mb-4"),

        # Results Container: Individual Bias Cards
        # This row will be dynamically filled by the update_results callback in app.py
        dbc.Row(
            id='individual-bias-cards', 
            className="g-4 pb-5"
        ), 
        
    ], fluid=True)

def create_individual_card(var_name, bias_value, status, color, theme_key, metrics):
    """
    Helper function to maintain the 'Old Look' card style.
    This structure is used within the app.py callback to generate result cards.
    """
    t = THEMES_COLORS[theme_key]
    alia_color = STATUS_COLORS[theme_key]["alia"]
    
    return dbc.Col(
        html.Div(style={
            'borderRadius': '15px', 
            'backgroundColor': t['card'], 
            'padding': '15px', 
            'textAlign': 'center', 
            'position': 'relative',
            'border': f'2px solid {color}' if status == "CRITIQUE" else f'1px solid {t["border"]}',
            'boxShadow': '0 4px 12px rgba(0,0,0,0.2)'
        }, children=[
            # Status Badge
            html.Span(
                status, 
                style={
                    'position': 'absolute', 'top': '10px', 'right': '10px', 
                    'fontSize': '9px', 'fontWeight': 'bold', 'padding': '2px 10px', 
                    'borderRadius': '20px', 'color': 'white', 'backgroundColor': color
                }
            ),
            
            # Variable Name
            html.B(
                var_name, 
                style={'color': t['texte'], 'fontSize': '1.1rem', 'display': 'block', 'marginBottom': '10px'}
            ),
            
            # Donut Chart Placeholder (Actual graph is created in app.py)
            html.Div(id={'type': 'donut-chart', 'index': var_name}),
            
            # Summary Metrics (Skewness & Entropy)
            html.Div([
                html.Small(

                    f"Skewness: {metrics['skewness']:.2f} | Entropy: {metrics['entropy']:.2f}", 
                    style={'color': '#94a3b8', 'fontSize': '11px'}
                ),
            ], className="mb-2"),

            # Technical Details Accordion
            dbc.Accordion([
                dbc.AccordionItem(title="🔍 Détails Techniques", children=[
                    html.Div(style={'padding': '10px', 'textAlign': 'left'}, children=[
                        html.P(f"P-Value (KS Test): {metrics['p_value']:.4f}", style={'fontSize': '12px', 'color': t['texte']}),
                        html.P(
                            f"Recommandation: {metrics['recommendation']}", 
                            style={'fontSize': '12px', 'color': alia_color, 'fontWeight': 'bold'}
                        )
                    ])
                ])
            ], start_collapsed=True, flush=True)
        ]),
        width=12, md=6, lg=4, className="mb-4"
    )