from dataclasses import dataclass, field
from typing import List, Optional

VAR_TYPE_OPTIONS = ["UInt8", "Int", "Float", "ArrayUInt", "ArrayFloat"]
DEFAULT_VAR_TYPE = "Float"

@dataclass
class AgentVariable:
    name: str
    default: str
    var_type: str = DEFAULT_VAR_TYPE

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
