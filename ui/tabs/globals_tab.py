from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView
from core.models import GlobalVariable, VAR_TYPE_OPTIONS, DEFAULT_VAR_TYPE

class GlobalsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Global Variables (name, type, value):"))
        self.globals_table = QTableWidget(0, 3)
        self.globals_table.setHorizontalHeaderLabels(["Name", "Type", "Value"])
        self.globals_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.globals_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.globals_table)

        self.add_btn = QPushButton("Add Variable")
        self.add_btn.clicked.connect(self.add_variable)
        layout.addWidget(self.add_btn)

    def add_variable(self):
        row = self.globals_table.rowCount()
        self.globals_table.insertRow(row)
        self.globals_table.setItem(row, 0, QTableWidgetItem(""))
        combo = self._make_type_combo(DEFAULT_VAR_TYPE)
        self.globals_table.setCellWidget(row, 1, combo)
        self.globals_table.setItem(row, 2, QTableWidgetItem(""))

    def get_globals(self):
        globals_list = []
        for row in range(self.globals_table.rowCount()):
            name_item = self.globals_table.item(row, 0)
            type_combo = self.globals_table.cellWidget(row, 1)
            value_item = self.globals_table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            value = value_item.text() if value_item else ""
            var_type = type_combo.currentText() if isinstance(type_combo, QComboBox) else DEFAULT_VAR_TYPE
            globals_list.append(GlobalVariable(name, value, var_type))
        return globals_list

    def load_globals(self, globals_list):
        self.globals_table.setRowCount(0)
        for glob in globals_list:
            row = self.globals_table.rowCount()
            self.globals_table.insertRow(row)
            self.globals_table.setItem(row, 0, QTableWidgetItem(glob.name))
            combo = self._make_type_combo(getattr(glob, "var_type", DEFAULT_VAR_TYPE))
            self.globals_table.setCellWidget(row, 1, combo)
            self.globals_table.setItem(row, 2, QTableWidgetItem(glob.value))

    def clear_globals(self):
        self.globals_table.setRowCount(0)

    def _make_type_combo(self, current: str | None = None):
        combo = QComboBox()
        combo.addItems(VAR_TYPE_OPTIONS)
        if current in VAR_TYPE_OPTIONS:
            combo.setCurrentText(current)
        else:
            combo.setCurrentText(DEFAULT_VAR_TYPE)
        combo.setFocusPolicy(Qt.StrongFocus)
        return combo
