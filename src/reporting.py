from fpdf import FPDF
import datetime

class BiasReport(FPDF):
    def header(self):
        """Custom PDF Header with Logo/Title."""
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Alia Bias Auditor - Technical Audit Report', 0, 1, 'C')
        self.ln(5)

    def add_metric_card(self, var_name, bias, status, entropy, skewness):
        """Adds a structured data block for each variable in the PDF."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f"Variable: {var_name}", ln=True)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, f" - Mean Bias: {bias:.2f}%", ln=True)
        self.cell(0, 6, f" - Status: {status}", ln=True)
        self.cell(0, 6, f" - Shannon Entropy: {entropy:.4f}", ln=True)
        self.cell(0, 6, f" - Skewness: {skewness:.4f}", ln=True)
        self.ln(5)

def generate_pdf_bytes(targets_data):
    """
    Generates the final PDF report as bytes for download.
    'targets_data' should be a list of dicts with metrics.
    """
    pdf = BiasReport()
    pdf.add_page()
    
    # Summary Section
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, "This report evaluates the statistical fidelity and fairness of synthetic datasets.")
    pdf.ln(10)

    for data in targets_data:
        pdf.add_metric_card(
            data['name'], data['bias'], data['status'], 
            data['entropy'], data['skewness']
        )
        
    return pdf.output(dest='S').encode('latin-1')