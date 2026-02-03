import re
import subprocess

import yaml

from utils.app_types import WorkflowYAML

yaml_pattern = re.compile(r"```yaml\n([\s\S]*?)\n```")


def extract_yaml(text: str) -> WorkflowYAML | None:
    matches = re.search(yaml_pattern, text)
    if matches:
        return WorkflowYAML(matches.group(1))
    else:
        return None


def remove_empty_lines(yaml_content: WorkflowYAML) -> WorkflowYAML:
    lines = yaml_content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    return WorkflowYAML("\n".join(non_empty_lines))


def remove_comments(yaml_content: WorkflowYAML) -> WorkflowYAML:
    output = subprocess.run(
        ["yq", '... comments=""'],
        input=yaml_content,
        text=True,
        capture_output=True,
        check=True,
    )
    return WorkflowYAML(output.stdout)


def default_format(yaml_content: WorkflowYAML) -> WorkflowYAML:
    output = subprocess.run(
        ["yq", "-I2", '.. style="double"'],
        input=remove_comments(yaml_content),
        text=True,
        capture_output=True,
        check=True,
    )
    return WorkflowYAML(output.stdout.replace(': ""', ":"))


def flow_format(yaml_content: WorkflowYAML) -> WorkflowYAML:
    output = subprocess.run(
        ["yq", "-I2", '.. style="flow"'],
        input=remove_comments(yaml_content),
        text=True,
        capture_output=True,
        check=True,
    )
    return WorkflowYAML(output.stdout)


def json_format(yaml_content: WorkflowYAML) -> WorkflowYAML:
    output = subprocess.run(
        ["yq", "-I2", "...=@json"],
        input=remove_comments(yaml_content),
        text=True,
        capture_output=True,
        check=True,
    )
    return WorkflowYAML(output.stdout)


def pyyaml_format(yaml_content: WorkflowYAML) -> WorkflowYAML:
    return WorkflowYAML(
        yaml.dump(
            yaml.safe_load(remove_comments(yaml_content)), sort_keys=False
        ).replace("\ntrue:", "\non: ")
    )
