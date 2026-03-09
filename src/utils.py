import numpy as np
import pandas as pd
from scipy.stats import skew

# --- UI CONFIGURATIONS ---

# Color palettes for different themes (clair, sombre, daltonien)
THEMES_COLORS = {
    "clair": {"fond": "#f8fafc", "texte": "#1e293b", "card": "white", "nav": "#1e293b", "border": "#cbd5e1"},
    "sombre": {"fond": "#0a192f", "texte": "#e2e8f0", "card": "#112240", "nav": "#020c1b", "border": "#1d2d50"},
    "daltonien": {"fond": "#fdf6e3", "texte": "#002b36", "card": "#eee8d5", "nav": "#073642", "border": "#93a1a1"}
}

# Status colors for bias levels and Alia brand
STATUS_COLORS = {
    "clair": {"ok": "#10b981", "moy": "#f59e0b", "crit": "#ef4444", "alia": "#d8627a"},
    "sombre": {"ok": "#34d399", "moy": "#fbbf24", "crit": "#f87171", "alia": "#fb7185"},
    "daltonien": {"ok": "#268bd2", "moy": "#b58900", "crit": "#dc322f", "alia": "#d33682"}
}

# --- STATISTICAL FUNCTIONS ---

def calculate_skewness(series):
    """
    Calculates the skewness of a numerical distribution.
    Measures the asymmetry around the mean.
    """
    if series.empty or series.nunique() <= 1:
        return 0.0
    return float(skew(series.dropna()))

def calculate_entropy(series):
    """
    Calculates Shannon Entropy for categorical or binned numerical data.
    Measures informational diversity.
    """
    if series.empty:
        return 0.0
    prob = series.value_counts(normalize=True)
    return float(-1 * np.sum(prob * np.log2(prob + 1e-10)))

def calculate_global_score(mean_bias, p_value_avg, spd_score=None):
    """
    Aggregates different metrics into a single interpretability score (0-100).
    Formula: Weights Bias (50%), Statistical Fidelity (30%), and Fairness (20%).
    """
    # 100 is perfect, 0 is poor
    bias_fidelity = max(0, 100 - mean_bias)
    stat_fidelity = p_value_avg * 100
    
    # If SPD is available, include it in the calculation
    if spd_score is not None:
        # SPD closer to 0 is better (fairer)
        fairness_score = max(0, (1 - abs(spd_score)) * 100)
        final_score = (bias_fidelity * 0.5) + (stat_fidelity * 0.3) + (fairness_score * 0.2)
    else:
        # Default weighting without fairness metric
        final_score = (bias_fidelity * 0.6) + (stat_fidelity * 0.4)
        
    return round(max(0, min(100, final_score)), 2)