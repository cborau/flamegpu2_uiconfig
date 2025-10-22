from PySide6.QtWidgets import QMainWindow, QWidget, QSplitter, QTabWidget, QVBoxLayout
from PySide6.QtCore import Qt
from ui.tabs.agent_config_tab import AgentConfigTab
from ui.tabs.globals_tab import GlobalsTab
from ui.tabs.layers_tab import LayersTab
from ui.tabs.model_tab import ModelTab
from ui.canvas.canvas_view import CanvasView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABM Configurator")
        self.resize(1400, 800)

        splitter = QSplitter(Qt.Horizontal)

        # Left panel with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumWidth(400)
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.addTab(AgentConfigTab(), "Agent Config.")
        self.tab_widget.addTab(GlobalsTab(), "Globals")
        self.tab_widget.addTab(LayersTab(), "Layers")
        self.tab_widget.addTab(ModelTab(), "Model")

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.tab_widget)
        left_panel.setLayout(left_layout)

        # Right panel with canvas
        self.canvas = CanvasView()

        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.setSizes([450, 950])  # 1/3 - 2/3

        self.setCentralWidget(splitter)
