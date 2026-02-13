import asyncio
import os

import polars as pl

import env

from main import AgentsWorkflow
from models.score import Score
from models.workflow import Workflow
from utils.functional_test import run_functional_test
from utils.logger import init_state_logger, log_score
from utils.scores import print_scores


def main():
    workflows = Workflow.load("invalids")
    scores = []

    for workflow in workflows[2:3]:
        print("----------------------------------------------------------------")
        print("Running workflow:", workflow.id)
        print(
            f"Difficulty tier: {workflow.difficulty_tier} (score: {workflow.difficulty_score})"
        )
        agents_workflow = AgentsWorkflow(
            f"{env.repositories_path}/{workflow.repository_owner}/{workflow.repository_name}"
        )
        init_state_logger(workflow.id)
        prompt_level = 1
        prompt = workflow.get_prompt(1)
        generated_workflow = agents_workflow.run(prompt)

        functional_result = asyncio.run(
            run_functional_test(
                generated_workflow or "",
                event_type=workflow.triggers[0] if workflow.triggers else "push",
                repository_path=f"{env.repositories_path}/{workflow.repository_owner}/{workflow.repository_name}",
            )
        )

        score = asyncio.run(
            Score.new(
                workflow, generated_workflow, prompt_level, "main", functional_result
            )
        )
        log_score(score)
        scores.append(score)

    data = pl.DataFrame(
        [s.to_dict() for s in scores], infer_schema_length=len(scores), strict=False
    )
    print_scores(data, env.results_path)

    for filename in os.listdir(env.tmp_path):
        os.remove(os.path.join(env.tmp_path, filename))


if __name__ == "__main__":
    main()
