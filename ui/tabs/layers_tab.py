from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem

class LayersTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Layer Name:"))
        self.layer_name_edit = QLineEdit()
        layout.addWidget(self.layer_name_edit)

        layout.addWidget(QLabel("Functions in Layer:"))
        self.func_list = QListWidget()
        self.func_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.func_list)

        self.add_btn = QPushButton("Add Layer")
        self.add_btn.clicked.connect(self.add_layer)
        layout.addWidget(self.add_btn)

        self.layer_store = []

    def add_layer(self):
        name = self.layer_name_edit.text().strip()
        if not name:
            return

        selected_funcs = [item.text() for item in self.func_list.selectedItems()]
        self.layer_store.append({"name": name, "functions": selected_funcs})
        print(f"Layer '{name}' with functions: {selected_funcs}")
        self.layer_name_edit.clear()
        self.func_list.clearSelection()
