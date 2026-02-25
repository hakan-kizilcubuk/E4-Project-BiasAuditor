# -*- coding: utf-8 -*-
"""
Created on Sat Feb  7 19:55:15 2026

@author: jguio
"""

import pandas as pd
from fpdf import FPDF
import datetime
import plotly.express as px
import io
from fpdf import FPDF
import datetime


def creation_de_ref(df: pd.DataFrame, nom_colonne: str) -> pd.DataFrame:
    """
    Crée une colonne 'ref' basée sur une colonne existante.

    Si la colonne est numérique, la valeur est copiée.
    Sinon, un mapping ordinal est créé à partir des valeurs uniques triées.
    """
    df = df.copy()

    if pd.api.types.is_numeric_dtype(df[nom_colonne]):
        df["ref"] = df[nom_colonne]
    else:
        valeurs_uniques = sorted(df[nom_colonne].dropna().unique())
        mapping = {val: i + 1 for i, val in enumerate(valeurs_uniques)}
        df["ref"] = df[nom_colonne].map(mapping)

    return df




def valeurs_les_plus_proches(
    df: pd.DataFrame,
    nom_colonne: str,
    valeur_ref: float
) -> pd.Series:
    """
    Retourne la valeur exacte si elle existe,
    sinon les deux valeurs les plus proches (borne inf et sup).
    """
    valeurs = df[nom_colonne].drop_duplicates().sort_values().values

    if valeur_ref in valeurs:
        return pd.Series([valeur_ref])


    inf = valeurs[valeurs < valeur_ref]
    sup = valeurs[valeurs > valeur_ref]

    borne_inf = inf[-1] if len(inf) > 0 else None
    borne_sup = sup[0] if len(sup) > 0 else None

    result = pd.Series([borne_inf, borne_sup]).dropna()
    return result



def filtrer_lignes_par_liste_ref(
    df: pd.DataFrame,
    liste_valeurs_ref: pd.Series
) -> pd.DataFrame:
    """Filtre les lignes dont la colonne 'ref' appartient à une liste."""
    return df[df["ref"].isin(liste_valeurs_ref)]





def selection_valeur_ref_gen(
    valeur_ref_gen: float,
    data_real: pd.DataFrame
) -> pd.DataFrame:
    """Sélectionne les lignes correspondant aux valeurs de référence proches."""
    valeurs_proches = valeurs_les_plus_proches(data_real, "ref", valeur_ref_gen)
    return filtrer_lignes_par_liste_ref(data_real, valeurs_proches)


def calcul_ratio(df: pd.DataFrame, valeur_ref_gen: float):
    """
    Calcule des poids : 
    1. Si correspondance exacte trouvée -> 100% sur l'exact.
    2. Sinon -> Pondération par distance entre les voisins proches.
    """
    if df.empty:
        return []

    liste_ref = df['ref'].tolist()
    
    # ÉTAPE 1 : Chercher s'il y a une valeur exacte
    indices_exacts = [i for i, x in enumerate(liste_ref) if abs(x - valeur_ref_gen) < 1e-6]
    
    if indices_exacts:
        # On donne tout le poids aux valeurs exactes (partagé si plusieurs)
        poids = [0] * len(liste_ref)
        valeur_partagee = 100 // len(indices_exacts)
        for idx in indices_exacts:
            poids[idx] = valeur_partagee
        # Ajustement pour total = 100
        poids[indices_exacts[-1]] += (100 - sum(poids))
        return poids

    # ÉTAPE 2 : Si pas d'exact, calcul par distance (Voisins proches)
    distances = [abs(x - valeur_ref_gen) for x in liste_ref]
    # On ajoute 1e-10 pour éviter la division par zéro (sécurité)
    poids_bruts = [1 / (d + 1e-10) for d in distances]
    somme_poids = sum(poids_bruts)
    
    poids_normalises = [int(round(100 * p / somme_poids)) for p in poids_bruts]
    
    # Ajustement final pour que la somme soit exactement 100
    if poids_normalises:
        poids_normalises[-1] += 100 - sum(poids_normalises)
        
    return poids_normalises



def biais_moyen(data_sans_biais, data_ref, df_reel_complet, df_gen_complet):
    """
    Calcule le pourcentage d'erreur (Fidélité) avec une logique adaptative :
    - Erreur Relative pour les mesures à large échelle.
    - Erreur Normalisée par l'étendue pour les catégories et petites valeurs.
    """
    ratio = data_sans_biais["ratio"]
    resultats_final = {}
    
    # On identifie les colonnes communes (excluant les colonnes techniques)
    colonnes_communes = data_sans_biais.columns.intersection(data_ref.columns).difference(["ratio", "ref"])

    for col in colonnes_communes:
        # 1. LA CIBLE : La valeur réelle de référence
        valeur_reelle_cible = data_ref[col].iloc[0]
        
        # 2. LA GÉNÉRATION : La valeur produite (Moyenne pondérée)
        # Si calcul_ratio a trouvé un 'exact', cette valeur sera identique au réel.
        valeur_generee = (data_sans_biais[col] * ratio).sum() / ratio.sum()
        
        # 3. ANALYSE DE L'ÉCHELLE
        ecart_absolu = abs(valeur_reelle_cible - valeur_generee)
        etendue_globale = df_reel_complet[col].max() - df_reel_complet[col].min()
        
        # 4. CALCUL DU BIAIS ADAPTATIF
        # On définit un seuil : si la valeur réelle est > 5% du max de la colonne, 
        # on la considère comme une "grande valeur" nécessitant une erreur relative.
        seuil_sensibilite = 0.05 * df_reel_complet[col].max()
        
        if abs(valeur_reelle_cible) > seuil_sensibilite:
            # CAS GRANDE VALEUR : Erreur relative classique
            # (Ex: Cholestérol, Rythme cardiaque)
            erreur_pourcent = (ecart_absolu / abs(valeur_reelle_cible)) * 100
        else:
            # CAS PETITE VALEUR / CATÉGORIE : Normalisation par l'étendue
            # (Ex: Sexe (0/1), FBS (0/1), CA (0-3))
            # On divise par l'étendue pour savoir quel % de l'échelle totale l'erreur représente.
            erreur_pourcent = (ecart_absolu / etendue_globale * 100) if etendue_globale != 0 else 0
            
        resultats_final[col] = erreur_pourcent

    return pd.DataFrame([resultats_final])

def moyenne_par_colone_référance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Regroupe par 'nom_fichier_référance' 
    et calcule la moyenne de toutes les autres colonnes numériques.
    """
    
    df_resultat = (
        df
        .groupby("ref", as_index=False)
        .mean(numeric_only=True)
    )
    
    return df_resultat 

# --- NOUVELLE FONCTION : GÉNÉRATION DE RAPPORT AUTOMATIQUE ---

def generate_pdf_report(df_bias_final, nom_colone_reference="ref"):
    """
    Génère un rapport d'audit au format PDF bilingue (FR/EN) pour Alia Santé.
    Generates a bilingual (FR/EN) audit report in PDF format for Alia Santé.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Colors (matching app theme)
    ROSE_LOGO = [216, 98, 122]  # #d8627a
    BLEU_FONCE = [66, 77, 109]  # #424d6d
    
    # En-tête du rapport / Report Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Bias Auditor - Rapport d'Analyse de Biais / Bias Analysis Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Date du rapport / Report date: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='R')
    pdf.ln(10)

    # Contexte du Projet / Project Context
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Contexte et Objectifs / Context and Objectives", ln=True)
    pdf.set_font("Arial", size=10)
    
    # French version
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, "Français:", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 4, "Ce rapport présente les résultats de l'audit des biais dans les données "
                         "synthétiques de santé générées par la plateforme Alia Santé. "
                         "L'objectif est de quantifier l'écart entre les données réelles et synthétiques "
                         "pour garantir l'équité des algorithmes.")
    pdf.ln(3)
    
    # English version
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, "English:", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 4, "This report presents the results of bias audit in synthetic health data "
                         "generated by the Alia Santé platform. The objective is to quantify the "
                         "gap between real and synthetic data to ensure algorithmic fairness.")
    pdf.ln(5)

    # Tableau des résultats de biais / Bias Results Table
    pdf.set_fill_color(*ROSE_LOGO)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 10, "Variable (Attribut/Attribute)", 1, 0, 'C', True)
    pdf.cell(95, 10, "Score de Biais Moyen / Mean Bias Score", 1, 1, 'C', True)

    # Contenu du tableau / Table content
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=10)
    
    # Get numeric columns (excluding 'ref')
    numeric_cols = [col for col in df_bias_final.columns if col != 'ref']
    
    for col in numeric_cols:
        if col in df_bias_final.columns:
            val_mean = df_bias_final[col].mean()
            pdf.cell(95, 10, str(col), 1)
            pdf.cell(95, 10, f"{val_mean:.5f}", 1, 1, 'C')

    # Section graphiques / Graphs Section
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Analyse Graphique des Biais / Graphical Bias Analysis", ln=True)
    
    # French description
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, "Français:", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 4, "Les graphiques ci-dessous montrent l'évolution des biais pour chaque variable "
                         "en fonction de la référence. La ligne pointillée représente un biais nul.")
    pdf.ln(2)
    
    # English description
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, "English:", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 4, "The graphs below show the evolution of bias for each variable "
                         "according to the reference. The dashed line represents zero bias.")
    pdf.ln(5)

    # Generate and add graphs for each numeric column
    for i, col in enumerate(numeric_cols[:3]):  # Limit to 3 graphs to avoid PDF size issues
        try:
            # Create the graph using plotly
            fig = px.line(
                df_bias_final, 
                x="ref", 
                y=col,
                title=f"Biais pour / Bias for '{col}' selon / according to '{nom_colone_reference}'",
                markers=True,
                labels={"ref": nom_colone_reference, col: "Biais Absolu / Absolute Bias"}
            )
            fig.update_traces(line_color='rgb(216, 98, 122)', marker=dict(size=8))
            fig.update_layout(
                template="plotly_white", 
                hovermode="x unified",
                width=600, 
                height=400,
                title_font_size=12,
                title_x=0.5
            )
            # Add reference line at y=0
            fig.add_hline(y=0, line_dash="dash", line_color='rgb(66, 77, 109)', 
                         annotation_text="Biais nul / Zero bias")

            # Convert plot to image bytes
            img_bytes = fig.to_image(format="png", width=600, height=400)
            
            # Save temporary image
            temp_img_path = f"temp_graph_{i}.png"
            with open(temp_img_path, "wb") as f:
                f.write(img_bytes)
            
            # Add to PDF
            if i > 0:  # Add new page for additional graphs
                pdf.add_page()
                
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, f"Graphique / Graph {i+1}: {col}", ln=True, align='C')
            pdf.ln(5)
            
            # Add image to PDF (centered)
            pdf.image(temp_img_path, x=10, w=190)
            pdf.ln(10)
            
            # Clean up temp file
            import os
            os.remove(temp_img_path)
            
        except Exception as e:
            # If graph generation fails, just add text
            pdf.set_font("Arial", 'I', 9)
            pdf.cell(0, 8, f"Graphique pour / Graph for {col}: Erreur de génération / Generation error", ln=True)
            pdf.ln(5)

    # Interprétation et Recommandations / Interpretation and Recommendations
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. Méthodologie et Interprétation / Methodology and Interpretation", ln=True)
    
    # French interpretation
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, "Français:", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 4, "Le pipeline 'Bias Auditor' a calculé les différentiels réel -> synthétique. "
                         "Un score proche de zéro indique une préservation optimale de la distribution originale. "
                         "Les scores élevés signalent une amplification potentielle de biais nécessitant "
                         "un ajustement des modèles génératifs.")
    pdf.ln(3)
    
    # English interpretation
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, "English:", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 4, "The 'Bias Auditor' pipeline calculated real -> synthetic differentials. "
                         "A score close to zero indicates optimal preservation of the original distribution. "
                         "High scores signal potential bias amplification requiring adjustment "
                         "of generative models.")

    # Pied de page / Footer
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, "Document généré automatiquement / Automatically generated document - Alia Santé x ESIEE Paris", 0, 0, 'C')

    # Return PDF as bytes
    return pdf.output()