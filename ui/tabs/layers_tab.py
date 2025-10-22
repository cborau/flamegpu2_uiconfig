from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QCheckBox
from PySide6.QtCore import Qt
from core.signals import signals

class LayersTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Header row with Adjust View
        head = QHBoxLayout()
        head.addWidget(QLabel("Existing Layers:"))
        self.btn_fit = QPushButton("Adjust View")
        self.btn_fit.clicked.connect(lambda: signals.adjust_view_requested.emit())
        head.addWidget(self.btn_fit)
        self.manual_toggle = QCheckBox("Adjust positions manually")
        self.manual_toggle.toggled.connect(lambda v: signals.manual_layout_toggled.emit(v))
        head.addWidget(self.manual_toggle)

        layout.addLayout(head)

        self.layer_table = QTableWidget(0, 1)
        self.layer_table.setHorizontalHeaderLabels(["Layer Name"])
        self.layer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.layer_table.cellClicked.connect(self.select_layer)
        layout.addWidget(self.layer_table)

        layout.addWidget(QLabel("Functions for Selected Layer:"))
        self.func_list = QListWidget()
        self.func_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.func_list)

        layout.addWidget(QLabel("Add New Layer:"))
        self.layer_name_edit = QLineEdit()
        layout.addWidget(self.layer_name_edit)

        self.add_btn = QPushButton("Add Layer")
        self.add_btn.clicked.connect(self.add_layer)
        layout.addWidget(self.add_btn)

        self.layer_store = []  # list of dicts {name, functions}
        self.functions = []    # list of all available "Agent::Function"
        self.current_layer_index = -1

        # Keep functions list in sync with agents
        signals.agent_added.connect(self.receive_agent)
        signals.agent_updated.connect(self.receive_agent)
        signals.agent_removed.connect(self.remove_agent_functions)

    # --- Functions inventory from agents ---
    def receive_agent(self, agent):
        new_func_names = [f"{agent.name}::{f.name}" for f in agent.functions]
        # Remove old entries for this agent then extend
        self.functions = [f for f in self.functions if not f.startswith(f"{agent.name}::")]
        self.functions.extend(new_func_names)
        self.refresh_function_list(self._current_selected_funcs())
        self._broadcast_layers()

    def remove_agent_functions(self, agent_name: str):
        self.functions = [f for f in self.functions if not f.startswith(f"{agent_name}::")]
        for layer in self.layer_store:
            layer["functions"] = [f for f in layer["functions"] if not f.startswith(f"{agent_name}::")]
        self.refresh_layer_table()
        self.refresh_function_list(self._current_selected_funcs())
        self._broadcast_layers()

    # --- Layers CRUD ---
    def add_layer(self):
        name = self.layer_name_edit.text().strip()
        if not name:
            return
        func_names = [item.text() for item in self._iter_checked_items()]
        self.layer_store.append({"name": name, "functions": func_names})
        self.refresh_layer_table()
        self.layer_name_edit.clear()
        self.func_list.clearSelection()
        self._broadcast_layers()

    def refresh_layer_table(self):
        self.layer_table.setRowCount(0)
        for layer in self.layer_store:
            row = self.layer_table.rowCount()
            self.layer_table.insertRow(row)
            self.layer_table.setItem(row, 0, QTableWidgetItem(layer["name"]))

    def select_layer(self, row, col):
        if row >= len(self.layer_store):
            return
        # Save previous selection back
        if 0 <= self.current_layer_index < len(self.layer_store):
            self.layer_store[self.current_layer_index]["functions"] = [item.text() for item in self._iter_checked_items()]
        self.current_layer_index = row
        selected_layer = self.layer_store[row]
        self.refresh_function_list(selected_layer["functions"])
        self._broadcast_layers()

    # --- UI helpers ---
    def refresh_function_list(self, selected_funcs):
        self.func_list.clear()
        for fname in sorted(self.functions):
            item = QListWidgetItem(fname)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if fname in selected_funcs else Qt.Unchecked)
            self.func_list.addItem(item)

    def _iter_checked_items(self):
        for i in range(self.func_list.count()):
            item = self.func_list.item(i)
            if item.checkState() == Qt.Checked:
                yield item

    def _current_selected_funcs(self):
        if 0 <= self.current_layer_index < len(self.layer_store):
            return list(self.layer_store[self.current_layer_index]["functions"])
        return []

    def _broadcast_layers(self):
        # Ensure UI state of the current layer is persisted before emitting
        if 0 <= self.current_layer_index < len(self.layer_store):
            self.layer_store[self.current_layer_index]["functions"] = [item.text() for item in self._iter_checked_items()]
        signals.layers_changed.emit([{"name": L["name"], "functions": list(L["functions"])} for L in self.layer_store])
