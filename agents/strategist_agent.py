# agents/strategist_agent.py
import json
from openai import OpenAI
from .analyst_agent import AgentCard, Message, Task, call_json, build_context


class StrategistAgent:
    def __init__(self, client: OpenAI):
        self.client = client
        self.name = "StrategistAgent"
        self.system_prompt = (
            "You are a marketing strategist. "
            "Based on the SWOT analysis, build a marketing strategy as a JSON object: "
            '{ "positioning": "...", "key_messages": [], "channels": [], "kpis": [] }.'
        )
        # Prompt de revue : le stratege juge si le SWOT recu est exploitable
        self.review_prompt = (
            "You are a marketing strategist reviewing a SWOT analysis produced by an analyst. "
            "Decide whether it contains enough actionable information to build a solid strategy "
            "(clear differentiators, target insights, competitive context, pricing/market cues). "
            "Respond ONLY as a JSON object: "
            '{ "sufficient": true/false, "feedback": "what is missing or should be improved, '
            'or an empty string if sufficient" }.'
        )
        self.card = AgentCard(
            name=self.name,
            description="Marketing strategy based on SWOT, with A2A review of the analyst output",
            skills=[
                {"id": "strategy", "name": "Marketing Strategy"},
                {"id": "review_swot", "name": "Review SWOT quality"},
            ],
        )

    def review_swot(self, task: Task) -> dict:
        """Coordination A2A : evalue le SWOT de l'analyste avant de l'utiliser."""
        swot = task.get_artifact("swot") or ""
        result = call_json(
            self.client,
            self.review_prompt,
            f"SWOT to review:\n{swot}",
            max_tokens=300,
        )
        return {
            "sufficient": bool(result.get("sufficient", True)),
            "feedback": result.get("feedback", "") or "",
        }

    def process_task(self, task: Task, feedback: str = "") -> Task:
        swot = task.get_artifact("swot") or ""
        user_msg = (
            f"Client request:\n{build_context(task.input)}\n\n"
            f"SWOT:\n{swot}\n\nBuild the marketing strategy."
        )
        if feedback:
            previous = task.get_artifact("strategy") or ""
            user_msg += (
                f"\n\nYour previous strategy was:\n{previous}\n\n"
                f"A downstream designer gave this feedback. Revise the strategy accordingly:\n{feedback}"
            )

        result = call_json(self.client, self.system_prompt, user_msg)
        output = json.dumps(result, ensure_ascii=False, indent=2)

        task.add_message(Message("agent", output))
        task.complete({"type": "strategy", "content": output, "agent": self.name})
        tag = "revised" if feedback else "generated"
        print(f"[{self.name}] Strategy {tag}.")
        return task
