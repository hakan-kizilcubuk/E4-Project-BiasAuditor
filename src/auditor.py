import fairlens as fl
import pandas as pd

def run_initial_audit(df, target_col):
    detector = fl.SensitiveAttributeDetector()
    sensitive_attrs = detector.detect(df)

    s_attr = sensitive_attrs[0] if sensitive_attrs else None
    
    if s_attr:
        scorer = fl.FairnessScorer(df, target_attr=target_col, sensitive_attr=s_attr)
        return sensitive_attrs, scorer.demographic_parity()
    return sensitive_attrs, None

if __name__ == "__main__":
    print("Kurulum başarılı, auditor modülü hazır!")