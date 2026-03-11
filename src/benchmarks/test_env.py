# import multiprocessing
import os
import shutil
import subprocess

import env
from models.workflow import Workflow


def setup(workflow: Workflow):
    destination_path = f"{env.repositories_path}/{workflow.repository_name}"
    if not os.path.exists(f"{env.repositories_path}/{workflow.repository_name}"):
        print(
            f"Cloning repository {workflow.repository_owner}/{workflow.repository_name}..."
        )

        subprocess.run(
            [
                "git",
                "clone",
                f"https://github.com/llm-gha-bench/{workflow.repository_name}.git",
                destination_path,
            ]
        )

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            capture_output=True,
            cwd=destination_path,
        ).stdout.strip()

        commit_sha = subprocess.run(
            ["git", "rev-list", "-n", "1", "--before=2025-05-01", branch],
            text=True,
            capture_output=True,
            cwd=destination_path,
        ).stdout.strip()

        subprocess.run(
            [
                "git",
                "reset",
                "--hard",
                commit_sha,
            ],
            cwd=destination_path,
            capture_output=True,
        )
        os.mkdir(f"{env.repositories_path}/workflows/{workflow.repository_name}")
        print(
            f"Repository {workflow.repository_owner}/{workflow.repository_name} cloned successfully. Using commit sha {commit_sha} on branch {branch}."
        )

    if not os.path.exists(
        f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}"
    ):
        shutil.move(
            f"{env.repositories_path}/{workflow.repository_name}/.github/workflows/{workflow.file_name}",
            f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}",
        )


def teardown(workflow: Workflow):
    shutil.move(
        f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}",
        f"{env.repositories_path}/{workflow.repository_name}/.github/workflows/{workflow.file_name}",
    )
