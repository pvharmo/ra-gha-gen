from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FunctionalTestResult:
    success: bool
    dryrun_success: bool
    execution_success: bool
    output: str
    errors: str
    skipped_jobs: list[str] = field(default_factory=list)
    jobs_executed: list[str] = field(default_factory=list)
    jobs_failed: list[str] = field(default_factory=list)


@dataclass
class MockEvent:
    event_type: str
    ref: str = "refs/heads/main"
    repository: str = "test/repo"
    sha: str = "abc123def456"
    actor: str = "testuser"
    extra_payload: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        base_payload = {
            "event": self.event_type,
            "ref": self.ref,
            "repository": {
                "full_name": self.repository,
                "name": self.repository.split("/")[1],
                "owner": {"login": self.repository.split("/")[0]},
            },
            "sha": self.sha,
            "actor": self.actor,
            "head_commit": {"id": self.sha, "message": "Test commit"},
            "github": {
                "event_name": self.event_type,
                "event": {},
                "repository": self.repository,
                "ref": self.ref,
                "sha": self.sha,
                "actor": self.actor,
                "workflow": "test-workflow",
                "run_id": "12345",
                "run_number": "1",
            },
        }
        base_payload.update(self.extra_payload)
        return base_payload


DEFAULT_MOCK_SECRETS = {
    # "GITHUB_TOKEN": "mock_token_12345",
    "DEPLOY_KEY": "mock_deploy_key",
    "NPM_TOKEN": "mock_npm_token",
    # "DOCKER_USERNAME": "mock_user",
    # "DOCKER_PASSWORD": "mock_password",
}


def create_minimal_repo_structure(tmpdir: Path) -> None:
    (tmpdir / ".git").mkdir(exist_ok=True)
    (tmpdir / ".git" / "config").write_text("[core]\n\trepositoryformatversion = 0\n")

    readme = tmpdir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Test Repository\n\nThis is a mock repository for testing GitHub Actions workflows.\n"
        )


class WorkflowTestRunner:
    def __init__(
        self,
        mock_secrets: dict[str, str] | None = None,
        timeout: int = 300,
        act_path: str = "act",
    ):
        self.mock_secrets = {**DEFAULT_MOCK_SECRETS, **(mock_secrets or {})}
        self.timeout = timeout
        self.act_path = act_path
        self._act_available: bool | None = None

    def _build_act_command(
        self,
        workflow_path: Path,
        event_path: Path,
        dryrun: bool = True,
        workflow_name: str | None = None,
    ) -> list[str]:
        cmd = [self.act_path]

        if dryrun:
            cmd.append("--dryrun")

        cmd.extend(
            [
                "-e",
                str(event_path),
                "-W",
                str(workflow_path),
                "--container-architecture",
                "linux/amd64",
                "--artifact-server-path",
                str(tempfile.mkdtemp("act_artifacts_")),
            ]
        )

        if workflow_name:
            cmd.extend(["-j", workflow_name])

        for secret_name, secret_value in self.mock_secrets.items():
            cmd.extend(["-s", f"{secret_name}={secret_value}"])

        return cmd

    def run_test(
        self,
        workflow_yaml: str,
        event_type: str = "push",
        repository_path: str | None = None,
    ) -> FunctionalTestResult:

        skipped_jobs = []

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            if repository_path:
                repo_path = Path(repository_path)
                for item in repo_path.iterdir():
                    # if item.name != ".git":
                    dest = tmpdir_path / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)

            workflow_dir = tmpdir_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)

            workflow_file = workflow_dir / "test_workflow.yml"
            workflow_file.write_text(workflow_yaml)

            create_minimal_repo_structure(tmpdir_path)

            mock_event = MockEvent(event_type=event_type)
            event_file = tmpdir_path / "event.json"
            event_file.write_text(json.dumps(mock_event.to_payload()))

            dryrun_cmd = self._build_act_command(workflow_file, event_file, dryrun=True)
            dryrun_result = subprocess.run(
                dryrun_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tmpdir_path,
            )

            dryrun_success = dryrun_result.returncode == 0

            if not dryrun_success:
                return FunctionalTestResult(
                    success=False,
                    dryrun_success=False,
                    execution_success=False,
                    output=dryrun_result.stdout,
                    errors=dryrun_result.stderr,
                    skipped_jobs=skipped_jobs,
                )

            exec_cmd = self._build_act_command(workflow_file, event_file, dryrun=False)

            try:
                exec_result = subprocess.run(
                    exec_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmpdir_path,
                )
                execution_success = exec_result.returncode == 0
                combined_output = dryrun_result.stdout + "\n" + exec_result.stdout
                combined_errors = dryrun_result.stderr + "\n" + exec_result.stderr

                jobs_executed, jobs_failed = self._parse_job_results(
                    exec_result.stdout + exec_result.stderr
                )

            except subprocess.TimeoutExpired:
                execution_success = False
                combined_output = dryrun_result.stdout
                combined_errors = f"Execution timed out after {self.timeout} seconds"
                jobs_executed = []
                jobs_failed = []

            return FunctionalTestResult(
                success=dryrun_success and execution_success,
                dryrun_success=dryrun_success,
                execution_success=execution_success,
                output=combined_output,
                errors=combined_errors,
                skipped_jobs=skipped_jobs,
                jobs_executed=jobs_executed,
                jobs_failed=jobs_failed,
            )

    def _parse_job_results(self, output: str) -> tuple[list[str], list[str]]:
        executed = []
        failed = []

        success_pattern = r"\[.*?\]\s*(?:✓|SUCCESS)\s+(\S+)"
        fail_pattern = r"\[.*?\]\s*(?:✗|FAIL|ERROR)\s+(\S+)"

        for match in re.finditer(success_pattern, output):
            executed.append(match.group(1))

        for match in re.finditer(fail_pattern, output):
            failed.append(match.group(1))

        if not executed and not failed:
            job_pattern = r"\[.*?/(\w+)\]\s+"
            for match in re.finditer(job_pattern, output):
                job_name = match.group(1)
                if job_name not in executed:
                    executed.append(job_name)

        return executed, failed


async def run_functional_test(
    workflow_yaml: str,
    event_type: str = "push",
    repository_path: str | None = None,
    mock_secrets: dict[str, str] | None = None,
) -> FunctionalTestResult:
    runner = WorkflowTestRunner(mock_secrets=mock_secrets)
    return runner.run_test(workflow_yaml, event_type, repository_path)
