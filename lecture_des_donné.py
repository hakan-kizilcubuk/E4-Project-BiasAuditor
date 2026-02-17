
import pandas as pd

#from datetime import timedelta



#-------------------------------------------------------------------------------------------------------------------
#Initialisation des fichier
#nom_fichier_gen = "gen_data_WBCD.csv"
#Nom_fichier_real = "real_data_WBCD.csv"

nom_fichier_gen = "gen_data_Heart.csv"
Nom_fichier_real = "real_data_Heart.csv"


#-------------------------------------------------------------------------------------------------------------------
#Import des données

Data_gen = pd.read_csv(nom_fichier_gen)
Data_real = pd.read_csv(Nom_fichier_real)


#-------------------------------------------------------------------------------------------------------------------
#Définit la variable de référance (suposé la première colone)écart valeur min et max

if len(Data_gen.columns) > 0 :
    nom_colone_référance = Data_real.columns[0]
    
    
    
#-------------------------------------------------------------------------------------------------------------------
#fonction création de colone de ref en int() et en str

def creation_de_ref(df, nom_colone):
    df = df.copy()

    if pd.api.types.is_numeric_dtype(df[nom_colone]):
        df["ref"] = df[nom_colone]
    else:
        valeurs_uniques = sorted(df[nom_colone].dropna().unique())
        mapping = {val: i + 1 for i, val in enumerate(valeurs_uniques)}
        df["ref"] = df[nom_colone].map(mapping)

    return df


#-------------------------------------------------------------------------------------------------------------------
#fonction qui décide d'une valeur ref

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

#-------------------------------------------------------------------------------------------------------------------
#fonction qui trie des donnée par a port a une valeur de ref (ligne par ligne)

def filtrer_lignes_par_liste_ref(df, liste_valeur_ref):
    return df[df["ref"].isin(liste_valeur_ref)]


#-------------------------------------------------------------------------------------------------------------------
#sélection des données dans un nouveau dataframe

def sélection_valeur_ref_gen(valeur_ref_gen,Data_real):
    return(filtrer_lignes_par_liste_ref(Data_real, valeurs_les_plus_proches(Data_real,"ref",valeur_ref_gen)))

    

##-------------------------------------------------------------------------------------------------------------------
#fonciotn qui calcule le biai moyen

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



##-------------------------------------------------------------------------------------------------------------------
#fonciotn qui calcule le biai moyen




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
    
##-------------------------------------------------------------------------------------------------------------------
#Corp du code 

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




##-------------------------------------------------------------------------------------------------------------------
#Corp du code 
    
Data_gen=creation_de_ref(Data_gen,nom_colone_référance)
Data_real=creation_de_ref(Data_real,nom_colone_référance)
Data_gen = Data_gen.drop(nom_colone_référance, axis=1)
Data_real = Data_real.drop(nom_colone_référance, axis=1)

Biais_tot = pd.DataFrame()

# Boucle sur toutes les valeurs de la colonne de référence
for valeur_ref_gen in Data_gen["ref"] :
    df_sans_biais = sélection_valeur_ref_gen(valeur_ref_gen,Data_real)
    df_sans_biais["ratio"] = ratio(df_sans_biais, valeur_ref_gen)
    data_ref = Data_gen[Data_gen["ref"] == valeur_ref_gen].copy()
    biais = Biai_moyen(df_sans_biais,data_ref)
    Biais_tot = pd.concat([Biais_tot, biais], ignore_index=True)
Biais_tot = Biais_tot.drop("ref", axis=1)
Biais_tot["ref"] = Data_gen["ref"]
Biais_tot = moyenne_par_colone_référance(Biais_tot)



