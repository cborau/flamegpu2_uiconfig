from dataclasses import dataclass, field
from typing import List, Optional

VAR_TYPE_OPTIONS = ["UInt8", "Int", "Float", "ArrayUInt", "ArrayFloat"]
DEFAULT_VAR_TYPE = "Float"
SHAPE_VAR_TYPE = "Shape"
GLOBAL_VAR_TYPE_OPTIONS = VAR_TYPE_OPTIONS + [SHAPE_VAR_TYPE]

AGENT_LOGGING_OPTIONS = ["NoLog", "Mean", "Min", "Max", "Sum", "Std"]
DEFAULT_LOGGING_OPTION = AGENT_LOGGING_OPTIONS[0]

VISUALIZATION_SHAPES = ["ICOSPHERE", "CUBE", "PYRAMID", "ARROWHEAD"]
DEFAULT_VISUALIZATION_SHAPE = VISUALIZATION_SHAPES[0]

VISUALIZATION_COLOR_MODES = ["Solid", "Interpolated"]
DEFAULT_VISUALIZATION_COLOR = VISUALIZATION_COLOR_MODES[0]

@dataclass
class AgentVariable:
    name: str
    default: str
    var_type: str = DEFAULT_VAR_TYPE
    logging: str = DEFAULT_LOGGING_OPTION

@dataclass
class AgentFunction:
    name: str
    description: str
    input_type: str
    output_type: str

@dataclass
class AgentType:
    name: str
    color: str
    variables: List[AgentVariable] = field(default_factory=list)
    functions: List[AgentFunction] = field(default_factory=list)

@dataclass
class Layer:
    name: str
    function_ids: List[str] = field(default_factory=list)
    height: Optional[float] = None

@dataclass
class GlobalVariable:
    name: str
    value: str
    var_type: str = DEFAULT_VAR_TYPE
    is_macro: bool = False


@dataclass
class VisualizationInterpolation:
    variable: str = ""
    min_value: float = 0.0
    max_value: float = 1.0


@dataclass
class VisualizationAgentConfig:
    agent_name: str
    include: bool = False
    shape: str = DEFAULT_VISUALIZATION_SHAPE
    color_mode: str = DEFAULT_VISUALIZATION_COLOR
    interpolation: VisualizationInterpolation | None = None


@dataclass
class VisualizationSettings:
    activated: bool = False
    domain_width: str = ""
    begin_paused: bool = False
    show_domain_boundaries: bool = False
    agents: List[VisualizationAgentConfig] = field(default_factory=list)
