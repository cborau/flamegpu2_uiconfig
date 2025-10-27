import json
from dataclasses import asdict
from core.models import (
    AgentType,
    AgentFunction,
    AgentVariable,
    Layer,
    GlobalVariable,
    VisualizationAgentConfig,
    VisualizationInterpolation,
    VisualizationSettings,
    DEFAULT_VISUALIZATION_COLOR,
    DEFAULT_VISUALIZATION_SHAPE,
    DEFAULT_VAR_TYPE,
)


def save_config(filename, agents, layers, globals_, connections=None, layout=None, visualization: VisualizationSettings | None = None):
    data = {
        "agents": [asdict(agent) for agent in agents],
        "layers": [asdict(layer) for layer in layers],
        "globals": [asdict(glob) for glob in globals_],
        "connections": connections or [],
    }
    if layout:
        data["manual_layout"] = layout
    if visualization is not None:
        data["visualization"] = asdict(visualization)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_config(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    agents = []
    for d in data.get("agents", []):
        variables = [AgentVariable(**v) for v in d.get("variables", [])]
        functions = [AgentFunction(**f) for f in d.get("functions", [])]
        agents.append(AgentType(d.get("name", "Unnamed Agent"), d.get("color", "#ffffff"), variables, functions))

    layers = []
    for l in data.get("layers", []):
        func_ids = l.get("function_ids")
        if func_ids is None:
            func_ids = l.get("functions", [])
        layers.append(Layer(l.get("name", "Layer"), list(func_ids), l.get("height")))

    globals_ = []
    for g in data.get("globals", []):
        globals_.append(GlobalVariable(
            g.get("name", ""),
            g.get("value", ""),
            g.get("var_type", DEFAULT_VAR_TYPE),
            g.get("is_macro", False),
        ))

    connections = data.get("connections", [])
    layout = data.get("manual_layout", {})
    visualization = _parse_visualization(data.get("visualization"))
    return agents, layers, globals_, connections, layout, visualization


def _parse_visualization(raw) -> VisualizationSettings | None:
    if not raw:
        return None

    def _as_float(value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    agents_cfg: list[VisualizationAgentConfig] = []
    for entry in raw.get("agents", []):
        interp_raw = entry.get("interpolation")
        interpolation: VisualizationInterpolation | None = None
        if interp_raw:
            interpolation = VisualizationInterpolation(
                variable=interp_raw.get("variable", ""),
                min_value=_as_float(interp_raw.get("min_value"), 0.0),
                max_value=_as_float(interp_raw.get("max_value"), 1.0),
            )
        agents_cfg.append(VisualizationAgentConfig(
            agent_name=entry.get("agent_name", ""),
            include=entry.get("include", False),
            shape=entry.get("shape", DEFAULT_VISUALIZATION_SHAPE),
            color_mode=entry.get("color_mode", DEFAULT_VISUALIZATION_COLOR),
            interpolation=interpolation,
        ))

    return VisualizationSettings(
        activated=raw.get("activated", False),
        domain_width=str(raw.get("domain_width", "")),
        begin_paused=raw.get("begin_paused", False),
        show_domain_boundaries=raw.get("show_domain_boundaries", False),
        agents=agents_cfg,
    )
