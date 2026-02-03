# from langgraph.graph import MessagesState
import json
import logging

from utils.app_types import GraphState
from utils.formatting import extract_yaml
from utils.lint import (
    check_vulnerabilities,
    validate_workflow,
)
from utils.logger import log_progress, log_state
from utils.scores import extract_judge_score


def extract_judge_score_function(state: GraphState) -> GraphState:
    log_progress("Extracting judge score")
    state.judge_score = extract_judge_score(str(state.messages[-1].content))  # pyright: ignore
    log_state("extract_judge_score", state, state.judge_score)
    log_progress(f"Judge score extracted: {state.judge_score}")
    return state


def extract_workflow_function(state: GraphState) -> GraphState:
    log_progress("Extracting workflow")
    workflow = extract_yaml(str(state.messages[-1].content))  # pyright: ignore
    state.workflow = workflow
    log_state("extract_workflow", state, str(state.workflow))
    log_progress("Workflow extracted")
    return state


def static_checker_function(state: GraphState) -> GraphState:
    log_progress("Running static checker")
    state.static_check = validate_workflow(state.workflow)
    log_state("static_checker", state, json.dumps(state.static_check))
    log_progress(f"Found {len(state.static_check['output'])} static check issues")
    log_progress("Static checker completed")
    return state


def vulnerability_scanner_function(state: GraphState) -> GraphState:
    log_progress("Running vulnerability scanner")
    log_progress(f"workflow: {state.workflow}", logging.DEBUG)
    state.vulnerabilities = check_vulnerabilities(state.workflow)
    log_state("vulnerability_scanner", state, json.dumps(state.vulnerabilities))
    log_progress(f"Found {len(state.vulnerabilities)} vulnerabilities")
    log_progress("Vulnerability scanner completed")
    return state


def retry_increment(state: GraphState) -> GraphState:
    state.retries_left -= 1
    log_state("retry_increment", state, str(state.retries_left))
    log_progress(f"Retries left: {state.retries_left}", logging.DEBUG)
    return state


functions = {
    "extract_judge_score": extract_judge_score_function,
    "vulnerability_scanner": vulnerability_scanner_function,
    "extract_workflow": extract_workflow_function,
    "static_checker": static_checker_function,
    "retry_increment": retry_increment,
}
