import os

import requests
from langchain.tools import tool

from utils.app_types import WorkflowYAML

# from langgraph.graph import MessagesState
from utils.formatting import extract_yaml
from utils.lint import (
    check_vulnerabilities_formatted,
    validate_workflow_formatted,
)


@tool
def extract_workflow(workflow: str) -> str | None:
    """Extracts information from the workflow.

    Args:
        workflow: workflow to extract information from
    """
    return extract_yaml(workflow)


@tool
def static_checker(workflow: WorkflowYAML) -> str:
    """Performs static analysis on the workflow.

    Args:
        workflow: workflow to analyse
    """
    return validate_workflow_formatted(workflow)


@tool
def vulnerability_scanner(workflow: WorkflowYAML) -> str | None:
    """Performs vulnerability scanning on the workflow.

    Args:
        workflow: workflow to analyse
    """
    return check_vulnerabilities_formatted(workflow)


@tool
def read_readme() -> str:
    """Reads the README file."""
    try:
        with open("README.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        try:
            with open("README", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "README not found"


@tool
def read_contributing() -> str:
    """Reads the CONTRIBUTING file."""
    try:
        with open("CONTRIBUTING.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        try:
            with open("CONTRIBUTING", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "CONTRIBUTING.md not found"


@tool
def list_files(path: str = ".") -> str:
    """Lists all files in the root of the project."""
    return "\n".join(os.listdir(path))


@tool
def read_file(file_path: str) -> str:
    """Reads the content of the file."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"File {file_path} not found"


@tool
def get_action_details(action_name: str) -> str:
    """Gets the readme file of an action."""
    try:
        if action_name.count("@") == 0:
            owner_repo = action_name
            ref = ["main", "master"]
        else:
            owner_repo, ref = action_name.split("@", 1)
            ref = [ref]
        owner, repo = owner_repo.split("/", 1)
    except ValueError:
        raise ValueError(f"Invalid uses string: {action_name!r}")

    for filename in ("action.yml", "action.yaml"):
        for r in ref:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{r}/{filename}"
            resp = requests.get(url)
            if resp.status_code == 200:
                return resp.text

    return f"Could not find details for {action_name}"


tools = [
    list_files,
    read_file,
    read_readme,
    read_contributing,
    extract_workflow,
    static_checker,
    vulnerability_scanner,
    get_action_details,
]
tools_by_name = {tool.name: tool for tool in tools}
