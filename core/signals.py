from PySide6.QtCore import QObject, Signal

class SignalBus(QObject):
    agent_added = Signal(object)           # Emits AgentType
    agent_updated = Signal(object)         # Emits AgentType
    agent_removed = Signal(str)            # Emits agent name
    request_edit_agent = Signal(object)    # Emits AgentType (open AgentConfig prefilled)
    layer_updated = Signal()
    globals_updated = Signal()
    redraw_canvas = Signal()

signals = SignalBus()
