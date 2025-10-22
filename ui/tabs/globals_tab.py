from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem

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
