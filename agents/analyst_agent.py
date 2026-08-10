# agents/analyst_agent.py
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import OpenAI


# ============================================================
# === A2A Core (Task / Message / AgentCard) ===
# ============================================================
class AgentCard:
    def __init__(self, name: str, description: str, skills: list, endpoint: str = "local"):
        self.data = {
            "name": name,
            "description": description,
            "url": endpoint,
            "skills": skills,
            "version": "2.0",
        }

    def to_json(self) -> str:
        return json.dumps(self.data, indent=2)


class Message:
    def __init__(self, role: str, content: str, metadata: Dict[str, Any] = None):
        self.role = role
        self.content = content
        self.metadata = metadata or {"timestamp": datetime.now().isoformat()}


class Task:
    def __init__(self, task_id: str, input_data: Dict[str, Any]):
        self.task_id = task_id
        self.status = "pending"
        self.input = input_data
        self.messages = [Message("client", json.dumps(input_data))]
        self.artifacts: List[Dict[str, Any]] = []
        # Journal de collaboration A2A : trace chaque echange de feedback
        self.feedback_log: List[Dict[str, Any]] = []

    def add_message(self, message: Message):
        self.messages.append(message)
        self.status = "working"

    def complete(self, artifact: Dict[str, Any]):
        # Remplace l'artefact du meme type s'il existe deja (utile lors des revisions)
        self.artifacts = [a for a in self.artifacts if a.get("type") != artifact.get("type")]
        self.artifacts.append(artifact)
        self.status = "completed"

    def get_artifact(self, artifact_type: str) -> Optional[str]:
        return next((a["content"] for a in self.artifacts if a["type"] == artifact_type), None)

    def log_feedback(self, sender: str, receiver: str, iteration: int,
                     sufficient: bool, feedback: str):
        """Enregistre un echange de feedback entre deux agents (coordination A2A)."""
        entry = {
            "iteration": iteration,
            "from": sender,
            "to": receiver,
            "sufficient": sufficient,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        }
        self.feedback_log.append(entry)
        self.add_message(Message("feedback", json.dumps(entry, ensure_ascii=False)))


# ============================================================
# === Helper : appel JSON fiable ===
# ============================================================
def build_context(data: Dict[str, Any]) -> str:
    """Formate la demande du client (produit, pays, brief libre + champs optionnels)
    en un bloc de contexte lisible, partage par tous les agents."""
    lines = []
    if data.get("product_name"):
        lines.append(f"Product: {data['product_name']}")
    if data.get("target_country"):
        lines.append(f"Target country / market: {data['target_country']}")
    if data.get("brief"):
        lines.append(f"Client brief: {data['brief']}")
    extra = data.get("extra") or {}
    labels = {
        "objective": "Objective",
        "audience": "Target audience",
        "budget": "Budget",
        "channels": "Preferred channels",
        "tone": "Brand tone / style",
    }
    for key, label in labels.items():
        if extra.get(key):
            lines.append(f"{label}: {extra[key]}")
    if data.get("documents"):
        lines.append(
            "\nReference documents provided by the client "
            "(use them as the primary source of facts):\n"
            f"{data['documents']}"
        )
    return "\n".join(lines) if lines else "No details provided."


def call_json(client: OpenAI, system: str, user: str,
              model: str = "gpt-4o-mini", max_tokens: int = 700,
              temperature: float = 0.7, images=None) -> Dict[str, Any]:
    """Appelle le modele en forcant une reponse JSON valide (structured output natif).

    Si `images` (liste de data-URI base64) est fourni, elles sont transmises au
    modele multimodal en plus du texte (vision)."""
    if images:
        user_content = [{"type": "text", "text": user}]
        for uri in images:
            user_content.append({"type": "image_url", "image_url": {"url": uri}})
    else:
        user_content = user

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# ============================================================
# === AnalystAgent ===
# ============================================================
class AnalystAgent:
    def __init__(self, client: OpenAI):
        self.client = client
        self.name = "AnalystAgent"
        self.system_prompt = (
            "You are a senior market analyst. "
            "Provide a complete SWOT analysis as a JSON object with this exact structure: "
            '{ "strengths": [], "weaknesses": [], "opportunities": [], "threats": [] }. '
            "Each list must contain concise, professional, specific points."
        )
        self.card = AgentCard(
            name=self.name,
            description="SWOT market analysis for a product in a country",
            skills=[{"id": "swot", "name": "SWOT Analysis"}],
        )

    def process_task(self, task: Task, feedback: str = "") -> Task:
        """Produit (ou revise) le SWOT. Si feedback est fourni, il revise son analyse."""
        images = task.input.get("images")
        user_msg = (
            "Produce a SWOT analysis for the following request:\n"
            f"{build_context(task.input)}"
        )
        if images:
            user_msg += ("\n\nAttached are the client's OWN proposed visuals for this product. "
                         "Analyze them (design, packaging, positioning cues they convey) and "
                         "factor these observations into the SWOT — e.g. whether the visual "
                         "identity is a strength or needs work versus the target market.")
        if feedback:
            previous = task.get_artifact("swot") or ""
            user_msg += (
                f"\n\nYour previous SWOT was:\n{previous}\n\n"
                f"A downstream strategist gave this feedback. "
                f"Revise and improve the SWOT accordingly:\n{feedback}"
            )

        result = call_json(self.client, self.system_prompt, user_msg, images=images)
        output = json.dumps(result, ensure_ascii=False, indent=2)

        task.add_message(Message("agent", output))
        task.complete({"type": "swot", "content": output, "agent": self.name})
        tag = "revised" if feedback else "created"
        print(f"[{self.name}] SWOT analysis {tag}.")
        return task
