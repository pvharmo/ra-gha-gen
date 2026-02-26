import asyncio
import os
import subprocess
import traceback

import polars as pl

import env
from models.workflow import Workflow
from tools import set_base_path
from utils.functional_test import FunctionalTestResult, run_functional_test


def pool_task(workflow: Workflow):
    try:
        if not os.path.exists(f"{env.repositories_path}/{workflow.repository_name}"):
            subprocess.run(
                f"git clone https://github.com/{env.repositories_path}/{workflow.repository_name}",
                capture_output=True,
                text=True,
                cwd=env.repositories_path,
            )
        set_base_path(f"{env.repositories_path}/{workflow.repository_name}")

        functional_result = asyncio.run(
            run_functional_test(
                workflow.file_content,
                event_type=workflow.triggers[0] if workflow.triggers else "push",
                repository_path=f"{env.repositories_path}/{workflow.repository_name}",
            )
        )
        print(
            "Functional test succeeded"
            if functional_result.success
            else "Functional test failed"
        )
    except Exception as e:
        print(f"Error during functional test: {e}")
        functional_result = FunctionalTestResult(
            success=False,
            dryrun_success=False,
            execution_success=False,
            output="",
            errors=traceback.format_exc(),
            skipped_jobs=[],
        )

    return functional_result


if __name__ == "__main__":
    workflows = Workflow.load("invalids")
    workflows = workflows[:1]
    scores = []
    for workflow in workflows:
        results = pool_task(workflow)
        scores.append(results)

    for filename in os.listdir(env.tmp_path):
        os.remove(os.path.join(env.tmp_path, filename))
