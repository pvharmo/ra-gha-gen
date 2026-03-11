from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils.logger import log_progress


@dataclass
class FunctionalTestResult:
    fully_ran: bool
    dryrun_output: list[dict]
    dryrun_errors: list[dict]
    output: list[dict]
    errors: list[dict]
    return_code: int | None


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


def parse_json(line: str) -> dict:
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return {"raw_line": line.strip()}


def output_to_json(output: str) -> list[dict]:
    try:
        return [parse_json(line) for line in output.strip().split("\n") if line.strip()]
    except json.JSONDecodeError:
        print("#####---JSON parsing error-------------------------------")
        print(output)
        print("-----------------------------------------------------####")
        return [
            json.loads(line.strip())
            for line in output.strip().split("\n")
            if line.strip()
        ]


class WorkflowTestRunner:
    def __init__(
        self,
        mock_secrets: dict[str, str] | None = None,
        timeout: int = 900,
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
                "--platform",
                "ubuntu-latest=catthehacker/ubuntu:full-latest",
                "--platform",
                "ubuntu-22.04=catthehacker/ubuntu:full-22.04",
                "--platform",
                "ubuntu-20.04=catthehacker/ubuntu:full-20.04",
                "--platform",
                "ubuntu-18.04=catthehacker/ubuntu:full-18.04",
                "--json",
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
        log_progress("Generating test environment...")

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

            mock_event = MockEvent(event_type=event_type)
            event_file = tmpdir_path / "event.json"
            event_file.write_text(json.dumps(mock_event.to_payload()))

            log_progress("Running act dry-run to validate workflow...")

            dryrun_cmd = self._build_act_command(workflow_file, event_file, dryrun=True)
            dryrun_result = subprocess.run(
                dryrun_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tmpdir_path,
            )

            dryrun_output = output_to_json(dryrun_result.stdout)

            dryrun_errors = output_to_json(dryrun_result.stderr)

            dryrun_success = dryrun_result.returncode == 0

            if not dryrun_success:
                return FunctionalTestResult(
                    fully_ran=False,
                    dryrun_output=dryrun_output,
                    dryrun_errors=dryrun_errors,
                    output=[],
                    errors=[],
                    return_code=dryrun_result.returncode,
                )

            # exec_cmd = self._build_act_command(workflow_file, event_file, dryrun=False)

            # try:
            #     exec_result = subprocess.run(
            #         exec_cmd,
            #         capture_output=True,
            #         text=True,
            #         timeout=self.timeout,
            #         cwd=tmpdir_path,
            #     )

            #     return FunctionalTestResult(
            #         fully_ran=True,
            #         dryrun_output=dryrun_output,
            #         dryrun_errors=dryrun_errors,
            #         output=output_to_json(exec_result.stdout),
            #         errors=output_to_json(exec_result.stderr),
            #         return_code=exec_result.returncode,
            #     )

            # except subprocess.TimeoutExpired:
            #     return FunctionalTestResult(
            #         fully_ran=False,
            #         dryrun_output=dryrun_output,
            #         dryrun_errors=dryrun_errors,
            #         output=output_to_json(
            #             exec_result.stdout if "exec_result" in locals() else ""
            #         ),
            #         errors=output_to_json(
            #             exec_result.stderr if "exec_result" in locals() else ""
            #         )
            #         + [{"error": f"Execution timed out after {self.timeout} seconds"}],
            #         return_code=None,
            #     )

            return FunctionalTestResult(
                fully_ran=False,
                dryrun_output=dryrun_output,
                dryrun_errors=dryrun_errors,
                output=[],
                errors=[],
                return_code=None,
            )


def run_functional_test(
    workflow_yaml: str,
    event_type: str = "push",
    repository_path: str | None = None,
    mock_secrets: dict[str, str] | None = None,
) -> FunctionalTestResult:
    runner = WorkflowTestRunner(mock_secrets=mock_secrets)
    try:
        return runner.run_test(workflow_yaml, event_type, repository_path)
    except Exception as e:
        return FunctionalTestResult(
            fully_ran=False,
            dryrun_output=[],
            dryrun_errors=[{"error": str(e), "traceback": traceback.format_exc()}],
            output=[],
            errors=[{"error": str(e), "traceback": traceback.format_exc()}],
            return_code=None,
        )
