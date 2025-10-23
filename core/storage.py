import json
from dataclasses import asdict
from core.models import AgentType, AgentFunction, AgentVariable, Layer, GlobalVariable


def save_config(filename, agents, layers, globals_, connections=None):
    data = {
        "agents": [asdict(agent) for agent in agents],
        "layers": [asdict(layer) for layer in layers],
        "globals": [asdict(glob) for glob in globals_],
        "connections": connections or [],
    }
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
        layers.append(Layer(l.get("name", "Layer"), list(func_ids)))

    globals_ = []
    for g in data.get("globals", []):
        globals_.append(GlobalVariable(g.get("name", ""), g.get("value", "")))

    connections = data.get("connections", [])
    return agents, layers, globals_, connections
