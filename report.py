# marketing_ai/report.py
"""Assemble le resultat du workflow A2A en un rapport HTML autonome et style.

Le HTML produit est self-contained (CSS inline, image encodee en base64), donc
il s'affiche dans Streamlit et se telecharge / s'ouvre dans n'importe quel
navigateur sans dependances.
"""
import os
import json
import base64
import html
from datetime import datetime


def _parse(raw):
    """Renvoie un dict a partir d'un artefact JSON (str ou deja dict)."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _esc(x) -> str:
    return html.escape(str(x))


def _list_items(items) -> str:
    if not items:
        return "<li class='muted'>–</li>"
    return "".join(f"<li>{_esc(i)}</li>" for i in items)


def _image_data_uri(image_artifact) -> str:
    """Encode l'image locale en data-URI base64 pour un rapport autonome."""
    path = None
    if isinstance(image_artifact, dict):
        path = image_artifact.get("path")
        url = image_artifact.get("url")
    elif isinstance(image_artifact, str):
        path = image_artifact
        url = None
    else:
        url = None
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    return url or ""


def build_html_report(result: dict) -> str:
    inp = result.get("input", {}) or {}
    artifacts = result.get("artifacts", {}) or {}
    swot = _parse(artifacts.get("swot")) or {}
    strategy = _parse(artifacts.get("strategy")) or {}
    design = _parse(artifacts.get("design")) or {}
    img_uri = _image_data_uri(artifacts.get("image"))
    log = result.get("collaboration_log", []) or []

    product = _esc(inp.get("product", "—"))
    country = _esc(inp.get("country", "—"))
    brief = _esc(inp.get("brief", "")) or "—"
    extra = inp.get("extra", {}) or {}
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- Bloc extras (champs optionnels renseignes) ---
    extra_labels = {"objective": "Objectif", "audience": "Cible",
                    "budget": "Budget", "channels": "Canaux", "tone": "Ton"}
    extra_html = "".join(
        f"<span class='chip'><b>{_esc(lbl)}</b>: {_esc(extra[k])}</span>"
        for k, lbl in extra_labels.items() if extra.get(k)
    )

    # --- Journal de collaboration A2A ---
    log_html = ""
    for e in log:
        icon = "✅" if e.get("sufficient") else "🔁"
        verb = "a validé" if e.get("sufficient") else "a demandé une révision à"
        fb = f"<div class='fb'>{_esc(e['feedback'])}</div>" if e.get("feedback") else ""
        log_html += (
            f"<div class='logrow'>{icon} <b>Itération {e.get('iteration')}</b> — "
            f"{_esc(e.get('from'))} {verb} {_esc(e.get('to'))}{fb}</div>"
        )
    if not log_html:
        log_html = "<div class='muted'>Aucun échange de feedback enregistré.</div>"

    image_block = (
        f"<img src='{img_uri}' alt='Visuel généré' class='mockup'/>"
        if img_uri else
        "<div class='muted'>Aucun visuel généré (modèle d'image indisponible).</div>"
    )

    messages = strategy.get("key_messages", []) or strategy.get("messages", [])
    channels = strategy.get("channels", [])
    kpis = strategy.get("kpis", []) or strategy.get("KPIs", [])
    mockups = design.get("mockup_ideas", []) or design.get("mockups", [])

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Rapport marketing — {product}</title>
<style>
  :root {{
    --green:#2f7d4f; --green-d:#1e5233; --bg:#f6f8f6; --card:#ffffff;
    --ink:#1c2b22; --muted:#8a988f; --line:#e4ebe5;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; line-height:1.55; }}
  .wrap {{ max-width:880px; margin:0 auto; padding:32px 20px 64px; }}
  header.hero {{ background:linear-gradient(135deg,var(--green),var(--green-d));
    color:#fff; border-radius:18px; padding:28px 30px; margin-bottom:26px; }}
  header.hero h1 {{ margin:0 0 6px; font-size:26px; }}
  header.hero .sub {{ opacity:.9; font-size:14px; }}
  .meta {{ margin-top:14px; display:flex; flex-wrap:wrap; gap:8px; }}
  .chip {{ background:rgba(255,255,255,.16); padding:5px 11px; border-radius:999px;
    font-size:12.5px; }}
  section.card {{ background:var(--card); border:1px solid var(--line);
    border-radius:16px; padding:22px 24px; margin-bottom:20px; }}
  section.card h2 {{ margin:0 0 14px; font-size:18px; color:var(--green-d);
    display:flex; align-items:center; gap:8px; }}
  .brief {{ font-style:italic; color:#42524a; }}
  .swot {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .quad {{ border-radius:12px; padding:14px 16px; }}
  .quad h3 {{ margin:0 0 8px; font-size:14px; text-transform:uppercase; letter-spacing:.4px; }}
  .s {{ background:#eaf6ee; }} .s h3 {{ color:#1e7a44; }}
  .w {{ background:#fdeeee; }} .w h3 {{ color:#b23b3b; }}
  .o {{ background:#eaf1fb; }} .o h3 {{ color:#2a5db0; }}
  .t {{ background:#fbf3e7; }} .t h3 {{ color:#a5701e; }}
  ul {{ margin:0; padding-left:18px; }} li {{ margin:3px 0; font-size:14px; }}
  .muted {{ color:var(--muted); }}
  .pos {{ background:#eaf6ee; border-left:4px solid var(--green); padding:12px 16px;
    border-radius:8px; font-size:15px; margin-bottom:12px; }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  .tag {{ font-size:22px; font-weight:700; color:var(--green-d); text-align:center;
    padding:8px 0 4px; }}
  .mockup {{ width:100%; border-radius:12px; border:1px solid var(--line); }}
  .logrow {{ padding:10px 0; border-bottom:1px dashed var(--line); font-size:14px; }}
  .logrow:last-child {{ border-bottom:none; }}
  .fb {{ margin-top:4px; color:#5b6b61; font-size:13px; }}
  footer {{ text-align:center; color:var(--muted); font-size:12px; margin-top:26px; }}
  @media(max-width:640px) {{ .swot,.cols {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <h1>🌿 Rapport marketing — {product}</h1>
    <div class="sub">Marché : {country} · Généré le {date_str} · {result.get('iterations',0)} échanges A2A</div>
    <div class="meta">{extra_html}</div>
  </header>

  <section class="card">
    <h2>📋 Demande</h2>
    <p class="brief">« {brief} »</p>
  </section>

  <section class="card">
    <h2>📊 Analyse de marché (SWOT)</h2>
    <div class="swot">
      <div class="quad s"><h3>Forces</h3><ul>{_list_items(swot.get('strengths'))}</ul></div>
      <div class="quad w"><h3>Faiblesses</h3><ul>{_list_items(swot.get('weaknesses'))}</ul></div>
      <div class="quad o"><h3>Opportunités</h3><ul>{_list_items(swot.get('opportunities'))}</ul></div>
      <div class="quad t"><h3>Menaces</h3><ul>{_list_items(swot.get('threats'))}</ul></div>
    </div>
  </section>

  <section class="card">
    <h2>🎯 Stratégie</h2>
    <div class="pos"><b>Positionnement :</b> {_esc(strategy.get('positioning','—'))}</div>
    <div class="cols">
      <div><h3 style="font-size:14px;">Messages clés</h3><ul>{_list_items(messages)}</ul></div>
      <div><h3 style="font-size:14px;">Canaux</h3><ul>{_list_items(channels)}</ul></div>
    </div>
    <h3 style="font-size:14px; margin-top:12px;">KPIs</h3><ul>{_list_items(kpis)}</ul>
  </section>

  <section class="card">
    <h2>🎨 Concept créatif</h2>
    <div class="tag">« {_esc(design.get('tagline','—'))} »</div>
    <p><b>Direction visuelle :</b> {_esc(design.get('visual_style','—'))}</p>
    <h3 style="font-size:14px;">Idées de maquettes</h3><ul>{_list_items(mockups)}</ul>
    <div style="margin-top:14px;">{image_block}</div>
  </section>

  <section class="card">
    <h2>🔄 Collaboration A2A</h2>
    {log_html}
  </section>

  <footer>Généré par le Multi-Agent Digital Marketing Advisor · Analyst ⇄ Strategist ⇄ Designer</footer>
</div>
</body>
</html>"""


def save_html_report(result: dict, path: str = "a2a_report.html") -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_html_report(result))
    return path
