import asyncio
import multiprocessing
import os
import shutil

import polars as pl

import env
from main import AgentsWorkflow
from models.score import Score
from models.workflow import Workflow
from tools import set_base_path
from utils.logger import init_state_logger, log_score
from utils.scores import print_scores


def pool_task(workflow: Workflow):
    shutil.move(
        f"{env.repositories_path}/{workflow.repository_name}/.github/workflows/{workflow.file_name}",
        f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}",
    )
    set_base_path(f"{env.repositories_path}/{workflow.repository_name}")
    init_state_logger(workflow.id, log_to_term=False)
    agents_workflow = AgentsWorkflow(
        f"{env.repositories_path}/{workflow.repository_name}"
    )
    prompt_level = 1
    prompt = workflow.get_prompt(1)
    generated_workflow = agents_workflow.run(prompt)
    score: Score = asyncio.run(
        Score.new(workflow, generated_workflow, prompt_level, "main")
    )
    log_score(score)
    shutil.move(
        f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}",
        f"{env.repositories_path}/{workflow.repository_name}/.github/workflows/{workflow.file_name}",
    )
    return score


if __name__ == "__main__":
    workflows = Workflow.load("invalids")
    workflows = workflows[:1]
    scores = []
    with multiprocessing.Pool(processes=100) as pool:
        results = pool.map(pool_task, workflows)

        data = pl.DataFrame(results, infer_schema_length=len(results), strict=False)
        print_scores(data, env.results_path)

    for filename in os.listdir(env.tmp_path):
        os.remove(os.path.join(env.tmp_path, filename))
