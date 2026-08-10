#!/usr/bin/env python
# coding: utf-8
# marketing_ai/streamlit_app.py
import os
import json
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from openai import OpenAI

from orchestrator import A2AOrchestrator
from report import build_html_report
from report_pdf import pdf_bytes
from file_ingest import (combine_files, images_to_data_uris, fetch_url,
                         SUPPORTED, IMAGE_EXT, MAX_IMAGES)

current_dir = os.path.dirname(__file__)
load_dotenv(os.path.join(current_dir, "key.env"))

st.set_page_config(page_title="A2A Marketing Advisor", page_icon="🚀", layout="wide")

# ============================================================
# Thème moderne & coloré (CSS)
# ============================================================
st.markdown("""
<style>
:root { --grad: linear-gradient(120deg,#7c3aed 0%,#db2777 55%,#f59e0b 100%); }
.stApp { background: #0f1117; }
.block-container { padding-top: 1.4rem; max-width: 1150px; }

/* Hero */
.hero { background: var(--grad); border-radius: 22px; padding: 30px 34px;
        margin-bottom: 22px; box-shadow: 0 12px 40px rgba(124,58,237,.35); }
.hero h1 { color:#fff; margin:0; font-size:30px; font-weight:800; letter-spacing:-.5px; }
.hero p { color:rgba(255,255,255,.92); margin:.4rem 0 0; font-size:15px; }
.hero .pills { margin-top:14px; display:flex; gap:8px; flex-wrap:wrap; }
.hero .pill { background:rgba(255,255,255,.18); color:#fff; padding:5px 12px;
        border-radius:999px; font-size:12.5px; font-weight:600; backdrop-filter:blur(4px); }

/* Cartes / sections */
section[data-testid="stForm"] { background:#171a23; border:1px solid #262b38;
        border-radius:18px; padding:22px 24px; }
h3, .stMarkdown h3 { color:#e7e9ee; }
label, .stMarkdown p { color:#c7ccd8 !important; }

/* Bouton principal */
.stButton>button, .stForm button[kind="primaryFormSubmit"], button[kind="primaryFormSubmit"] {
        background: var(--grad) !important; color:#fff !important; border:none !important;
        border-radius:12px !important; font-weight:700 !important; padding:.6rem 1rem !important;
        box-shadow:0 6px 20px rgba(219,39,119,.35) !important; }
.stDownloadButton>button { border-radius:10px !important; border:1px solid #3a4152 !important;
        background:#1d2230 !important; color:#e7e9ee !important; font-weight:600 !important; }

/* Metrics */
div[data-testid="stMetric"] { background:#171a23; border:1px solid #262b38;
        border-radius:14px; padding:12px 16px; }
div[data-testid="stMetricValue"] { color:#f59e0b; font-weight:800; }

/* Tabs */
button[data-baseweb="tab"] { font-weight:600; }
.tagbig { font-size:26px; font-weight:800; text-align:center; padding:14px;
        background:var(--grad); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🚀 Multi-Agent Marketing Advisor</h1>
  <p>Décris ta demande, et trois agents IA collaborent — Analyste ⇄ Stratège ⇄ Designer — pour te livrer une stratégie complète.</p>
  <div class="pills">
    <span class="pill">🔍 Analyse SWOT</span>
    <span class="pill">🎯 Stratégie</span>
    <span class="pill">🎨 Concept créatif</span>
    <span class="pill">🔄 Coordination A2A</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Réglages (sidebar)
# ============================================================
with st.sidebar:
    st.header("⚙️ Réglages")
    env_key = os.getenv("OPENAI_API_KEY", "")
    api_key_input = st.text_input(
        "Clé API OpenAI", value="", type="password",
        placeholder="sk-…" if not env_key else "clé déjà chargée depuis key.env",
        help="Laisse vide pour utiliser la clé configurée dans key.env.",
    )
    if env_key and not api_key_input:
        st.caption("🔑 Clé chargée depuis key.env.")
    # La clé saisie a priorité ; sinon on retombe sur celle de l'environnement.
    api_key = api_key_input.strip() or env_key
    max_iterations = st.slider("Itérations de feedback A2A", 0, 4, 2,
                               help="Nombre max de tours de révision entre agents.")
    generate_image = st.toggle("Générer le visuel (image)", value=True)
    st.divider()
    st.caption("💡 Démo : mets les itérations à 0 (séquentiel) puis à 2 pour "
               "montrer la coordination A2A en direct.")


@st.cache_resource(show_spinner=False)
def _client(key: str):
    return OpenAI(api_key=key)


# ============================================================
# Formulaire
# ============================================================
with st.form("campaign_form"):
    st.markdown("### 📝 Ta demande")
    brief = st.text_area(
        "Décris ta demande librement",
        placeholder="Ex. : Je lance Nyo, une boisson énergisante naturelle à base de "
                    "plantes, sans sucre, pour jeunes actifs urbains. Je veux un "
                    "positionnement premium et un benchmark face à Red Bull et Monster.",
        height=120, label_visibility="collapsed",
    )

    c1, c2 = st.columns(2)
    with c1:
        product_name = st.text_input("Produit *", value="Nyo")
    with c2:
        target_country = st.text_input("Pays / marché *", value="France")

    with st.expander("🎛️ Détails optionnels (cible, budget, ton…)"):
        d1, d2 = st.columns(2)
        with d1:
            objective = st.text_input("Objectif", placeholder="Ex. : lancement, benchmark…")
            audience = st.text_input("Cible", placeholder="Ex. : 18-35 ans urbains")
            budget = st.text_input("Budget", placeholder="Ex. : 50k€")
        with d2:
            tone = st.text_input("Ton de marque", placeholder="Ex. : premium, engagé")
            channels = st.text_input("Canaux préférés", placeholder="Ex. : Instagram, TikTok")

    with st.expander("📎 Sources : documents, images, lien"):
        uploaded = st.file_uploader(
            "Documents de référence (fiche produit, étude, pitchdeck…)",
            type=[e.lstrip(".") for e in SUPPORTED], accept_multiple_files=True,
            help="Formats : txt, md, csv, pdf, docx, pptx.",
        )
        doc_url = st.text_input(
            "Lien vers un document (pitchdeck, page web, PDF, Google Slides/Docs)",
            placeholder="https://…",
        )
        images_up = st.file_uploader(
            f"Tes propositions de visuels pour le produit (max {MAX_IMAGES})",
            type=[e.lstrip(".") for e in IMAGE_EXT], accept_multiple_files=True,
        )

    run_btn = st.form_submit_button("▶️  Lancer les agents", use_container_width=True)


# ============================================================
# Exécution
# ============================================================
def _parse(raw):
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}


if run_btn:
    if not api_key.strip():
        st.error("Renseigne ta clé API OpenAI dans la barre latérale.")
        st.stop()
    if not product_name.strip() or not target_country.strip():
        st.error("Le produit et le pays sont obligatoires.")
        st.stop()

    extra = {k: v.strip() for k, v in {
        "objective": objective, "audience": audience, "budget": budget,
        "channels": channels, "tone": tone,
    }.items() if v and v.strip()}

    # Sources
    documents = ""
    if uploaded:
        documents = combine_files(uploaded)
    if doc_url and doc_url.strip():
        url_text = fetch_url(doc_url.strip())
        if url_text.startswith("[Erreur"):
            st.warning(f"Lien non exploité : {url_text}")
        else:
            documents = (documents + "\n\n" if documents else "") + \
                        f"--- Contenu du lien : {doc_url.strip()} ---\n{url_text}"
    image_uris = images_to_data_uris(images_up) if images_up else []

    orch = A2AOrchestrator(_client(api_key.strip()), max_iterations=max_iterations)

    # --- Suivi en direct ---
    with st.status("🚀 Les agents travaillent…", expanded=True) as status:
        def progress(msg):
            st.write(msg)
        try:
            result = orch.run_campaign(
                product_name.strip(), target_country.strip(),
                brief=brief.strip(), extra=extra, documents=documents,
                images=image_uris, generate_image=generate_image,
                progress=progress,
            )
            status.update(label="✅ Analyse terminée", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ Une erreur est survenue", state="error")
            st.exception(e)
            st.stop()

    st.session_state["result"] = result  # persiste pour les téléchargements / onglets


# ============================================================
# Résultats (persistants entre reruns)
# ============================================================
result = st.session_state.get("result")
if result:
    artifacts = result.get("artifacts", {}) or {}
    swot = _parse(artifacts.get("swot"))
    strat = _parse(artifacts.get("strategy"))
    design = _parse(artifacts.get("design"))
    img = artifacts.get("image")
    img_path = img.get("path") if isinstance(img, dict) else (img if isinstance(img, str) else None)
    img_url = img.get("url") if isinstance(img, dict) else None

    # --- KPIs ---
    st.markdown("### 📊 Synthèse")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Échanges A2A", result.get("iterations", 0))
    m2.metric("Messages clés", len(strat.get("key_messages", []) or strat.get("messages", [])))
    m3.metric("Canaux", len(strat.get("channels", [])))
    m4.metric("KPIs", len(strat.get("kpis", []) or strat.get("KPIs", [])))

    tab1, tab2, tab3 = st.tabs(["✨ Aperçu", "📄 Rapport complet", "🧩 Données (JSON)"])

    # ---- Aperçu visuel ----
    with tab1:
        if design.get("tagline"):
            st.markdown(f"<div class='tagbig'>« {design['tagline']} »</div>",
                        unsafe_allow_html=True)
        left, right = st.columns([1, 1])
        with left:
            if strat.get("positioning"):
                st.markdown("**🎯 Positionnement**")
                st.info(strat["positioning"])
            if swot:
                st.markdown("**📊 SWOT (aperçu)**")
                s1, s2 = st.columns(2)
                s1.success("**Forces**\n\n" + "\n".join(f"- {x}" for x in swot.get("strengths", [])[:3]) or "–")
                s2.error("**Faiblesses**\n\n" + "\n".join(f"- {x}" for x in swot.get("weaknesses", [])[:3]) or "–")
                s3, s4 = st.columns(2)
                s3.info("**Opportunités**\n\n" + "\n".join(f"- {x}" for x in swot.get("opportunities", [])[:3]) or "–")
                s4.warning("**Menaces**\n\n" + "\n".join(f"- {x}" for x in swot.get("threats", [])[:3]) or "–")
        with right:
            if img_path and os.path.exists(img_path):
                st.image(img_path, caption="🎨 Visuel généré", use_container_width=True)
            elif img_url:
                st.image(img_url, caption="🎨 Visuel généré", use_container_width=True)
            else:
                st.caption("Aucun visuel généré.")
            if design.get("visual_style"):
                st.markdown("**Direction visuelle**")
                st.write(design["visual_style"])

    # ---- Rapport complet ----
    with tab2:
        report_html = build_html_report(result)
        components.html(report_html, height=1300, scrolling=True)
        cta1, cta2 = st.columns(2)
        cta1.download_button("💾 Télécharger en HTML", data=report_html,
                             file_name="rapport_marketing.html", mime="text/html",
                             use_container_width=True)
        try:
            cta2.download_button("📄 Télécharger en PDF", data=pdf_bytes(result),
                                 file_name="rapport_marketing.pdf",
                                 mime="application/pdf", use_container_width=True)
        except Exception as e:
            cta2.caption(f"PDF indisponible : {e}")

    # ---- JSON ----
    with tab3:
        st.json(result, expanded=False)
        st.download_button("💾 Télécharger le JSON",
                           data=json.dumps(result, indent=2, ensure_ascii=False),
                           file_name="a2a_result.json", mime="application/json",
                           use_container_width=True)
