#!/usr/bin/env python
# coding: utf-8
# marketing_ai/main.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from orchestrator import A2AOrchestrator
from report import save_html_report
from report_pdf import save_pdf_report

# Charge la cle depuis key.env (jamais versionne), sinon depuis l'environnement
current_dir = os.path.dirname(__file__)
load_dotenv(os.path.join(current_dir, "key.env"))

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found (set it in key.env or as an env variable)")

client = OpenAI(api_key=api_key)

# --- Reglages ---
# Mettre a False pour ne PAS generer d'image (evite toute erreur si le compte
# n'a pas acces aux modeles d'image : le SWOT, la strategie et le design JSON
# sont produits normalement).
GENERATE_IMAGE = True

if __name__ == "__main__":
    # max_iterations : nombre max de tours de feedback A2A par lien inter-agents
    orch = A2AOrchestrator(client, max_iterations=2)

    result = orch.run_campaign(
        product_name="GreenTech Watch",
        target_country="Germany",
        brief="Lancement d'une montre connectée écologique en matériaux biosourcés, "
              "pour de jeunes urbains soucieux de l'environnement. Positionnement premium.",
        extra={"audience": "18-35 ans urbains", "tone": "premium, engagé",
               "channels": "Instagram, TikTok, influenceurs"},
        generate_image=GENERATE_IMAGE,
    )

    # Rapports (ouvrables dans un navigateur / lecteur PDF)
    print(f"Rapport HTML généré -> {save_html_report(result, 'a2a_report.html')}")
    print(f"Rapport PDF généré  -> {save_pdf_report(result, 'a2a_report.pdf')}")
