from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt
from core.signals import signals

class LayersTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Existing Layers:"))
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
        self.functions = []    # list of all available functions
        self.current_layer_index = -1

        signals.agent_added.connect(self.receive_agent)
        signals.agent_updated.connect(self.receive_agent)   # refresh functions after updates
        signals.agent_removed.connect(self.remove_agent_functions)

    def receive_agent(self, agent):
        # rebuild the function names for this agent and merge unique
        new_func_names = [f"{agent.name}::{f.name}" for f in agent.functions]
        # Remove any older entries for this agent, then extend
        self.functions = [f for f in self.functions if not f.startswith(f"{agent.name}::")]
        self.functions.extend(new_func_names)
        self.refresh_function_list([])

    def remove_agent_functions(self, agent_name: str):
        self.functions = [f for f in self.functions if not f.startswith(f"{agent_name}::")]
        # Also purge from stored layers
        for layer in self.layer_store:
            layer["functions"] = [f for f in layer["functions"] if not f.startswith(f"{agent_name}::")]
        self.refresh_layer_table()

        if not self.layer_store:
            self.current_layer_index = -1
            self.refresh_function_list([])
            return

        if self.current_layer_index >= len(self.layer_store):
            self.current_layer_index = len(self.layer_store) - 1

        selected_funcs = []
        if 0 <= self.current_layer_index < len(self.layer_store):
            selected_funcs = self.layer_store[self.current_layer_index]["functions"]
            self.layer_table.selectRow(self.current_layer_index)

        self.refresh_function_list(selected_funcs)

    def add_layer(self):
        name = self.layer_name_edit.text().strip()
        if not name:
            return
        func_names = [item.text() for item in self.func_list.selectedItems() if item.checkState() == Qt.Checked]
        self.layer_store.append({"name": name, "functions": func_names})
        self.refresh_layer_table()
        self.layer_name_edit.clear()
        self.func_list.clearSelection()

    def refresh_layer_table(self):
        self.layer_table.setRowCount(0)
        for layer in self.layer_store:
            row = self.layer_table.rowCount()
            self.layer_table.insertRow(row)
            self.layer_table.setItem(row, 0, QTableWidgetItem(layer["name"]))

    def select_layer(self, row, col):
        if row >= len(self.layer_store):
            return

        # Save current selection state back to previous layer
        if 0 <= self.current_layer_index < len(self.layer_store):
            prev_funcs = []
            for i in range(self.func_list.count()):
                item = self.func_list.item(i)
                if item.checkState() == Qt.Checked:
                    prev_funcs.append(item.text())
            self.layer_store[self.current_layer_index]["functions"] = prev_funcs

        self.current_layer_index = row
        selected_layer = self.layer_store[row]
        self.refresh_function_list(selected_layer["functions"])

    def refresh_function_list(self, selected_funcs):
        self.func_list.clear()
        for fname in self.functions:
            item = QListWidgetItem(fname)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if fname in selected_funcs else Qt.Unchecked)
            self.func_list.addItem(item)

    def update_function_list(self, new_funcs):
        self.functions = new_funcs
        self.refresh_function_list([])
