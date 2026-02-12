import requests
from langchain.tools import tool
from langchain_community.agent_toolkits import FileManagementToolkit

from utils.app_types import WorkflowYAML

# from langgraph.graph import MessagesState
from utils.formatting import extract_yaml
from utils.lint import (
    check_vulnerabilities_formatted,
    validate_workflow_formatted,
)

base_path: str = ""


def set_base_path(path: str):
    global base_path
    if not path.endswith("/"):
        path += "/"
    base_path = path


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
        with open(base_path + "README.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        try:
            with open(base_path + "README", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "README not found"


@tool
def read_contributing() -> str:
    """Reads the CONTRIBUTING file."""
    try:
        with open(base_path + "CONTRIBUTING.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        try:
            with open(base_path + "CONTRIBUTING", "r") as f:
                return f.read()
        except FileNotFoundError:
            return "CONTRIBUTING.md not found"


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


def get_tools(directory: str):
    files_tools = FileManagementToolkit(
        root_dir=str(directory),
        selected_tools=["read_file", "file_search", "list_directory"],
    ).get_tools()
    read_file, file_search, list_dir = files_tools
    tools = [
        read_file,
        file_search,
        list_dir,
        read_readme,
        read_contributing,
        extract_workflow,
        static_checker,
        vulnerability_scanner,
        get_action_details,
    ]
    tools_by_name = {tool.name: tool for tool in tools}

    return tools_by_name
