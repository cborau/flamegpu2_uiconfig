from PySide6.QtWidgets import QMainWindow, QWidget, QSplitter, QTabWidget, QVBoxLayout
from PySide6.QtCore import Qt
from ui.tabs.agent_config_tab import AgentConfigTab
from ui.tabs.globals_tab import GlobalsTab
from ui.tabs.layers_tab import LayersTab
from ui.tabs.model_tab import ModelTab
from ui.canvas.canvas_view import CanvasView
from core.signals import signals

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABM Configurator")
        self.resize(1400, 800)

        splitter = QSplitter(Qt.Horizontal)

        # Left panel with tabs (keep references!)
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumWidth(420)
        self.tab_widget.setTabPosition(QTabWidget.North)

        self.agent_config_tab = AgentConfigTab()
        self.globals_tab = GlobalsTab()
        self.layers_tab = LayersTab()
        self.model_tab = ModelTab()

        self.tab_widget.addTab(self.agent_config_tab, "Agent Config.")
        self.tab_widget.addTab(self.globals_tab, "Globals")
        self.tab_widget.addTab(self.layers_tab, "Layers")
        self.tab_widget.addTab(self.model_tab, "Model")

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.tab_widget)
        left_panel.setLayout(left_layout)

        # Right panel with canvas
        self.canvas = CanvasView()

        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.setSizes([500, 900])  # ~1/3 - 2/3

        self.setCentralWidget(splitter)

        # When the Model tab requests to edit, open Agent Config prefilled
        signals.request_edit_agent.connect(self._open_edit_agent)

    def _open_edit_agent(self, agent):
        self.tab_widget.setCurrentWidget(self.agent_config_tab)
        self.agent_config_tab.load_agent_for_edit(agent)
