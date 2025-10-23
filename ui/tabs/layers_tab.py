from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QCheckBox
from PySide6.QtCore import Qt
from core.signals import signals
from core.models import Layer

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
        self.layer_table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
        )
        self.layer_table.cellClicked.connect(self.select_layer)
        self.layer_table.itemChanged.connect(self._on_layer_name_changed)
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

        self.layer_store = []  # list of dicts {name, functions, height}
        self.functions = []    # list of all available "Agent::Function"
        self.current_layer_index = -1
        self._updating_layer_table = False

        # Keep functions list in sync with agents
        signals.agent_added.connect(self.receive_agent)
        signals.agent_updated.connect(self.receive_agent)
        signals.agent_removed.connect(self.remove_agent_functions)
        signals.layer_height_changed.connect(self.update_layer_height)

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
        self.layer_store.append({"name": name, "functions": func_names, "height": None})
        self.refresh_layer_table()
        self.layer_name_edit.clear()
        self.func_list.clearSelection()
        self._broadcast_layers()

    def refresh_layer_table(self):
        self._updating_layer_table = True
        self.layer_table.blockSignals(True)
        self.layer_table.setRowCount(0)
        for layer in self.layer_store:
            row = self.layer_table.rowCount()
            self.layer_table.insertRow(row)
            item = QTableWidgetItem(layer["name"])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.layer_table.setItem(row, 0, item)
        self.layer_table.blockSignals(False)
        self._updating_layer_table = False
        if 0 <= self.current_layer_index < self.layer_table.rowCount():
            self.layer_table.selectRow(self.current_layer_index)

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

    def load_layers(self, layers):
        self.layer_store = [
            {
                "name": layer.name,
                "functions": list(getattr(layer, "function_ids", getattr(layer, "functions", []))),
                "height": getattr(layer, "height", None),
            }
            for layer in layers
        ]
        self.current_layer_index = 0 if self.layer_store else -1
        self.refresh_layer_table()
        if self.layer_store:
            self.refresh_function_list(self.layer_store[self.current_layer_index]["functions"])
        else:
            self.refresh_function_list([])
        self._broadcast_layers()

    def clear_layers(self):
        self.layer_store = []
        self.current_layer_index = -1
        self.refresh_layer_table()
        self.refresh_function_list([])
        self._broadcast_layers()

    def _on_layer_name_changed(self, item: QTableWidgetItem):
        if self._updating_layer_table:
            return
        row = item.row()
        if row < 0 or row >= len(self.layer_store):
            return
        new_name = item.text().strip()
        if not new_name:
            self._restore_layer_name(row, item)
            return
        if any(i != row and layer["name"].lower() == new_name.lower() for i, layer in enumerate(self.layer_store)):
            self._restore_layer_name(row, item)
            return
        self.layer_store[row]["name"] = new_name
        self._broadcast_layers()

    def _restore_layer_name(self, row: int, item: QTableWidgetItem):
        self._updating_layer_table = True
        self.layer_table.blockSignals(True)
        item.setText(self.layer_store[row]["name"])
        self.layer_table.blockSignals(False)
        self._updating_layer_table = False

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
        payload = []
        for L in self.layer_store:
            payload.append({
                "name": L["name"],
                "functions": list(L["functions"]),
                "height": L.get("height"),
            })
        signals.layers_changed.emit(payload)

    def get_layers(self):
        if 0 <= self.current_layer_index < len(self.layer_store):
            self.layer_store[self.current_layer_index]["functions"] = [item.text() for item in self._iter_checked_items()]
        return [Layer(layer["name"], list(layer["functions"]), layer.get("height")) for layer in self.layer_store]

    def update_layer_height(self, layer_name: str, height: float):
        for layer in self.layer_store:
            if layer["name"] == layer_name:
                layer["height"] = height
                break
