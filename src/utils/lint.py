import json
import re
import subprocess
import uuid

import env
from utils.app_types import (
    SyntaxValidation,
    SyntaxValidationOutput,
    Vulnerability,
    WorkflowYAML,
)


def detect_invalid_format(response: WorkflowYAML):
    if len(response) > 20000:
        return True
    pattern = r"(.*)```"
    matches = re.match(pattern, response.strip(), re.DOTALL)
    if matches and (matches.group(1)):
        return False
    else:
        return True


def format_actionlint_output(output: list[SyntaxValidationOutput]):
    errors = ""
    for value in output:
        severity = "error" if value["kind"] == "syntax-check" else "warning"
        filepath = "test.yml"
        line = value["line"] if "line" in value else 0
        col = value["column"] if "column" in value else 0
        message = value["message"]
        snippet = value["snippet"] if "snippet" in value else ""
        errors += f"{severity}: {filepath}:{line}:{col} - {message}\n```{snippet}```\n"
    return errors


def validate_workflow_formatted(workflow: WorkflowYAML | None) -> str:
    result = validate_workflow(workflow)
    return format_actionlint_output(result["output"])


def validate_workflow(workflow: str | None) -> SyntaxValidation:
    if workflow is None:
        return {
            "valid": False,
            "output": [{"message": "Workflow is empty", "kind": "empty"}],
        }
    unique_id = str(uuid.uuid4())
    with open(f"{env.tmp_path}/{unique_id}.yml", "w+") as file:
        file.write(workflow.replace("\ntrue", "\non"))

    output = subprocess.run(
        [
            "actionlint",
            "-ignore",
            "action is too old",
            "-format",
            "{{json .}}",
            f"{env.tmp_path}/{unique_id}.yml",
        ],
        text=True,
        capture_output=True,
    ).stdout

    json_output = json.loads(output)

    return {"valid": len(json_output) == 0, "output": json_output}


def check_vulnerabilities_with_format(
    workflow: str | None, format: str
) -> list[Vulnerability] | str:
    if workflow is None:
        return [] if format == "json" else "Workflow is empty"
    unique_id = str(uuid.uuid4())
    with open(f"{env.root}/tmp/{unique_id}.yml", "w+") as file:
        file.write(workflow)

    output = subprocess.run(
        ["zizmor", f"--format={format}", f"{env.root}/tmp/{unique_id}.yml"],
        text=True,
        capture_output=True,
    ).stdout

    if format == "github":
        return output

    if output.strip() == "":
        return json.loads("{}")

    json_output = json.loads(output)

    return json_output


def check_vulnerabilities(workflow: str | None) -> list[Vulnerability]:
    return check_vulnerabilities_with_format(workflow, "json")  # type: ignore[invalid-return-type]


def check_vulnerabilities_formatted(workflow: str | None) -> str:
    return check_vulnerabilities_with_format(workflow, "github")  # type: ignore[invalid-return-type]
