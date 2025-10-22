from PySide6.QtCore import QObject, Signal

class SignalBus(QObject):
    agent_added = Signal(object)      # Emits AgentType
    agent_updated = Signal(object)    # Emits AgentType
    layer_updated = Signal()
    globals_updated = Signal()
    redraw_canvas = Signal()

signals = SignalBus()
