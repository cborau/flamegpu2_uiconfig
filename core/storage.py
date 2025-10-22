import json
from core.models import AgentType, AgentFunction, AgentVariable, Layer, GlobalVariable


def save_config(filename, agents, layers, globals_):
    data = {
        "agents": [agent.__dict__ for agent in agents],
        "layers": [layer.__dict__ for layer in layers],
        "globals": [glob.__dict__ for glob in globals_]
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def load_config(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

    agents = []
    for d in data["agents"]:
        variables = [AgentVariable(**v) for v in d["variables"]]
        functions = [AgentFunction(**f) for f in d["functions"]]
        agents.append(AgentType(d["name"], d["color"], variables, functions))

    layers = [Layer(**l) for l in data["layers"]]
    globals_ = [GlobalVariable(**g) for g in data["globals"]]
    return agents, layers, globals_
