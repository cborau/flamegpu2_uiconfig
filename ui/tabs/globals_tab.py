from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
from core.models import GlobalVariable

class GlobalsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Global Variables (name, value):"))
        self.globals_table = QTableWidget(0, 2)
        self.globals_table.setHorizontalHeaderLabels(["Name", "Value"])
        layout.addWidget(self.globals_table)

        self.add_btn = QPushButton("Add Variable")
        self.add_btn.clicked.connect(self.add_variable)
        layout.addWidget(self.add_btn)

    def add_variable(self):
        row = self.globals_table.rowCount()
        self.globals_table.insertRow(row)
        self.globals_table.setItem(row, 0, QTableWidgetItem(""))
        self.globals_table.setItem(row, 1, QTableWidgetItem(""))

    def get_globals(self):
        globals_list = []
        for row in range(self.globals_table.rowCount()):
            name_item = self.globals_table.item(row, 0)
            value_item = self.globals_table.item(row, 1)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            value = value_item.text() if value_item else ""
            globals_list.append(GlobalVariable(name, value))
        return globals_list

    def load_globals(self, globals_list):
        self.globals_table.setRowCount(0)
        for glob in globals_list:
            row = self.globals_table.rowCount()
            self.globals_table.insertRow(row)
            self.globals_table.setItem(row, 0, QTableWidgetItem(glob.name))
            self.globals_table.setItem(row, 1, QTableWidgetItem(glob.value))

    def clear_globals(self):
        self.globals_table.setRowCount(0)
