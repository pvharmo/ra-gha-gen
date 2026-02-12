import asyncio
import os

import polars as pl

import env

# from graph import build_graph, run_graph
from main import AgentsWorkflow
from models.score import Score
from models.workflow import Workflow
from utils.logger import init_state_logger, log_score
from utils.scores import print_scores


def main():
    workflows = Workflow.load("invalids")
    scores = []

    for workflow in workflows[2:3]:
        print("----------------------------------------------------------------")
        print("Running workflow:", workflow.id)
        agents_workflow = AgentsWorkflow(
            f"{env.repositories_path}/{workflow.repository_owner}/{workflow.repository_name}"
        )
        init_state_logger(workflow.id)
        prompt_level = 1
        prompt = workflow.get_prompt(1)
        # graph = build_graph("main", True)
        # generated_workflow = run_graph(graph, prompt)
        generated_workflow = agents_workflow.run(prompt)
        score: Score = asyncio.run(
            Score.new(workflow, generated_workflow, prompt_level, "main")
        )
        log_score(score)
        scores.append(score)

    data = pl.DataFrame(scores, infer_schema_length=len(scores), strict=False)
    # data.write_ndjson(env.results_path + "/scores.jsonl")
    print_scores(data, env.results_path)

    for filename in os.listdir(env.tmp_path):
        os.remove(os.path.join(env.tmp_path, filename))


if __name__ == "__main__":
    main()
