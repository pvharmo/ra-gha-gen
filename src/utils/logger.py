import json
import logging
from datetime import datetime
from typing import Any

import env
from models.score import Score
from utils.app_types import GraphState, SyntaxValidation, Vulnerability

logging.basicConfig()
logger = logging.getLogger("flow")
logger.setLevel(logging.INFO)

state_file_name = f"{env.log_path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_state.log"
messages_file_name = (
    f"{env.log_path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_state.log"
)


def init_state_logger(id: int, log_to_term: bool = True) -> None:
    logging.getLogger("flow").disabled = not log_to_term
    global state_file_name
    state_file_name = (
        f"{env.log_path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id}_state.log"
    )
    global messages_file_name
    messages_file_name = (
        f"{env.log_path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id}_messages.log"
    )


def log_progress(message: str, level: int = logging.INFO) -> None:
    logger.log(level, message)


def log_message(message: str | dict[str, Any], level: int = logging.INFO) -> None:
    with open(messages_file_name, "a") as f:
        json.dump(
            {
                "log_type": "message",
                "timestamp": datetime.now().isoformat(),
                "level": logging.getLevelName(level),
                "message": message,
            },
            f,
        )
        f.write("\n")


def log_state(
    step: str,
    state: GraphState,
    message: str | list[Vulnerability] | SyntaxValidation,
    level: int = logging.INFO,
) -> None:
    with open(state_file_name, "a") as f:
        json.dump(
            {
                "log_type": "storyline",
                "timestamp": datetime.now().isoformat(),
                "level": logging.getLevelName(level),
                "step": step,
                "state": state.to_dict(),
                "message": message,
            },
            f,
        )
        f.write("\n")


def log_score(score: Score):
    with open(state_file_name, "a") as f:
        json.dump({"log_type": "score", **score.to_dict()}, f)
        f.write("\n")


def log_graph(graph):
    with open(state_file_name, "a") as f:
        json.dump({"log_type": "graph", **graph}, f)
        f.write("\n")
