# from utils.logger import logger
from utils.app_types import GraphState
from utils.logger import log_progress, log_state


def validity_router(state: GraphState):
    chech_fmt = f"vulnerabilities: {len(state.vulnerabilities) if state.vulnerabilities else ''}, static check issues: {len(state.static_check['output']) if state.static_check else ''}, judge score: {state.judge_score}, retries: {state.retries_left}"
    log_progress(chech_fmt)
    log_state("validity_router", state, chech_fmt)
    if (
        state.vulnerabilities is not None
        and len(state.vulnerabilities) == 0
        and state.static_check is not None
        and state.static_check["valid"]
        and state.judge_score is not None
        and state.judge_score == 5
        or state.retries_left <= 0
    ):
        return "valid"
    else:
        return "invalid"


routers = {
    "validity_router": validity_router,
}
