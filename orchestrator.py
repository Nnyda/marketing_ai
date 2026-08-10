# marketing_ai/orchestrator.py
import json
from datetime import datetime
from agents import AnalystAgent, StrategistAgent, DesignerAgent
from agents.analyst_agent import Task


class A2AOrchestrator:
    """
    Orchestrateur multi-agent avec coordination A2A iterative.

    Contrairement a un simple pipeline sequentiel, chaque agent en aval
    *evalue* le travail de l'agent en amont. S'il le juge insuffisant, il
    renvoie un feedback et l'agent en amont revise sa production. Ces boucles
    sont limitees a `max_iterations` pour garantir la terminaison.

        Analyst  --SWOT-->  Strategist  --strategy-->  Designer
           ^                    |            ^              |
           +---- feedback ------+            +--- feedback -+
    """

    def __init__(self, client, max_iterations: int = 2):
        self.analyst = AnalystAgent(client)
        self.strategist = StrategistAgent(client)
        self.designer = DesignerAgent(client)
        self.max_iterations = max_iterations

    @staticmethod
    def _notify(progress, message):
        """Appelle le callback de progression s'il existe (pour l'UI en direct)."""
        if progress:
            try:
                progress(message)
            except Exception:
                pass

    def _refine_loop(self, task, producer, reviewer, review_fn,
                     producer_label, reviewer_label, progress=None):
        """
        Boucle generique de feedback A2A entre un producteur (amont) et un
        relecteur (aval). Le relecteur juge l'artefact ; s'il est insuffisant,
        le producteur revise. On repete jusqu'a satisfaction ou epuisement.
        """
        for iteration in range(1, self.max_iterations + 1):
            review = review_fn(task)
            task.log_feedback(
                sender=reviewer_label,
                receiver=producer_label,
                iteration=iteration,
                sufficient=review["sufficient"],
                feedback=review["feedback"],
            )

            if review["sufficient"]:
                print(f"[A2A] {reviewer_label} validates {producer_label}'s output "
                      f"(iteration {iteration}).")
                self._notify(progress, f"✅ {reviewer_label} valide le travail de "
                                       f"{producer_label} (itération {iteration}).")
                return task

            print(f"[A2A] {reviewer_label} requests changes to {producer_label} "
                  f"(iteration {iteration}): {review['feedback'][:80]}...")
            self._notify(progress, f"🔁 {reviewer_label} demande une révision "
                                   f"(itération {iteration})…")
            # L'agent en amont revise en tenant compte du feedback
            producer.process_task(task, feedback=review["feedback"])

        print(f"[A2A] Max iterations reached between {reviewer_label} and "
              f"{producer_label}; proceeding with best available output.")
        return task

    def run_campaign(self, product_name: str, target_country: str,
                     brief: str = "", extra: dict = None,
                     documents: str = "", images: list = None,
                     generate_image: bool = True, progress=None):
        task_id = f"campaign_{datetime.now():%Y%m%d_%H%M%S}"
        task = Task(task_id, {
            "product_name": product_name,
            "target_country": target_country,
            "brief": brief,
            "extra": extra or {},
            "documents": documents or "",
            "images": images or [],   # data-URI base64 pour la vision
        })
        print(f"A2A Workflow started -> {task_id}")

        # 1. Analyste : SWOT initial
        self._notify(progress, "🔍 Analyste : analyse du marché (SWOT)…")
        self.analyst.process_task(task)
        self._notify(progress, "✓ SWOT produit.")

        # 2. Boucle A2A : le Stratege relit le SWOT, l'Analyste revise si besoin
        self._refine_loop(
            task,
            producer=self.analyst, reviewer=self.strategist,
            review_fn=self.strategist.review_swot,
            producer_label="AnalystAgent", reviewer_label="StrategistAgent",
            progress=progress,
        )

        # 3. Stratege : strategie a partir d'un SWOT valide
        self._notify(progress, "🎯 Stratège : élaboration de la stratégie…")
        self.strategist.process_task(task)
        self._notify(progress, "✓ Stratégie produite.")

        # 4. Boucle A2A : le Designer relit la strategie, le Stratege revise si besoin
        self._refine_loop(
            task,
            producer=self.strategist, reviewer=self.designer,
            review_fn=self.designer.review_strategy,
            producer_label="StrategistAgent", reviewer_label="DesignerAgent",
            progress=progress,
        )

        # 5. Designer : concepts creatifs + image
        self._notify(progress, "🎨 Designer : concept créatif" +
                     (" + génération du visuel…" if generate_image else "…"))
        self.designer.process_task(task, generate_image=generate_image)
        self._notify(progress, "✓ Concept créatif produit.")

        return self._build_result(task, product_name, target_country)

    # Compatibilite ascendante avec l'ancien nom
    def run_ecovibe(self, product_name: str, target_country: str):
        return self.run_campaign(product_name, target_country)

    def _build_result(self, task, product_name, target_country):
        artifacts_dict = {}
        for artifact in task.artifacts:
            artifact_type = artifact["type"]
            if "content" in artifact:
                artifacts_dict[artifact_type] = artifact["content"]
            else:
                artifacts_dict[artifact_type] = {k: v for k, v in artifact.items() if k != "type"}

        result = {
            "task_id": task.task_id,
            "input": {
                "product": product_name,
                "country": target_country,
                "brief": task.input.get("brief", ""),
                "extra": task.input.get("extra", {}),
            },
            "artifacts": artifacts_dict,
            "collaboration_log": task.feedback_log,  # trace des echanges A2A
            "iterations": len(task.feedback_log),
        }

        with open("a2a_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Workflow completed -> a2a_result.json "
              f"({len(task.feedback_log)} A2A feedback exchanges logged)")
        return result
