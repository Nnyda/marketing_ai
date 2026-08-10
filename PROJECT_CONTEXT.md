# Contexte du projet — Multi-Agent Digital Marketing Advisor

> Document destiné à donner à Claude (ou tout collaborateur) une vue complète du
> projet pour continuer à le développer. À placer dans la base de connaissances
> du Projet Claude.

## 1. Objectif du projet

Système multi-agent qui génère une stratégie marketing complète à partir d'une
demande utilisateur. Il reproduit une équipe marketing (Analyste → Stratège →
Designer) avec une **coordination Agent-to-Agent (A2A) à boucles de feedback** :
chaque agent en aval évalue le travail de l'amont et peut demander une révision.

Sortie : SWOT, stratégie (positionnement, messages, canaux, KPIs), concept
créatif (tagline, style, maquettes) + image générée, le tout dans un rapport
HTML/PDF soigné.

Projet académique — auteurs : ADJENIA Danelius, BALDE Ibrahima,
BOULANKI Loukmane, D'OLIVERRA Johnny.

## 2. Architecture

```
 Analyst  --SWOT-->  Strategist  --strategy-->  Designer  --> concept + image
    ^                    |             ^             |
    +---- feedback ------+             +-- feedback -+
```

Socle A2A : `AgentCard` (capacités d'un agent), `Message` (échange horodaté),
`Task` (objet partagé qui circule et accumule artefacts + journal de feedback).

Modèles OpenAI : `gpt-4o-mini` (texte + vision), image via `dall-e-3` avec repli
automatique sur `gpt-image-1`.

## 3. Fichiers du projet

| Fichier | Rôle |
|---|---|
| `agents/analyst_agent.py` | Socle A2A (Task/Message/AgentCard), `build_context`, `call_json` (JSON + vision), AnalystAgent (SWOT) |
| `agents/strategist_agent.py` | StrategistAgent : stratégie + `review_swot` (feedback à l'Analyste) |
| `agents/designer_agent.py` | DesignerAgent : concept + image (repli de modèle) + `review_strategy` |
| `orchestrator.py` | `A2AOrchestrator` : enchaînement + boucles de feedback (`max_iterations`) |
| `report.py` | Rapport HTML autonome (image en base64) |
| `report_pdf.py` | Rapport PDF (fpdf2, sans dépendance système) |
| `file_ingest.py` | Extraction texte (txt/md/csv/pdf/docx/pptx), images→data-URI, `fetch_url` |
| `streamlit_app.py` | Interface web : brief + champs + documents + images + URL → rapport |
| `main.py` | Point d'entrée CLI |
| `requirements.txt` | Dépendances |
| `key.env.example` | Modèle de configuration (clé OpenAI) |

## 4. Entrées supportées (par l'interface)

- Brief libre en langage naturel + champs optionnels (objectif, cible, budget,
  canaux, ton).
- Documents téléversés : txt, md, csv, pdf, docx, pptx (source de faits).
- Images : propositions de visuels du produit (analysées par vision).
- URL : pitchdeck / page web / PDF / Google Slides-Docs partagés.

## 5. Lancer le projet

```bash
pip install -r requirements.txt
cp key.env.example key.env      # renseigner OPENAI_API_KEY
streamlit run streamlit_app.py  # interface web
# ou : python main.py           # ligne de commande
```

## 6. État actuel

Fonctionnel de bout en bout : boucles de feedback A2A, entrées multiples
(texte/fichiers/images/URL), rapports HTML + PDF. Testé (compilation + flux
simulé avec faux client).

## 7. Limitations connues / pistes d'amélioration

- Le SWOT s'appuie sur les connaissances du modèle si aucune source n'est
  fournie → risque d'hallucination. Fournir documents/URL pour fiabiliser.
- Pas encore de recherche web automatique intégrée aux agents.
- Pas de logging du coût/temps par étape.
- Pas d'historique des campagnes (comparer plusieurs runs).
- Google Slides/Docs doivent être partagés publiquement ; pages 100 % JS peu
  exploitables.
- Accès au modèle d'image dépend de la vérification du compte OpenAI.

## 8. Sécurité

`key.env` contient la clé OpenAI et ne doit JAMAIS être versionné (déjà dans
`.gitignore`). Régénérer la clé si elle a été exposée.
