# agents/designer_agent.py
import json
import base64
import urllib.request
import time
from openai import OpenAI
from .analyst_agent import AgentCard, Message, Task, call_json, build_context

# Modeles d'image essayes dans l'ordre : si le premier n'est pas accessible
# sur le compte (erreur "model does not exist"), on bascule sur le suivant.
IMAGE_MODELS = ["dall-e-3", "gpt-image-1"]


class DesignerAgent:
    def __init__(self, client: OpenAI):
        self.client = client
        self.name = "DesignerAgent"
        self.system_prompt = (
            "You are a creative designer. "
            "Return a JSON object with this exact structure:\n"
            '{ "tagline": "short catchy phrase", '
            '"visual_style": "description of colors, mood, style", '
            '"mockup_ideas": ["idea 1", "idea 2"] }'
        )
        # Prompt de revue : le designer juge si la strategie est assez claire pour creer
        self.review_prompt = (
            "You are a creative designer reviewing a marketing strategy. "
            "Decide whether it gives enough creative direction to design a campaign "
            "(clear positioning, distinct tone/messages, defined channels). "
            "Respond ONLY as a JSON object: "
            '{ "sufficient": true/false, "feedback": "what is missing for the creative work, '
            'or an empty string if sufficient" }.'
        )
        self.card = AgentCard(
            name=self.name,
            description="Creative concepts + image, with A2A review of the strategy",
            skills=[
                {"id": "design", "name": "Creative Design"},
                {"id": "review_strategy", "name": "Review strategy clarity"},
            ],
        )

    def review_strategy(self, task: Task) -> dict:
        """Coordination A2A : evalue la strategie avant de creer les concepts."""
        strategy = task.get_artifact("strategy") or ""
        result = call_json(
            self.client,
            self.review_prompt,
            f"Strategy to review:\n{strategy}",
            max_tokens=300,
        )
        return {
            "sufficient": bool(result.get("sufficient", True)),
            "feedback": result.get("feedback", "") or "",
        }

    def process_task(self, task: Task, feedback: str = "", generate_image: bool = True) -> Task:
        strategy = task.get_artifact("strategy") or ""
        images = task.input.get("images")
        user_msg = (
            f"Client request:\n{build_context(task.input)}\n\n"
            f"Strategy:\n{strategy}"
        )
        if images:
            user_msg += ("\n\nAttached are the CLIENT'S OWN proposed visuals for THIS product. "
                         "Treat them as drafts to build on: keep what works, stay consistent "
                         "with their look (colors, materials, mood), and refine/extend them. "
                         "Your visual_style and mockup_ideas must align with these proposals, "
                         "and briefly note how to improve them.")
        if feedback:
            previous = task.get_artifact("design") or ""
            user_msg += (
                f"\n\nYour previous design was:\n{previous}\n\n"
                f"Feedback to incorporate:\n{feedback}"
            )

        # 1. Concept creatif (JSON fiable)
        design_json = call_json(self.client, self.system_prompt, user_msg,
                                max_tokens=500, images=images)
        design_json_str = json.dumps(design_json, ensure_ascii=False, indent=2)

        task.add_message(Message("agent", design_json_str))
        task.complete({"type": "design", "content": design_json_str, "agent": self.name})
        print(f"[{self.name}] Design JSON created.")

        # 2. Image DALL-E (optionnelle) avec retry
        if generate_image:
            self._generate_image(task, design_json)

        return task

    def _generate_image(self, task: Task, design_json: dict, max_retries: int = 3):
        tagline = design_json.get("tagline", "Eco product")
        ideas = design_json.get("mockup_ideas") or ["product photography"]
        prompt = f"{tagline}. {ideas[0]}. Professional, high-quality, realistic, commercial style."
        img_path = "a2a_design_mockup.png"

        for model in IMAGE_MODELS:
            for attempt in range(max_retries):
                try:
                    print(f"[{self.name}] Generating image with '{model}' "
                          f"(attempt {attempt + 1}/{max_retries})...")
                    image_resp = self.client.images.generate(
                        model=model, prompt=prompt, size="1024x1024", n=1,
                    )
                    data = image_resp.data[0]

                    # dall-e-3 renvoie une URL ; gpt-image-1 renvoie du base64.
                    image_url = getattr(data, "url", None)
                    if image_url:
                        urllib.request.urlretrieve(image_url, img_path)
                    else:
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(data.b64_json))

                    print(f"[{self.name}] Image saved: {img_path} (model={model})")
                    task.complete({"type": "image", "url": image_url,
                                   "path": img_path, "model": model, "agent": self.name})
                    return
                except Exception as e:
                    msg = str(e)
                    print(f"[{self.name}] '{model}' attempt {attempt + 1} failed: {msg}")
                    # Modele indisponible sur ce compte -> inutile de reessayer, on change de modele
                    if any(s in msg for s in ("does not exist", "invalid_value", "model_not_found")):
                        print(f"[{self.name}] '{model}' not available on this account, "
                              f"trying next model...")
                        break
                    if attempt < max_retries - 1:
                        time.sleep(5)

        print(f"[{self.name}] Image generation skipped (no image model available). "
              f"Text artifacts are still complete.")
