# 🌿 Multi-Agent Digital Marketing Advisor

**Un système multi-agent avec coordination Agent-to-Agent (A2A) qui produit une
stratégie marketing complète à partir d'un simple produit et pays cible :
analyse de marché → stratégie → concept créatif + visuel généré.**

Le système reproduit une vraie équipe marketing (Analyste → Stratège → Designer),
mais avec une collaboration automatique et **des boucles de feedback** entre agents,
là où les pipelines classiques se contentent d'un enchaînement séquentiel.

---

## ✨ Fonctionnalités

- **Trois agents spécialisés** qui collaborent sur une même tâche partagée.
- **Coordination A2A avec feedback** : chaque agent en aval évalue le travail de
  l'amont et peut demander une révision (boucles itératives bornées).
- **Journal de collaboration** (`collaboration_log`) qui trace chaque échange —
  idéal pour rendre la coopération visible.
- **Brief en langage naturel** : décris ta demande librement, avec des champs
  optionnels (objectif, cible, budget, canaux, ton) qui affinent le résultat.
- **Téléversement de documents** (txt, md, csv, pdf, docx, pptx) : les agents
  lisent le contenu (fiche produit, étude de marché, pitchdeck) et s'en servent
  comme source de faits — idéal pour une marque peu connue du modèle.
- **Lien / URL en entrée** : colle un lien vers un pitchdeck, une page web, un
  PDF/Word/PowerPoint ou un Google Slides/Docs partagé ; l'agent télécharge le
  contenu et l'ajoute au contexte.
- **Images en entrée (vision)** : téléverse tes propositions de visuels pour le
  produit ; l'Analyste les analyse pour le SWOT et le Designer construit un
  concept cohérent qui s'appuie sur elles et les affine (via `gpt-4o-mini`,
  multimodal).
- **Rapport soigné en HTML et en PDF** généré automatiquement (SWOT, stratégie,
  concept, visuel intégré, journal A2A), affiché dans l'appli et téléchargeable.
  Le HTML est une page autonome ; le PDF est produit avec `fpdf2` (aucune
  dépendance système à installer).
- **Sorties JSON fiables** via le mode natif `response_format={"type":"json_object"}`.
- **Génération d'image** du concept créatif, avec repli automatique
  `dall-e-3` → `gpt-image-1` selon les modèles disponibles sur le compte.
- **Interface web Streamlit** (brief + rapport) et **CLI** en une commande.

---

## 🧠 Architecture

```
 Analyst  --SWOT-->  Strategist  --strategy-->  Designer  --> concept + image
    ^                    |             ^             |
    +---- feedback ------+             +-- feedback -+
```

1. L'**Analyste** produit un SWOT (forces / faiblesses / opportunités / menaces).
2. Le **Stratège** relit le SWOT (`review_swot`). S'il le juge insuffisant, il
   renvoie un feedback et l'Analyste **révise**. On répète jusqu'à validation
   (ou `max_iterations`).
3. Le **Stratège** produit la stratégie (positionnement, messages, canaux, KPIs).
4. Le **Designer** relit la stratégie (`review_strategy`), même logique de boucle.
5. Le **Designer** produit le concept créatif (tagline, style visuel, maquettes)
   et génère un visuel.

Le socle A2A repose sur trois objets : `AgentCard` (carte de capacités de
l'agent), `Message` (échange horodaté) et `Task` (objet partagé qui circule et
accumule artefacts + journal de feedback).

---

## 📦 Structure du projet

```
marketing_ai/
├── agents/
│   ├── __init__.py
│   ├── analyst_agent.py      # AnalystAgent + socle A2A (Task/Message/AgentCard)
│   ├── strategist_agent.py   # StrategistAgent + review_swot
│   └── designer_agent.py     # DesignerAgent + review_strategy + image
├── orchestrator.py           # A2AOrchestrator : enchaînement + boucles de feedback
├── report.py                 # Génère le rapport HTML soigné et autonome
├── report_pdf.py             # Génère le rapport PDF (fpdf2, sans dépendance système)
├── file_ingest.py            # Extrait le texte des documents téléversés (pdf, docx, txt…)
├── main.py                   # Point d'entrée CLI
├── streamlit_app.py          # Interface web (brief + rapport)
├── requirements.txt
├── key.env.example           # Modèle de config (copier vers key.env)
└── README.md
```

---

## 🚀 Installation

```bash
git clone <votre-repo>.git
cd marketing_ai

python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate

pip install -r requirements.txt

cp key.env.example key.env      # puis renseignez votre clé OpenAI
```

`key.env` :

```
OPENAI_API_KEY=sk-votre-cle-ici
```

> ⚠️ `key.env` est listé dans `.gitignore` : ne committez jamais votre clé.

---

## ▶️ Utilisation

**En ligne de commande :**

```bash
python main.py
```

**Interface web :**

```bash
streamlit run streamlit_app.py
```

**Dans votre code :**

```python
from openai import OpenAI
from orchestrator import A2AOrchestrator
from report import save_html_report

client = OpenAI(api_key="sk-...")
orch = A2AOrchestrator(client, max_iterations=2)
result = orch.run_campaign(
    product_name="GreenTech Watch",
    target_country="Germany",
    brief="Montre connectée écologique premium pour jeunes urbains.",
    extra={"audience": "18-35 urbains", "tone": "premium, engagé",
           "channels": "Instagram, TikTok"},
)
save_html_report(result, "a2a_report.html")   # rapport HTML soigné
```

Dans l'interface web, un champ **brief libre** + des champs optionnels
(objectif, cible, budget, canaux, ton) permettent de formuler la demande, et le
**rapport HTML** s'affiche directement avec un bouton de téléchargement.

`max_iterations` fixe le nombre de tours de feedback par lien inter-agents.
`max_iterations=0` reproduit un pipeline purement séquentiel (utile pour comparer
en démo). Le résultat est aussi écrit dans `a2a_result.json`.

---

## 🛠️ Stack technique

- Python 3.9+
- [OpenAI API](https://platform.openai.com/) (GPT-4o-mini + DALL·E 3)
- Streamlit · python-dotenv

---

## 🗺️ Pistes d'évolution

- Ancrer le SWOT dans des données réelles (recherche web / sources).
- Logger le temps et le coût (tokens) par étape.
- Ajouter un agent « critique » global en fin de chaîne.

---

## 👥 Auteurs

- ADJENIA Danelius
- BALDE Ibrahima
- BOULANKI Loukmane
- D'OLIVERRA Johnny

---

## 📄 Licence

Projet académique. Ajoutez ici la licence de votre choix (par ex. MIT).
