from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from core.models import (
    AgentType,
    GlobalVariable,
    Layer,
    VisualizationSettings,
    DEFAULT_VISUALIZATION_COLOR,
    DEFAULT_VISUALIZATION_SHAPE,
    VISUALIZATION_COLOR_MODES,
    VISUALIZATION_SHAPES,
    DEFAULT_VAR_TYPE,
    SHAPE_VAR_TYPE,
)

_MESSAGE_TYPE_KEYS: dict[str, str] = {
    "MessageSpatial3D": "spatial",
    "MessageArray3D": "grid",
    "MessageBucket": "bucket",
}

_ENV_PROPERTY_METHODS: dict[str, str] = {
    "Float": "newPropertyFloat",
    "Int": "newPropertyInt",
    "UInt8": "newPropertyUInt",
    "ArrayFloat": "newPropertyArrayFloat",
    "ArrayUInt": "newPropertyArrayUInt",
}

_MACRO_PROPERTY_METHODS: dict[str, str] = {
    "Float": "newMacroPropertyFloat",
    "ArrayFloat": "newMacroPropertyFloat",
    "Int": "newMacroPropertyInt",
    "UInt8": "newMacroPropertyInt",
    "ArrayUInt": "newMacroPropertyInt",
}

_AGENT_VARIABLE_METHODS: dict[str, str] = {
    "Float": "newVariableFloat",
    "Int": "newVariableInt",
    "UInt8": "newVariableUInt8",
    "ArrayFloat": "newVariableArrayFloat",
    "ArrayUInt": "newVariableArrayUInt",
}

_MESSAGE_CONSTRUCTORS: dict[str, str] = {
    "MessageSpatial3D": "newMessageSpatial3D",
    "MessageArray3D": "newMessageArray3D",
    "MessageBucket": "newMessageBucket",
}

_ARRAY_TYPES = {"ArrayFloat", "ArrayUInt"}

_LOGGING_METHODS = {
    "Mean": "logMean",
    "Min": "logMin",
    "Max": "logMax",
    "Sum": "logSum",
    "Std": "logStandardDev",
}

_INTERPOLATED_MODE = "Interpolated"


def export_model_files(
    model_name: str,
    template_path: Path,
    output_dir: Path,
    agents: Sequence[AgentType],
    layers: Sequence[Layer],
    globals_: Sequence[GlobalVariable],
    connections: Sequence[dict],
    visualization: VisualizationSettings | None = None,
    created_at: datetime | None = None,
) -> Path:
    """Render the main template with the provided model data and write it to disk."""
    timestamp = created_at or datetime.now()
    template = template_path.read_text(encoding="utf-8")

    all_globals_block = _render_all_globals(globals_)
    env_globals_block = _render_model_globals(globals_)
    function_files_block = _render_function_files(agents)
    messages_block, spatial_agents = _render_messages(agents)
    agents_block = _render_agents(agents, connections or [])
    layers_block = _render_layers(layers)
    logging_block = _render_logging(agents)
    visualization_block_1, visualization_block_2 = _render_visualisation_blocks(agents, visualization)
    agent_logs_block = _render_agent_logs(agents)

    constants_block = _render_spatial_constants(spatial_agents)

    replacements = {
        "[PLACEHOLDER_MODEL_NAME]": model_name,
        "[PLACEHOLDER_DATE]": timestamp.strftime("%d/%m/%Y - %H:%M:%S"),
        "[PLACEHOLDER_ALL_GLOBALS]": all_globals_block,
        "[PLACEHODER_MODEL_GLOBALS]": env_globals_block,
        "[PLACEHOLDER_FUNCTION_FILES]": function_files_block,
        "[PLACEHOLDER_MESSAGES]": messages_block,
        "[PLACEHOLDER_AGENTS]": agents_block,
        "[PLACEHOLDER_LAYERS]": layers_block,
        "[PLACEHOLDER_LOGGING]": logging_block,
        "[PLACEHOLDER_VISUALIZATION_1]": visualization_block_1,
        "[PLACEHOLDER_VISUALIZATION_2]": visualization_block_2,
        "[PLACEHOLDER_AGENT_LOGS]": agent_logs_block,
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    template = template.replace("[PLACEHOLDER_MAX_SEARCH_RADIUS_AGENT_i_NAME]", constants_block)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{model_name}.py"
    output_path.write_text(template, encoding="utf-8")
    return output_path


def _render_all_globals(globals_: Sequence[GlobalVariable]) -> str:
    if not globals_:
        return "# No global variables defined"

    lines: list[str] = []
    for glob in globals_:
        literal = _format_literal(glob.var_type, glob.value)
        lines.append(f"{glob.name} = {literal}")
    return "\n".join(lines)


def _render_model_globals(globals_: Sequence[GlobalVariable]) -> str:
    if not globals_:
        return "# No model globals configured"

    lines: list[str] = []
    for glob in globals_:
        if getattr(glob, "is_macro", False):
            method = _MACRO_PROPERTY_METHODS.get(glob.var_type, "newMacroPropertyFloat")
        else:
            method = _ENV_PROPERTY_METHODS.get(glob.var_type, _ENV_PROPERTY_METHODS[DEFAULT_VAR_TYPE])
        literal = _format_literal(glob.var_type, glob.value)
        lines.append(f'env.{method}("{glob.name}", {literal})')
    return "\n".join(lines)


def _render_function_files(agents: Sequence[AgentType]) -> str:
    blocks: list[str] = []
    for agent in agents:
        if not agent.functions:
            continue
        block_lines = [
            "\"\"\"",
            f"  {agent.name}",
            "\"\"\"",
        ]
        for func in agent.functions:
            block_lines.append(f'{func.name}_file = "{func.name}.cpp"')
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks) if blocks else "# No agent function files declared"


def _render_messages(agents: Sequence[AgentType]) -> tuple[str, set[str]]:
    blocks: list[str] = []
    spatial_agents: set[str] = set()
    seen: set[tuple[str, str]] = set()
    for agent in agents:
        for func in agent.functions:
            msg_type = func.output_type
            if msg_type == "MessageNone":
                continue
            key = (agent.name, msg_type)
            if key in seen:
                continue
            seen.add(key)
            constructor = _MESSAGE_CONSTRUCTORS.get(msg_type)
            msg_key = _MESSAGE_TYPE_KEYS.get(msg_type)
            if not constructor or not msg_key:
                continue
            var_name = f"{agent.name}_{msg_key}_location_message"
            if msg_type == "MessageBucket":
                block_lines = [
                    f"{agent.name}_MAX_CONNECTIVITY = ? # the maximum expected connectivity of each node",
                    f"{agent.name}_N_NODES = ? # number of nodes in the bucket network",
                    f"{var_name} = model.newMessageBucket(\"{agent.name}_bucket_location_message\")",
                    "# Set the range and bounds.",
                    f"{var_name}.setBounds(0,{agent.name}_N_NODES)",
                ]
            else:
                block_lines = [
                    f'{var_name} = model.{constructor}("{var_name}")'
                ]
            if msg_type == "MessageSpatial3D":
                spatial_agents.add(agent.name)
                block_lines.extend([
                    f"{var_name}.setRadius(MAX_SEARCH_RADIUS_{agent.name})",
                    f"{var_name}.setMin(MIN_EXPECTED_BOUNDARY_POS, MIN_EXPECTED_BOUNDARY_POS, MIN_EXPECTED_BOUNDARY_POS)",
                    f"{var_name}.setMax(MAX_EXPECTED_BOUNDARY_POS, MAX_EXPECTED_BOUNDARY_POS, MAX_EXPECTED_BOUNDARY_POS)",
                ])
            elif msg_type == "MessageArray3D":
                block_lines.extend([
                    f"{agent.name}_AGENTS_PER_DIR = [?, ?, ?]",
                    f"{var_name}.setDimensions({agent.name}_AGENTS_PER_DIR[0], {agent.name}_AGENTS_PER_DIR[1], {agent.name}_AGENTS_PER_DIR[2])",
                ])

            _append_agent_variables_to_message(block_lines, var_name, agent, msg_type)

            if msg_type == "MessageBucket":
                block_lines.append(
                    f'{var_name}.newVariableArrayUInt("linked_nodes", {agent.name}_MAX_CONNECTIVITY)'
                )

            block_lines.append(
                "# TODO: add or remove variables manually to leave only those that need to be reported. If message type is MessageSpatial3D, variables x, y, z are included internally."
            )

            blocks.append("\n".join(block_lines))
    return ("\n\n".join(blocks) if blocks else "# No location messages defined"), spatial_agents


def _append_agent_variables_to_message(
    block_lines: list[str],
    message_var_name: str,
    agent: AgentType,
    msg_type: str,
) -> None:
    handled: set[str] = set()

    def add_variable(name: str, var_type: str, default: str | None) -> None:
        if not name or name in handled:
            return
        method = _AGENT_VARIABLE_METHODS.get(var_type, _AGENT_VARIABLE_METHODS[DEFAULT_VAR_TYPE])
        if var_type in _ARRAY_TYPES:
            caster = float if var_type == "ArrayFloat" else int
            values = _parse_array(default, caster)
            length_literal = str(len(values)) if values else "?"
            block_lines.append(f'{message_var_name}.{method}("{name}", {length_literal})')
        else:
            block_lines.append(f'{message_var_name}.{method}("{name}")')
        handled.add(name)

    add_variable("id", "Int", None)

    if msg_type == "MessageBucket":
        handled.add("linked_nodes")

    skip_for_spatial = {"x", "y", "z"} if msg_type == "MessageSpatial3D" else set()
    for var in getattr(agent, "variables", []):
        var_name = getattr(var, "name", "")
        if not var_name or var_name in skip_for_spatial:
            continue
        var_type = getattr(var, "var_type", DEFAULT_VAR_TYPE) or DEFAULT_VAR_TYPE
        add_variable(var_name, var_type, getattr(var, "default", None))

def _render_agents(agents: Sequence[AgentType], connections: Sequence[dict]) -> str:
    if not agents:
        return "# No agents available"

    input_map = _build_input_map(connections)
    blocks: list[str] = []
    for agent in agents:
        lines = [
            '"""',
            f"  {agent.name} agent",
            '"""',
            f'{agent.name}_agent = model.newAgent("{agent.name}")',
            f'{agent.name}_agent.newVariableInt("id")',
        ]

        for var in agent.variables:
            if var.name == "id":
                continue
            var_type = var.var_type or DEFAULT_VAR_TYPE
            method = _AGENT_VARIABLE_METHODS.get(var_type, _AGENT_VARIABLE_METHODS[DEFAULT_VAR_TYPE])
            if var_type in _ARRAY_TYPES:
                caster = float if var_type == "ArrayFloat" else int
                array_values = _parse_array(var.default, caster)
                array_length = len(array_values)
                lines.append(f'{agent.name}_agent.{method}("{var.name}", {array_length})')
                lines.append("# TODO: default array values must be explicitly defined when initializing agent populations")
            else:
                literal = _format_literal(var_type, var.default)
                lines.append(f'{agent.name}_agent.{method}("{var.name}", {literal})')

        for func in agent.functions:
            base = f'{agent.name}_agent.newRTCFunctionFile("{func.name}", {func.name}_file)'
            suffix = ""
            if func.output_type != "MessageNone":
                msg_key = _MESSAGE_TYPE_KEYS.get(func.output_type)
                if msg_key:
                    suffix += f'.setMessageOutput("{agent.name}_{msg_key}_location_message ")'
            if func.input_type != "MessageNone":
                msg_key = _MESSAGE_TYPE_KEYS.get(func.input_type)
                source_agent = _input_source_agent(agent.name, func.name, func.input_type, input_map)
                missing_input = False
                if msg_key and source_agent:
                    suffix += f'.setMessageInput("{source_agent}_{msg_key}_location_message ")'
                elif msg_key:
                    missing_input = True
                if missing_input:
                    lines.append(f"# TODO: connect message input for {agent.name}::{func.name}")
            lines.append(base + suffix)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_layers(layers: Sequence[Layer]) -> str:
    if not layers:
        return "layer_count = 0\n# No layers defined"

    lines = ["layer_count = 0"]
    for layer in layers:
        lines.append(f"# {layer.name}")
        lines.append("layer_count += 1")
        functions = list(getattr(layer, "function_ids", getattr(layer, "functions", [])))
        for idx, func_id in enumerate(functions):
            try:
                agent_name, func_name = func_id.split("::", 1)
            except ValueError:
                continue
            layer_accessor = "newLayer" if idx == 0 else "Layer"
            lines.append(f'model.{layer_accessor}("{layer.name}").addAgentFunction("{agent_name}", "{func_name}")')
    return "\n".join(lines)


def _render_spatial_constants(spatial_agents: Iterable[str]) -> str:
    agents = sorted(set(spatial_agents))
    if not agents:
        return "# MAX_SEARCH_RADIUS constants can be declared per agent when spatial messages are in use"
    return "\n".join(f"MAX_SEARCH_RADIUS_{name} = ?" for name in agents)


def _render_logging(agents: Sequence[AgentType]) -> str:
    if not agents:
        return "# No agents available for logging configuration"

    blocks: list[str] = []
    for agent in agents:
        lines = [
            f'{agent.name}_agent_log = logging_config.agent("{agent.name}")',
            f"{agent.name}_agent_log.logCount()",
        ]
        for var in getattr(agent, "variables", []):
            log_mode = getattr(var, "logging", None)
            method = _LOGGING_METHODS.get(log_mode)
            if not method:
                continue
            lines.append(f'{agent.name}_agent_log.{method}("{var.name}")')
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_agent_logs(agents: Sequence[AgentType]) -> str:
    indent = " " * 12
    if not agents:
        return indent + "# No agent log data available"

    lines: list[str] = []
    for agent in agents:
        lines.append(f'{indent}{agent.name}_agents = step.getAgent("{agent.name}")')
        lines.append(f'{indent}{agent.name}_agent_counts[counter] = {agent.name}_agents.getCount()')
        for var in getattr(agent, "variables", []):
            if _LOGGING_METHODS.get(getattr(var, "logging", None)):
                lines.append(f'{indent}{var.name} = {agent.name}_agents.getSumFloat("{var.name}")')
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_visualisation_blocks(
    agents: Sequence[AgentType],
    visualization: VisualizationSettings | None,
) -> tuple[str, str]:
    if not visualization or not visualization.activated:
        return (
            "# Visualisation disabled in configuration",
            "# Visualisation join disabled",
        )

    domain_width_literal = _safe_numeric_literal(getattr(visualization, "domain_width", None))
    begin_paused_literal = "True" if visualization.begin_paused else "False"

    lines: list[str] = [
        '"""',
        "  Create Visualisation",
        '"""',
        "if pyflamegpu.VISUALISATION and VISUALISATION:",
        "    vis = simulation.getVisualisation()",
        "    # Configure vis",
        f"    domain_width = {domain_width_literal}",
        "    INIT_CAM = ? # A value of the position of the domain by the end of the simulation, multiplied by 5, looks nice",
        "    vis.setInitialCameraLocation(0.0, 0.0, INIT_CAM)",
        "    vis.setCameraSpeed(? * domain_width) # values <<1 (e.g. 0.002) work fine",
        "    if DEBUG_PRINTING:",
        "        vis.setSimulationSpeed(1)",
        f"    vis.setBeginPaused({begin_paused_literal})",
    ]

    agent_map = {agent.name: agent for agent in agents}
    for agent_cfg in getattr(visualization, "agents", []):
        if not getattr(agent_cfg, "include", False):
            continue
        agent = agent_map.get(agent_cfg.agent_name)
        if not agent:
            continue

        vis_var = f"{agent_cfg.agent_name}_vis_agent"
        shape = agent_cfg.shape if agent_cfg.shape in VISUALIZATION_SHAPES else DEFAULT_VISUALIZATION_SHAPE
        color_mode = agent_cfg.color_mode if agent_cfg.color_mode in VISUALIZATION_COLOR_MODES else DEFAULT_VISUALIZATION_COLOR
        color_value = getattr(agent, "color", "#ffffff") or "#ffffff"

        lines.append("")
        lines.append(f"    {vis_var} = vis.addAgent(\"{agent_cfg.agent_name}\")")
        lines.append("    # Position vars are named x, y, z so they are used by default")
        lines.append(f"    {vis_var}.setModel(pyflamegpu.{shape})")
        lines.append(f"    {vis_var}.setModelScale(? * domain_width) # values <<1 (e.g. 0.03) work fine")

        if color_mode == _INTERPOLATED_MODE:
            interpolation = getattr(agent_cfg, "interpolation", None)
            variable_name = _resolve_interpolation_variable(interpolation, agent)
            min_value, max_value = _resolve_interpolation_bounds(interpolation)
            lines.append(
                f"    {vis_var}.setColor(pyflamegpu.HSVInterpolation.GREENRED(\"{variable_name}\", {min_value}, {max_value}))"
            )
        else:
            lines.append(f"    {vis_var}.setColor(pyflamegpu.Color(\"{color_value}\"))")

    if visualization.show_domain_boundaries:
        lines.extend([
            "",
            "    coord_boundary = list(env.getPropertyArrayFloat(\"BOUNDARY_COORDS\"))",
            "    pen = vis.newLineSketch(1, 1, 1, 0.8)",
            "    pen.addVertex(coord_boundary[0], coord_boundary[2], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[2], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[3], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[3], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[2], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[2], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[3], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[3], coord_boundary[5])",
            "",
            "    pen.addVertex(coord_boundary[0], coord_boundary[2], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[3], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[2], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[3], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[2], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[3], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[2], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[3], coord_boundary[5])",
            "",
            "    pen.addVertex(coord_boundary[0], coord_boundary[2], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[2], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[3], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[3], coord_boundary[4])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[2], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[2], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[0], coord_boundary[3], coord_boundary[5])",
            "    pen.addVertex(coord_boundary[1], coord_boundary[3], coord_boundary[5])",
        ])

    lines.append("")
    lines.append("    vis.activate()")

    block_one = "\n".join(lines)

    block_two_lines = [
        "if pyflamegpu.VISUALISATION and VISUALISATION and not ENSEMBLE:",
        "    vis.join() # join the visualisation thread and stops the visualisation closing after the simulation finishes",
    ]
    block_two = "\n".join(block_two_lines)

    return block_one, block_two


def _resolve_interpolation_variable(interpolation, agent: AgentType) -> str:
    if interpolation and getattr(interpolation, "variable", ""):
        return interpolation.variable
    for var in getattr(agent, "variables", []):
        if var.name:
            return var.name
    return "?"


def _resolve_interpolation_bounds(interpolation) -> tuple[str, str]:
    if not interpolation:
        return _format_number(0.0), _format_number(1.0)
    return _format_number(interpolation.min_value), _format_number(interpolation.max_value)


def _safe_numeric_literal(value, fallback: str = "?") -> str:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return _format_number(value)
    raw = str(value).strip()
    if not raw:
        return fallback
    try:
        parsed = float(raw)
    except ValueError:
        return fallback
    return _format_number(parsed)


def _format_literal(var_type: str | None, raw_value: str | None) -> str:
    var_type = var_type or DEFAULT_VAR_TYPE
    raw = (raw_value or "").strip()
    if var_type == SHAPE_VAR_TYPE:
        dims = _parse_array(raw, float)
        if not dims:
            return "?"
        return ", ".join(_format_shape_dimension(value) for value in dims)
    if var_type in _ARRAY_TYPES:
        items = _parse_array(raw, float if var_type == "ArrayFloat" else int)
        return "[" + ", ".join(_format_number(item) for item in items) + "]"
    if var_type == "Int":
        return str(_parse_int(raw))
    if var_type == "UInt8":
        return str(max(0, min(255, _parse_int(raw))))
    # Default to float
    return _format_number(_parse_float(raw))


def _parse_array(raw: str | None, caster) -> list:
    if not raw:
        return []
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if not value:
        return []
    items = []
    for part in value.split(","):
        piece = part.strip()
        if not piece:
            continue
        try:
            items.append(caster(piece))
        except (TypeError, ValueError):
            continue
    return items


def _parse_int(raw: str | None) -> int:
    try:
        return int(raw.strip()) if raw else 0
    except (ValueError, AttributeError):
        return 0


def _parse_float(raw: str | None) -> float:
    try:
        return float(raw.strip()) if raw else 0.0
    except (ValueError, AttributeError):
        return 0.0


def _format_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


def _format_shape_dimension(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return _format_number(value)


def _build_input_map(connections: Sequence[dict]) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for conn in connections:
        dst = conn.get("dst")
        src = conn.get("src")
        msg_type = conn.get("type")
        if not dst or not src or not msg_type:
            continue
        mapping.setdefault(dst, {})[msg_type] = src
    return mapping


def _input_source_agent(agent_name: str, func_name: str, msg_type: str, input_map: dict[str, dict[str, str]]) -> str | None:
    dst_key = f"{agent_name}::{func_name}"
    src_identifier = input_map.get(dst_key, {}).get(msg_type)
    if not src_identifier:
        return None
    return src_identifier.split("::", 1)[0]
