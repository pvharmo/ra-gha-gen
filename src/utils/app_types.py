from dataclasses import dataclass
from typing import Literal, NewType, NotRequired, TypedDict

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

WorkflowYAML = NewType("WorkflowYAML", str)


class AgentYAML(TypedDict):
    identifier: str
    system_prompt: str
    tools: list[str]
    prompt_template: str
    model: NotRequired[str]


class Agent(TypedDict):
    identifier: str
    model: ChatOpenAI | Runnable[LanguageModelInput, AIMessage]
    model_name: str
    # system_prompt: str
    prompt_template: str


class SyntaxValidationOutput(TypedDict):
    message: str
    filepath: NotRequired[str]
    line: NotRequired[int]
    column: NotRequired[int]
    kind: str
    snippet: NotRequired[str]
    end_column: NotRequired[int]


class SyntaxValidation(TypedDict):
    valid: bool
    output: list[SyntaxValidationOutput]


class LocalKey(TypedDict):
    prefix: str | None
    given_path: str


class Key(TypedDict):
    Local: LocalKey


class RouteComponent(TypedDict):
    Key: str


class Route(TypedDict):
    components: list[RouteComponent]


class SymbolicLocation(TypedDict):
    key: Key
    annotation: str
    route: Route
    feature_kind: Literal["Normal"]
    kind: Literal["Related", "Primary"]


class Point(TypedDict):
    row: int
    column: int


class OffsetSpan(TypedDict):
    start: int
    end: int


class LocationSpan(TypedDict):
    start_point: Point
    end_point: Point
    offset_span: OffsetSpan


class ConcreteLocation(TypedDict):
    location: LocationSpan
    feature: str
    comments: list[str]


class LocationItem(TypedDict):
    symbolic: SymbolicLocation
    concrete: ConcreteLocation


class Determinations(TypedDict):
    confidence: Literal["Low", "Medium", "High"]
    severity: Literal["Low", "Medium", "High"]
    persona: Literal["Regular", "Admin", "System"]


class Vulnerability(TypedDict):
    ident: str
    desc: str
    url: str
    determinations: Determinations
    locations: list[LocationItem]
    ignored: bool


@dataclass
class GraphState:
    workflow: WorkflowYAML | None
    llm_response: str | None
    static_check: SyntaxValidation | None
    vulnerabilities: list[Vulnerability] | None
    judgement: str | None
    judge_score: float | None
    prompt: str
    syntax_retries_left: int
    if_retries_left: int
    vuln_retries_left: int

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "static_check": self.static_check,
            "vulnerabilities": self.vulnerabilities,
            "judge_score": self.judge_score,
            "prompt": self.prompt,
            "syntax_retries_left": self.syntax_retries_left,
            "if_retries_left": self.if_retries_left,
            "vuln_retries_left": self.vuln_retries_left,
        }
