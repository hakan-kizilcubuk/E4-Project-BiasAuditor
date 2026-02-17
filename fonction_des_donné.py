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


def creation_de_ref(df, nom_colone):
    df = df.copy()

    if pd.api.types.is_numeric_dtype(df[nom_colone]):
        df["ref"] = df[nom_colone]
    else:
        valeurs_uniques = sorted(df[nom_colone].dropna().unique())
        mapping = {val: i + 1 for i, val in enumerate(valeurs_uniques)}
        df["ref"] = df[nom_colone].map(mapping)

    return df




def valeurs_les_plus_proches(df, nom_colonne, valeur_ref_2):
    # Trie et extrait les valeurs uniques de la colonne
    valeurs = df[nom_colonne].drop_duplicates().sort_values().values

    # Cas où la valeur exacte existe
    if valeur_ref_2 in valeurs:
        return pd.Series([valeur_ref_2])

    # Sinon, cherche les deux bornes
    inf = valeurs[valeurs < valeur_ref_2]
    sup = valeurs[valeurs > valeur_ref_2]

    # Récupère la plus grande valeur inférieure et la plus petite valeur supérieure
    borne_inf = inf[-1] if len(inf) > 0 else None
    borne_sup = sup[0] if len(sup) > 0 else None

    # Retourne les bornes sous forme de Série (sans doublon)
    result = pd.Series([borne_inf, borne_sup]).dropna()
    return result



def filtrer_lignes_par_liste_ref(df, liste_valeur_ref):
    return df[df["ref"].isin(liste_valeur_ref)]





def sélection_valeur_ref_gen(valeur_ref_gen, Data_real):
    return(filtrer_lignes_par_liste_ref(Data_real, valeurs_les_plus_proches(Data_real,"ref",valeur_ref_gen)))


def ratio(df, valeur_ref_gen):

    if df.empty:
        return []

    liste_ref = df['ref'].tolist()
    
    distances = [abs(x - valeur_ref_gen) for x in liste_ref]
    
    poids = [1 / (d + 1e-10) for d in distances]
    somme_poids = sum(poids)
    
    poids_normalises = [int(round(100 * p / somme_poids)) for p in poids]
    
    # Ajustement final seulement si la liste n'est pas vide
    if poids_normalises:
        poids_normalises[-1] += 100 - sum(poids_normalises)
        
    return poids_normalises

def Biai_moyen(Data_sans_biai_gen, data_ref):

    if "ratio" not in Data_sans_biai_gen.columns:
        raise ValueError("La colonne 'ratio' est absente de Data_sans_biai_gen")

    ratio = Data_sans_biai_gen["ratio"]

    biais_absolus = {}

    # Colonnes communes (sauf ratio)
    colonnes_communes = (
        Data_sans_biai_gen.columns
        .intersection(data_ref.columns)
        .difference(["ratio"])
    )

    for col in colonnes_communes:

        # uniquement numérique
        if not pd.api.types.is_numeric_dtype(Data_sans_biai_gen[col]):
            continue

        # valeur de référence UNIQUE
        ref_val = data_ref[col].iloc[0]

        # biais pondéré
        biais = (
            (Data_sans_biai_gen[col] - ref_val) * ratio
        ).sum() / ratio.sum()

        biais_absolus[col] = abs(biais)

    # sortie : 1 ligne, colonnes = variables
    return pd.DataFrame([biais_absolus])
    

def moyenne_par_colone_référance(df):
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









