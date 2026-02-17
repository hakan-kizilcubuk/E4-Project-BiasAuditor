# -*- coding: utf-8 -*-
import runpy
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# -------------------------------------------------------------------------------------------------------------------
# Import du DataFrame Biais_tot
donnees = runpy.run_path("lecture_des_donné.py")
Biais_tot = donnees["Biais_tot"]  # Assurez-vous que c'est bien le nom exact dans le fichier

# Liste des colonnes du DataFrame
liste_colonnes = Biais_tot.columns.tolist()

# Couleurs et style
fond_foncé = "#FFFFFF"
texte_couleur = "#0f172a"
couleur_accent = "#FFD700"

# -------------------------------------------------------------------------------------------------------------------
# Création de l'app Dash
app = Dash(__name__)
app.title = "Visualisation des biais"

# Layout principal
app.layout = html.Div([
    html.H2("Biais absolus moyens par variable", style={"marginBottom": "16px"}),

    # Sélecteur de colonne
    html.Div([
        html.Label("Choisir une colonne :"),
        dcc.Dropdown(liste_colonnes, liste_colonnes[0], id="dropdown-colonne", clearable=False)
    ], style={"width":"40%", "marginBottom":"20px"}),

    # Graphique barres
    dcc.Graph(id="graph-biais", style={"height":"600px"})
], style={
    "backgroundColor": fond_foncé,
    "color": texte_couleur,
    "padding": "16px"
})

# -------------------------------------------------------------------------------------------------------------------
# Callback pour mettre à jour le graphique selon la colonne sélectionnée
@app.callback(
    Output("graph-biais", "figure"),
    Input("dropdown-colonne", "value")
)
def mise_a_jour_biais(colonne_choisie):
    if colonne_choisie not in Biais_tot.columns:
        return px.bar(title="Colonne non trouvée")
    
    # Préparer le dataframe pour le graphique
    df_plot = Biais_tot[[colonne_choisie]].copy()
    df_plot["index"] = df_plot.index.astype(str)

    # Graphique barres
    fig = px.bar(
        df_plot,
        x="index",
        y=colonne_choisie,
        text=colonne_choisie,
        labels={"index":"Valeur de référence", colonne_choisie:"Biais absolu"},
        title=f"Biais absolu moyen pour {colonne_choisie}"
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", marker_color=couleur_accent)
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=texte_couleur,
        margin=dict(l=40,r=40,t=60,b=40)
    )
    return fig

# -------------------------------------------------------------------------------------------------------------------
# Main
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True, use_reloader=False)
    
    
#http://127.0.0.1:8050/
