import asyncio
import json
import multiprocessing
import os

import polars as pl
from test_env import setup, teardown

import env
from main import AgentsWorkflow
from models.score import Score
from models.workflow import Workflow
from tools import set_base_path
from utils.functional_test import run_functional_test
from utils.logger import init_state_logger, log_progress, log_score
from utils.scores import print_scores


def run_agents(workflow: Workflow):
    set_base_path(f"{env.repositories_path}/{workflow.repository_name}")
    init_state_logger(workflow.id, log_to_term=True)
    agents_workflow = AgentsWorkflow(
        f"{env.repositories_path}/{workflow.repository_name}"
    )
    prompt = workflow.get_prompt(1)
    generated_workflow = agents_workflow.run(prompt)

    log_progress(
        f"Generated workflow for {workflow.repository_name}:\n{generated_workflow}"
    )

    return generated_workflow


def print_scores_by_tier(scores: list[Score], save_dir: str):
    with open(os.path.join(save_dir, "scores.jsonl"), "w") as f:
        for score in scores:
            f.write(json.dumps(score.to_dict()) + "\n")
    data = pl.DataFrame(
        [s.to_dict() for s in scores], infer_schema_length=len(scores), strict=False
    )

    print("\n" + "=" * 60)
    print("OVERALL RESULTS")
    print("=" * 60)
    print_scores(data, save_dir, suffix="_overall")

    for tier in ["easy", "medium", "hard"]:
        tier_scores = [s for s in scores if s.difficulty_tier == tier]
        if tier_scores:
            tier_data = pl.DataFrame(
                [s.to_dict() for s in tier_scores],
                infer_schema_length=len(tier_scores),
                strict=False,
            )
            print("\n" + "=" * 60)
            print(f"{tier.upper()} TIER ({len(tier_scores)} workflows)")
            print("=" * 60)
            print_scores(tier_data, save_dir, suffix=f"_{tier}")


if __name__ == "__main__":
    workflows = Workflow.load("hard")
    # workflows = workflows[2:10]
    scores = []
    prompt_level = 1
    for workflow in workflows:
        setup(workflow)

    with multiprocessing.Pool(processes=24) as pool:
        generated_workflows = pool.map(run_agents, workflows)

    for workflow, generated_workflow in zip(workflows, generated_workflows):
        log_progress("Running functional test...")
        functional_result = run_functional_test(
            generated_workflow,
            workflow.triggers[0] if workflow.triggers else "push",
            f"{env.repositories_path}/{workflow.repository_name}",
        )
        log_progress("Functional tests completed")
        score: Score = asyncio.run(
            Score.new(
                workflow, generated_workflow, prompt_level, "main", functional_result
            )
        )
        log_score(score)
        score.save(f"{env.results_path}/id/{workflow.id}")
        scores.append(score)

        teardown(workflow)

    print_scores_by_tier(scores, env.results_path)

    for filename in os.listdir(env.tmp_path):
        os.remove(os.path.join(env.tmp_path, filename))
