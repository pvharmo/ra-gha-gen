from dataclasses import asdict, dataclass
from typing import Literal, NewType, NotRequired, TypedDict

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.graph.message import AnyMessage

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
    system_prompt: str
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
    messages: list[AnyMessage]
    workflow: WorkflowYAML | None
    static_check: SyntaxValidation | None
    vulnerabilities: list[Vulnerability] | None
    judge_score: float | None
    prompt: str
    retries_left: int

    def to_dict(self) -> dict:
        return {
            "messages": [m.dict() for m in self.messages],
            "workflow": self.workflow,
            "static_check": self.static_check,
            "vulnerabilities": self.vulnerabilities,
            "judge_score": self.judge_score,
            "prompt": self.prompt,
            "retries_left": self.retries_left,
        }
