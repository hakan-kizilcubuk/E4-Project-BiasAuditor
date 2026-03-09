import pandas as pd
from fairlearn.metrics import demographic_parity_difference

def run_fairness_audit(df, target_col, sensitive_col):
    """
    Performs a fairness audit using the Fairlearn library.
    Calculates the Statistical Parity Difference (SPD).
    """
    if sensitive_col not in df.columns or target_col not in df.columns:
        return None

    try:
        # Calculate Demographic Parity Difference (SPD)
        # It requires the target to be binary or categorical for meaningful results
        spd = demographic_parity_difference(
            df[target_col],
            df[target_col], # Comparing distribution against itself as a baseline
            sensitive_features=df[sensitive_col]
        )
        return float(spd)
    except Exception as e:
        print(f"Fairness Audit Error: {e}")
        return None