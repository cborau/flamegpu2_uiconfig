from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QTabWidget, QVBoxLayout,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from pathlib import Path
from ui.tabs.agent_config_tab import AgentConfigTab
from ui.tabs.globals_tab import GlobalsTab
from ui.tabs.layers_tab import LayersTab
from ui.tabs.model_tab import ModelTab
from ui.canvas.canvas_view import CanvasView
from core.signals import signals
from core.storage import save_config, load_config
from core.ui_helpers import show_quiet_message

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

        self._config_dir = (Path(__file__).resolve().parent.parent / "configs").resolve()
        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._init_menus()

        # When the Model tab requests to edit, open Agent Config prefilled
        signals.request_edit_agent.connect(self._open_edit_agent)

    def _open_edit_agent(self, agent):
        self.tab_widget.setCurrentWidget(self.agent_config_tab)
        self.agent_config_tab.load_agent_for_edit(agent)

    def _init_menus(self):
        file_menu = self.menuBar().addMenu("&File")

        load_action = file_menu.addAction("Load Configuration…")
        load_action.triggered.connect(self._load_configuration)

        save_action = file_menu.addAction("Save Configuration…")
        save_action.triggered.connect(self._save_configuration)

    def _save_configuration(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            str(self._config_dir),
            "JSON Files (*.json)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".json"):
            filename += ".json"

        try:
            agents = self.model_tab.get_agents()
            layers = self.layers_tab.get_layers()
            globals_ = self.globals_tab.get_globals()
            connections = self.canvas.get_connections()
            manual_layout = self.canvas.get_manual_layout()
            save_config(filename, agents, layers, globals_, connections, manual_layout)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not save configuration:\n{exc}")
            return

        show_quiet_message(self, "Saved", f"Configuration saved to:\n{filename}")

    def _load_configuration(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            str(self._config_dir),
            "JSON Files (*.json)"
        )
        if not filename:
            return

        try:
            agents, layers, globals_, connections, manual_layout = load_config(filename)
        except Exception as exc:
            QMessageBox.critical(self, "Load Failed", f"Could not load configuration:\n{exc}")
            return

        # Remove existing agents and reset state
        existing_agents = self.model_tab.get_agents()
        for agent in existing_agents:
            signals.agent_removed.emit(agent.name)

        self.canvas.set_connections([])

        self.layers_tab.clear_layers()
        self.globals_tab.clear_globals()

        # Load new agents
        for agent in agents:
            signals.agent_added.emit(agent)

        self.agent_config_tab.set_agents(agents)

        # Load globals and layers
        self.globals_tab.load_globals(globals_)
        if globals_:
            signals.globals_updated.emit()

        self.layers_tab.load_layers(layers)

        self.canvas.set_manual_layout(manual_layout)

        self.canvas.set_connections(connections)

        # Select first agent/layer if available
        if self.model_tab.agent_list.count() > 0:
            self.model_tab.agent_list.setCurrentRow(0)
        if self.layers_tab.layer_table.rowCount() > 0:
            self.layers_tab.layer_table.selectRow(0)

        signals.redraw_canvas.emit()

        show_quiet_message(self, "Loaded", f"Configuration loaded from:\n{filename}")
