from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QColorDialog,QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QMessageBox
from PySide6.QtCore import Qt

class AgentConfigTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Agent Name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        color_btn_layout = QHBoxLayout()
        self.color_btn = QPushButton("Select Agent Color")
        self.color_btn.clicked.connect(self.choose_color)
        self.color_label = QLabel("None")
        color_btn_layout.addWidget(self.color_btn)
        color_btn_layout.addWidget(self.color_label)
        layout.addLayout(color_btn_layout)

        layout.addWidget(QLabel("Variables (name + default):"))
        self.vars_table = QTableWidget(0, 2)
        self.vars_table.setHorizontalHeaderLabels(["Variable", "Default Value"])
        layout.addWidget(self.vars_table)

        layout.addWidget(QLabel("Functions:"))
        self.funcs_table = QTableWidget(0, 4)
        self.funcs_table.setHorizontalHeaderLabels(["Name", "Description", "Input", "Output"])
        layout.addWidget(self.funcs_table)

        add_func_btn = QPushButton("Add Function")
        add_func_btn.clicked.connect(self.add_function_row)
        layout.addWidget(add_func_btn)

        self.save_btn = QPushButton("Save Agent Type")
        self.save_btn.clicked.connect(self.save_agent_type)
        layout.addWidget(self.save_btn)

        self.selected_color = None

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color
            self.color_label.setText(color.name())
            self.color_label.setStyleSheet(f"background-color: {color.name()}")

    def add_function_row(self):
        row = self.funcs_table.rowCount()
        self.funcs_table.insertRow(row)
        for col in range(4):
            if col in [2, 3]:
                combo = QComboBox()
                combo.addItems(["MessageNone", "MessageSpatial3D", "MessageBucket", "MessageArray3D"])
                self.funcs_table.setCellWidget(row, col, combo)
            else:
                self.funcs_table.setItem(row, col, QTableWidgetItem(""))

    def save_agent_type(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Agent name cannot be empty")
            return

        print(f"Saving Agent '{name}' with color {self.selected_color.name() if self.selected_color else 'None'}")
        print("Variables:")
        for row in range(self.vars_table.rowCount()):
            var = self.vars_table.item(row, 0).text()
            val = self.vars_table.item(row, 1).text()
            print(f"  {var} = {val}")

        print("Functions:")
        for row in range(self.funcs_table.rowCount()):
            name_item = self.funcs_table.item(row, 0).text()
            desc_item = self.funcs_table.item(row, 1).text()
            input_type = self.funcs_table.cellWidget(row, 2).currentText()
            output_type = self.funcs_table.cellWidget(row, 3).currentText()
            print(f"  {name_item} ({input_type} -> {output_type}): {desc_item}")
