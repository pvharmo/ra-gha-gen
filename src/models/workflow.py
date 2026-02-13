from __future__ import annotations

from dataclasses import dataclass

import polars as pl

import env
from utils.formatting import WorkflowYAML


@dataclass
class Workflow:
    id: int
    repository_id: int
    repository_name: str
    repository_owner: str
    file_name: str
    file_content: str
    mainLanguage: str
    tokens_count: int
    augmented_workflow: str
    workflow: WorkflowYAML
    triggers: list[str]
    nb_triggers: int
    nb_actions: int
    nb_jobs: int
    actions: list[str]
    actions_details: list[dict[str, str]]
    nb_reusable_workflows: int
    reusable_workflows: list[str]
    nb_steps: int
    cyclomatic_complexity: int
    prompt_level1: str
    prompt_level2: str
    prompt_level3: str

    @classmethod
    def load(cls, name: str) -> list[Workflow]:
        data = pl.read_ndjson(f"{env.dataset_path}/{name}.jsonl")

        workflows = data.to_dicts()
        return [cls(**workflow) for workflow in workflows]

    def get_prompt(self, level: int) -> str:
        if level == 1:
            return self.prompt_level1
        elif level == 2:
            return self.prompt_level2
        elif level == 3:
            return self.prompt_level3
        else:
            raise ValueError("Invalid prompt level")

    @property
    def difficulty_tier(self) -> str:
        score = (
            self.cyclomatic_complexity
            + self.nb_jobs
            + self.nb_reusable_workflows * 3
            + (1 if self.nb_triggers > 1 else 0)
            + len([a for a in self.actions if "docker" in a.lower()])
        )
        if score <= 2:
            return "easy"
        elif score <= 5:
            return "medium"
        return "hard"

    @property
    def difficulty_score(self) -> int:
        return (
            self.cyclomatic_complexity
            + self.nb_jobs
            + self.nb_reusable_workflows * 3
            + (1 if self.nb_triggers > 1 else 0)
            + len([a for a in self.actions if "docker" in a.lower()])
        )

    @classmethod
    def get_wf_by_id(self, name: str, id: int) -> Workflow:
        workflows = self.load(name)
        for wf in workflows:
            if wf.id == id:
                return wf
        raise ValueError(f"Workflow with id {id} not found")
