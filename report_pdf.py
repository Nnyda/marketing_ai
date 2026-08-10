# marketing_ai/report_pdf.py
"""Export PDF du rapport A2A, sans dependance systeme (fpdf2, pur Python).

    from report_pdf import save_pdf_report
    save_pdf_report(result, "a2a_report.pdf")
"""
import os
from datetime import datetime
from fpdf import FPDF

from report import _parse  # reutilise le parseur d'artefacts JSON

# Palette (RGB)
GREEN = (47, 125, 79)
GREEN_D = (30, 82, 51)
INK = (28, 43, 34)
MUTED = (138, 152, 143)
QUAD = {
    "s": ((234, 246, 238), (30, 122, 68)),
    "w": ((253, 238, 238), (178, 59, 59)),
    "o": ((234, 241, 251), (42, 93, 176)),
    "t": ((251, 243, 231), (165, 112, 30)),
}


def _s(text) -> str:
    """Nettoie le texte pour l'encodage latin-1 des polices de base fpdf."""
    if text is None:
        return ""
    t = str(text)
    repl = {
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...", "•": "-",
        " ": " ", "→": "->", "⇄": "<->",
    }
    for k, v in repl.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "replace").decode("latin-1")


class ReportPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, _s(f"Multi-Agent Digital Marketing Advisor  -  page {self.page_no()}"),
                  align="C")

    # --- briques reutilisables ---
    def section_title(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*GREEN_D)
        self.cell(0, 9, _s(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*GREEN)
        self.set_line_width(0.5)
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(3)

    def bullets(self, items, indent=4):
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(*INK)
        if not items:
            self.set_text_color(*MUTED)
            self.cell(0, 6, _s("  -"), new_x="LMARGIN", new_y="NEXT")
            return
        for it in items:
            x = self.l_margin + indent
            self.set_x(x)
            self.cell(4, 6, "-")
            self.multi_cell(self.w - self.r_margin - x - 4, 6, _s(it),
                            new_x="LMARGIN", new_y="NEXT")

    def quad(self, label, key, items):
        bg, fg = QUAD[key]
        x0, y0 = self.l_margin, self.get_y()
        w = self.w - self.l_margin - self.r_margin
        # titre colore
        self.set_fill_color(*bg)
        self.set_text_color(*fg)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(x0, y0)
        self.cell(w, 8, _s("  " + label), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.bullets(items, indent=6)
        self.ln(2)


def build_pdf(result: dict, path: str) -> str:
    inp = result.get("input", {}) or {}
    artifacts = result.get("artifacts", {}) or {}
    swot = _parse(artifacts.get("swot")) or {}
    strategy = _parse(artifacts.get("strategy")) or {}
    design = _parse(artifacts.get("design")) or {}
    log = result.get("collaboration_log", []) or []

    image_path = None
    img = artifacts.get("image")
    if isinstance(img, dict):
        image_path = img.get("path")
    elif isinstance(img, str):
        image_path = img

    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin

    # --- Bandeau titre ---
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 0, pdf.w, 30, style="F")
    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, _s(f"Rapport marketing - {inp.get('product', '-')}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 10)
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 6, _s(f"Marche : {inp.get('country', '-')}  -  {date_str}  -  "
                      f"{result.get('iterations', 0)} echanges A2A"))
    pdf.ln(20)

    # --- Demande / brief ---
    if inp.get("brief") or inp.get("extra"):
        pdf.section_title("Demande")
        if inp.get("brief"):
            pdf.set_font("Helvetica", "I", 10.5)
            pdf.set_text_color(66, 82, 74)
            pdf.multi_cell(W, 6, _s(f"« {inp['brief']} »"),
                           new_x="LMARGIN", new_y="NEXT")
        extra = inp.get("extra", {}) or {}
        labels = {"objective": "Objectif", "audience": "Cible", "budget": "Budget",
                  "channels": "Canaux", "tone": "Ton"}
        chips = [f"{lbl}: {extra[k]}" for k, lbl in labels.items() if extra.get(k)]
        if chips:
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(W, 5, _s("   |   ".join(chips)), new_x="LMARGIN", new_y="NEXT")

    # --- SWOT ---
    pdf.section_title("Analyse de marche (SWOT)")
    pdf.quad("Forces", "s", swot.get("strengths"))
    pdf.quad("Faiblesses", "w", swot.get("weaknesses"))
    pdf.quad("Opportunites", "o", swot.get("opportunities"))
    pdf.quad("Menaces", "t", swot.get("threats"))

    # --- Strategie ---
    pdf.section_title("Strategie")
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Positionnement :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(W, 6, _s(strategy.get("positioning", "-")), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 6, "Messages cles :", new_x="LMARGIN", new_y="NEXT")
    pdf.bullets(strategy.get("key_messages") or strategy.get("messages"))
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 6, "Canaux :", new_x="LMARGIN", new_y="NEXT")
    pdf.bullets(strategy.get("channels"))
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 6, "KPIs :", new_x="LMARGIN", new_y="NEXT")
    pdf.bullets(strategy.get("kpis") or strategy.get("KPIs"))

    # --- Concept creatif ---
    pdf.section_title("Concept creatif")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*GREEN_D)
    pdf.multi_cell(W, 8, _s(f"« {design.get('tagline', '-')} »"),
                   align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Direction visuelle :", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(W, 6, _s(design.get("visual_style", "-")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 6, "Idees de maquettes :", new_x="LMARGIN", new_y="NEXT")
    pdf.bullets(design.get("mockup_ideas") or design.get("mockups"))

    if image_path and os.path.exists(image_path):
        pdf.ln(2)
        img_w = min(110, W)
        x = (pdf.w - img_w) / 2
        try:
            pdf.image(image_path, x=x, w=img_w)
        except Exception:
            pass

    # --- Collaboration A2A ---
    pdf.section_title("Collaboration A2A")
    pdf.set_font("Helvetica", "", 10)
    if not log:
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, _s("Aucun echange de feedback enregistre."), new_x="LMARGIN", new_y="NEXT")
    for e in log:
        mark = "[OK]" if e.get("sufficient") else "[REVISION]"
        verb = "a valide" if e.get("sufficient") else "a demande une revision a"
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(W, 6, _s(f"{mark} Iteration {e.get('iteration')} - "
                                f"{e.get('from')} {verb} {e.get('to')}"),
                       new_x="LMARGIN", new_y="NEXT")
        if e.get("feedback"):
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.set_text_color(91, 107, 97)
            pdf.multi_cell(W, 5, _s(f"    {e['feedback']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.output(path)
    return path


def save_pdf_report(result: dict, path: str = "a2a_report.pdf") -> str:
    return build_pdf(result, path)


def pdf_bytes(result: dict) -> bytes:
    """Renvoie le PDF en memoire (utile pour le bouton de telechargement Streamlit)."""
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "a2a_report_tmp.pdf")
    build_pdf(result, tmp)
    with open(tmp, "rb") as f:
        data = f.read()
    try:
        os.remove(tmp)
    except Exception:
        pass
    return data
