import logging
from datetime import datetime

import env
from utils.app_types import GraphState

logging.basicConfig()
logger = logging.getLogger("flow")
logger.setLevel(logging.INFO)

state_logger = logging.getLogger("state")

state_handler = None

file_name = f"{env.log_path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_state.log"
state_logger.setLevel(logging.INFO)


def init_state_logger(id: int) -> None:
    global state_handler
    file_name = (
        f"{env.log_path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id}_state.log"
    )
    if state_handler:
        state_logger.removeHandler(state_handler)
    state_handler = logging.FileHandler(file_name)
    state_logger.addHandler(state_handler)


def log_progress(message: str, level: int = logging.INFO) -> None:
    logger.log(level, message)


def log_state(
    step: str, state: GraphState, message: str, level: int = logging.INFO
) -> None:
    state_logger.log(
        level,
        {"step": step, "state": state.to_dict(), "message": message},
    )
