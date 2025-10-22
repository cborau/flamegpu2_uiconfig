from PySide6.QtCore import QObject, Signal

class SignalBus(QObject):
    # Agents
    agent_added = Signal(object)           # Emits AgentType
    agent_updated = Signal(object)         # Emits AgentType
    agent_removed = Signal(str)            # Emits agent name

    # Layers & globals
    layers_changed = Signal(list)          # Emits List[{"name": str, "functions": List[str]}]
    layer_updated = Signal()               # (kept for compatibility)
    globals_updated = Signal()

    # Canvas
    redraw_canvas = Signal()
    adjust_view_requested = Signal()       # Ask the view to fit the whole layout
    manual_layout_toggled = Signal(bool)   # True = user drags nodes; wiring disabled


    # Model-tab requests
    request_edit_agent = Signal(object)    # Emits AgentType (open AgentConfig prefilled)

    # Connections (optional persistence/hooks)
    connection_added = Signal(dict)        # {"src": "Agent::Func", "dst": "Agent::Func", "type": "MessageSpatial3D"}
    connection_removed = Signal(dict)      # same payload as above

signals = SignalBus()
