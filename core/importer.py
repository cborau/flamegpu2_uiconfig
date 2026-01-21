from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable

from core.models import (
    AgentType,
    AgentVariable,
    AgentFunction,
    Layer,
    GlobalVariable,
    VisualizationSettings,
    DEFAULT_VAR_TYPE,
    SHAPE_VAR_TYPE,
    DEFAULT_LOGGING_OPTION,
)

_MESSAGE_TYPE_BY_CONSTRUCTOR = {
    "newMessageSpatial3D": "MessageSpatial3D",
    "newMessageArray3D": "MessageArray3D",
    "newMessageBucket": "MessageBucket",
}

_VAR_TYPE_BY_VAR_METHOD = {
    "newVariableFloat": "Float",
    "newVariableInt": "Int",
    "newVariableUInt8": "UInt8",
    "newVariableUInt16": "UInt16",
    "newVariableUInt32": "UInt32",
    "newVariableArrayFloat": "ArrayFloat",
    "newVariableArrayInt": "ArrayInt",
    "newVariableArrayUInt": "ArrayUInt",
}

_GLOBAL_TYPE_BY_ENV_METHOD = {
    "newPropertyFloat": "Float",
    "newPropertyInt": "Int",
    "newPropertyUInt": "UInt32",
    "newPropertyArrayFloat": "ArrayFloat",
    "newPropertyArrayInt": "ArrayInt",
    "newPropertyArrayUInt": "ArrayUInt",
}

_LOGGING_MODE_BY_METHOD = {
    "logMean": "Mean",
    "logMin": "Min",
    "logMax": "Max",
    "logSum": "Sum",
    "logStandardDev": "Std",
}

_DEFAULT_AGENT_COLORS = [
    "#e6194B", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
]


class _ProjectAnalyzer(ast.NodeVisitor):
    def __init__(self, source: str) -> None:
        self.source = source
        self.assignments: dict[str, str] = {}
        self.assignment_nodes: dict[str, ast.AST] = {}
        self.assignment_order: list[str] = []
        self.agent_vars: dict[str, str] = {}
        self.agents: dict[str, AgentType] = {}
        self.agent_variables: dict[str, list[AgentVariable]] = {}
        self.agent_functions: dict[str, dict[str, AgentFunction]] = {}
        self.message_vars: dict[str, str] = {}
        self.message_outputs: dict[str, list[tuple[str, str]]] = {}
        self.function_inputs: dict[tuple[str, str], str] = {}
        self.function_outputs: dict[tuple[str, str], str] = {}
        self.layer_vars: dict[str, str] = {}
        self.layers: dict[str, list[str]] = {}
        self.env_properties: dict[str, GlobalVariable] = {}
        self.env_property_order: list[str] = []
        self.log_var_agents: dict[str, str] = {}
        self.logging_map: dict[str, dict[str, str]] = {}
        self.function_vars: dict[str, tuple[str, str]] = {}

    def visit_Assign(self, node: ast.Assign) -> Any:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            self.assignments[target_name] = self._source_for(node.value)
            self.assignment_nodes[target_name] = node.value
            if target_name not in self.assignment_order:
                self.assignment_order.append(target_name)

        if isinstance(node.value, ast.Call) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
            call_attr = self._call_attr(node.value)

            if call_attr == "newAgent":
                agent_name = self._string_arg(node.value, 0)
                if agent_name:
                    self.agent_vars[target] = agent_name
                    self._ensure_agent(agent_name)

            if call_attr == "newRTCFunctionFile":
                agent_name = self._agent_name_from_value(self._call_value(node.value))
                func_name = self._string_arg(node.value, 0)
                if agent_name and func_name:
                    self.function_vars[target] = (agent_name, func_name)
                    self._ensure_function(agent_name, func_name)

            if call_attr in _MESSAGE_TYPE_BY_CONSTRUCTOR:
                msg_name = self._string_arg(node.value, 0)
                if msg_name:
                    self.message_vars[msg_name] = _MESSAGE_TYPE_BY_CONSTRUCTOR[call_attr]
                self.message_vars[target] = _MESSAGE_TYPE_BY_CONSTRUCTOR[call_attr]

            if call_attr == "agent" and self._is_name(self._call_value(node.value), "logging_config"):
                agent_name = self._string_arg(node.value, 0)
                if agent_name:
                    self.log_var_agents[target] = agent_name

            if call_attr in {"newLayer", "Layer"}:
                layer_name = self._string_arg(node.value, 0)
                if layer_name:
                    self.layer_vars[target] = layer_name
                    self.layers.setdefault(layer_name, [])

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        return None

    def visit_Call(self, node: ast.Call) -> Any:
        attr = self._call_attr(node)
        value = self._call_value(node)

        if attr in _GLOBAL_TYPE_BY_ENV_METHOD and self._is_name(value, "env"):
            name = self._string_arg(node, 0)
            if name:
                var_type = _GLOBAL_TYPE_BY_ENV_METHOD[attr]
                value_expr = self._resolve_value(node, 1)
                self._set_global(name, value_expr, var_type, is_macro=False)

        if attr and attr.startswith("newMacroProperty") and self._is_name(value, "env"):
            name = self._string_arg(node, 0)
            if name:
                dims = [self._resolve_value(node, idx) for idx in range(1, len(node.args))]
                value_expr = ", ".join(dim for dim in dims if dim) if dims else ""
                var_type = SHAPE_VAR_TYPE if len(node.args) > 2 else "Float"
                self._set_global(name, value_expr, var_type, is_macro=True)

        if attr in _VAR_TYPE_BY_VAR_METHOD:
            agent_name = self._agent_name_from_value(value)
            if agent_name:
                var_name = self._string_arg(node, 0)
                if var_name:
                    default_expr = self._resolve_value(node, 1)
                    var_type = _VAR_TYPE_BY_VAR_METHOD[attr]
                    self._add_agent_variable(agent_name, var_name, default_expr, var_type)

        if attr == "newRTCFunctionFile":
            agent_name = self._agent_name_from_value(value)
            func_name = self._string_arg(node, 0)
            if agent_name and func_name:
                self._ensure_function(agent_name, func_name)

        if attr in {"setMessageOutput", "setMessageInput"}:
            func_call = value if isinstance(value, ast.Call) else None
            if func_call and self._call_attr(func_call) == "newRTCFunctionFile":
                agent_name = self._agent_name_from_value(self._call_value(func_call))
                func_name = self._string_arg(func_call, 0)
            elif isinstance(value, ast.Name) and value.id in self.function_vars:
                agent_name, func_name = self.function_vars[value.id]
            else:
                agent_name, func_name = None, None

            message_name = (self._string_arg(node, 0) or "").strip()
            if agent_name and func_name and message_name:
                self._ensure_function(agent_name, func_name)
                msg_type = self._message_type_for(message_name)
                if attr == "setMessageOutput":
                    self._set_function_output(agent_name, func_name, message_name, msg_type)
                else:
                    self._set_function_input(agent_name, func_name, message_name, msg_type)

        if attr == "addAgentFunction":
            agent_name = self._string_arg(node, 0)
            func_name = self._string_arg(node, 1)
            if agent_name and func_name:
                layer_name = None
                if isinstance(value, ast.Call):
                    inner_attr = self._call_attr(value)
                    if inner_attr in {"newLayer", "Layer"}:
                        layer_name = self._string_arg(value, 0)
                elif isinstance(value, ast.Name):
                    layer_name = self.layer_vars.get(value.id)

                if layer_name:
                    self.layers.setdefault(layer_name, []).append(f"{agent_name}::{func_name}")

        if attr in _LOGGING_MODE_BY_METHOD:
            log_var = value.id if isinstance(value, ast.Name) else None
            agent_name = self.log_var_agents.get(log_var) if log_var else None
            var_name = self._string_arg(node, 0)
            if agent_name and var_name:
                self.logging_map.setdefault(agent_name, {})[var_name] = _LOGGING_MODE_BY_METHOD[attr]

        self.generic_visit(node)

    def _ensure_agent(self, agent_name: str) -> None:
        if agent_name not in self.agents:
            color = _DEFAULT_AGENT_COLORS[len(self.agents) % len(_DEFAULT_AGENT_COLORS)]
            self.agents[agent_name] = AgentType(agent_name, color)
            self.agent_variables[agent_name] = []
            self.agent_functions[agent_name] = {}

    def _ensure_function(self, agent_name: str, func_name: str) -> None:
        self._ensure_agent(agent_name)
        self.agent_functions[agent_name].setdefault(
            func_name,
            AgentFunction(func_name, "", "MessageNone", "MessageNone"),
        )

    def _set_function_output(self, agent_name: str, func_name: str, message_name: str, msg_type: str) -> None:
        self.function_outputs[(agent_name, func_name)] = message_name
        func = self.agent_functions[agent_name][func_name]
        func.output_type = msg_type
        self.message_outputs.setdefault(message_name, []).append((agent_name, func_name))

    def _set_function_input(self, agent_name: str, func_name: str, message_name: str, msg_type: str) -> None:
        self.function_inputs[(agent_name, func_name)] = message_name
        func = self.agent_functions[agent_name][func_name]
        func.input_type = msg_type

    def _add_agent_variable(self, agent_name: str, var_name: str, default_expr: str, var_type: str) -> None:
        self._ensure_agent(agent_name)
        if var_type in {"ArrayFloat", "ArrayInt", "ArrayUInt"}:
            default_expr = ""
        logging_value = self.logging_map.get(agent_name, {}).get(var_name, DEFAULT_LOGGING_OPTION)
        self.agent_variables[agent_name].append(
            AgentVariable(var_name, default_expr, var_type, logging_value)
        )

    def _set_global(self, name: str, value_expr: str, var_type: str, is_macro: bool) -> None:
        if not name:
            return
        if var_type in {"ArrayFloat", "ArrayInt", "ArrayUInt"}:
            value_expr = self._strip_brackets(value_expr)
        if var_type == SHAPE_VAR_TYPE:
            value_expr = self._strip_brackets(value_expr)
        self.env_properties[name] = GlobalVariable(name, value_expr, var_type, is_macro=is_macro)
        if name not in self.env_property_order:
            self.env_property_order.append(name)

    def _message_type_for(self, message_name: str) -> str:
        if message_name in self.message_vars:
            return self.message_vars[message_name]
        lowered = message_name.lower()
        if "spatial" in lowered:
            return "MessageSpatial3D"
        if "grid" in lowered or "array" in lowered:
            return "MessageArray3D"
        if "bucket" in lowered:
            return "MessageBucket"
        return "MessageNone"

    def _agent_name_from_value(self, node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Name):
            return self.agent_vars.get(node.id)
        return None

    def _is_name(self, node: ast.AST | None, name: str) -> bool:
        return isinstance(node, ast.Name) and node.id == name

    def _call_attr(self, node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _call_value(self, node: ast.AST | None) -> ast.AST | None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return node.func.value
        return None

    def _string_arg(self, node: ast.Call, index: int) -> str | None:
        if len(node.args) <= index:
            return None
        arg = node.args[index]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None

    def _resolve_value(self, node: ast.Call, index: int) -> str:
        if len(node.args) <= index:
            return ""
        arg = node.args[index]
        if isinstance(arg, ast.Name) and arg.id in self.assignments:
            return self.assignments[arg.id]
        return self._source_for(arg)

    def _source_for(self, node: ast.AST) -> str:
        segment = ast.get_source_segment(self.source, node)
        if segment:
            return segment.strip()
        try:
            return ast.unparse(node).strip()
        except Exception:
            return ""

    def _strip_brackets(self, value: str) -> str:
        if not value:
            return value
        trimmed = value.strip()
        if trimmed.startswith("[") and trimmed.endswith("]"):
            return trimmed[1:-1].strip()
        return trimmed

    def _infer_global_type(self, node: ast.AST | None, raw_value: str) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "Int"
            if isinstance(node.value, int):
                return "Int"
            if isinstance(node.value, float):
                return "Float"
        if isinstance(node, (ast.List, ast.Tuple)):
            numeric_types = []
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, (int, float)):
                    numeric_types.append(float if isinstance(elt.value, float) else int)
                else:
                    numeric_types.append(None)
            if numeric_types and all(t is not None for t in numeric_types):
                return "ArrayFloat" if any(t is float for t in numeric_types) else "ArrayInt"
            return "ArrayFloat"
        if raw_value:
            try:
                parsed = ast.literal_eval(raw_value)
            except Exception:
                return DEFAULT_VAR_TYPE
            if isinstance(parsed, bool):
                return "Int"
            if isinstance(parsed, int):
                return "Int"
            if isinstance(parsed, float):
                return "Float"
            if isinstance(parsed, (list, tuple)):
                if all(isinstance(x, int) for x in parsed):
                    return "ArrayInt"
                if all(isinstance(x, (int, float)) for x in parsed):
                    return "ArrayFloat"
                return "ArrayFloat"
        return DEFAULT_VAR_TYPE

    def build(self) -> tuple[list[AgentType], list[Layer], list[GlobalVariable], list[dict]]:
        for agent_name, variables in self.agent_variables.items():
            log_map = self.logging_map.get(agent_name, {})
            for var in variables:
                if var.name in log_map:
                    var.logging = log_map[var.name]
            self.agents[agent_name].variables = variables
        for agent_name, funcs in self.agent_functions.items():
            self.agents[agent_name].functions = list(funcs.values())

        connections: list[dict] = []
        for (agent_name, func_name), message_name in self.function_inputs.items():
            msg_type = self.agent_functions[agent_name][func_name].input_type
            sources = self.message_outputs.get(message_name, [])
            if not sources:
                continue
            src_agent, src_func = sources[0]
            connections.append({
                "src": f"{src_agent}::{src_func}",
                "dst": f"{agent_name}::{func_name}",
                "type": msg_type,
            })

        layers = [Layer(name, functions) for name, functions in self.layers.items()]

        globals_: list[GlobalVariable] = []
        seen_globals: set[str] = set()
        for name in self.assignment_order:
            if not name or not name[:1].isupper():
                continue
            raw_value = self.assignments.get(name, "")
            node = self.assignment_nodes.get(name)
            inferred_type = self._infer_global_type(node, raw_value)
            value_expr = raw_value
            if inferred_type in {"ArrayFloat", "ArrayInt", "ArrayUInt", SHAPE_VAR_TYPE}:
                value_expr = self._strip_brackets(value_expr)

            glob = self.env_properties.get(name)
            if glob:
                glob.value = glob.value or value_expr
                glob.var_type = glob.var_type or inferred_type
                globals_.append(glob)
            else:
                globals_.append(GlobalVariable(name, value_expr, inferred_type, is_macro=False))
            seen_globals.add(name)

        for name in self.env_property_order:
            if not name or not name[:1].isupper():
                continue
            if name in seen_globals:
                continue
            globals_.append(self.env_properties[name])

        agents = list(self.agents.values())
        return agents, layers, globals_, connections


def import_project_file(file_path: Path) -> tuple[
    list[AgentType],
    list[Layer],
    list[GlobalVariable],
    list[dict],
    dict,
    VisualizationSettings | None,
]:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    analyzer = _ProjectAnalyzer(source)
    analyzer.visit(tree)
    agents, layers, globals_, connections = analyzer.build()
    return agents, layers, globals_, connections, {}, None
