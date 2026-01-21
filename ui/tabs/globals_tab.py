from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHeaderView
from core.models import GlobalVariable, DEFAULT_VAR_TYPE, GLOBAL_VAR_TYPE_OPTIONS

class GlobalsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Global Variables (name, type, value | shape):"))
        self.globals_table = QTableWidget(0, 5)
        self.globals_table.setHorizontalHeaderLabels(["Name", "Type", "Value | Shape", "MacroProperty", ""])
        self.globals_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.globals_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.globals_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.globals_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        value_header = self.globals_table.horizontalHeaderItem(2)
        if value_header:
            value_header.setToolTip(
                "Specify array values separated by commas. If variable is a MacroProperty, "
                "specify shape (separated by commas) instead of values. Macro Properties are initialized programatically,"
                "so you can use ? to denote undefined dimensions (e.g. '10,?,5')"
            )
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
        self.globals_table.setItem(row, 3, self._make_macro_item(False))
        btn = self._make_delete_button(self.globals_table)
        btn.clicked.connect(lambda _, b=btn: self._remove_table_row(self.globals_table, b))
        self.globals_table.setCellWidget(row, 4, btn)

    def get_globals(self):
        globals_list = []
        for row in range(self.globals_table.rowCount()):
            name_item = self.globals_table.item(row, 0)
            type_combo = self.globals_table.cellWidget(row, 1)
            value_item = self.globals_table.item(row, 2)
            macro_item = self.globals_table.item(row, 3)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            value = value_item.text() if value_item else ""
            var_type = type_combo.currentText() if isinstance(type_combo, QComboBox) else DEFAULT_VAR_TYPE
            is_macro = macro_item.checkState() == Qt.Checked if macro_item else False
            globals_list.append(GlobalVariable(name, value, var_type, is_macro))
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
            self.globals_table.setItem(row, 3, self._make_macro_item(getattr(glob, "is_macro", False)))
            btn = self._make_delete_button(self.globals_table)
            btn.clicked.connect(lambda _, b=btn: self._remove_table_row(self.globals_table, b))
            self.globals_table.setCellWidget(row, 4, btn)

    def clear_globals(self):
        self.globals_table.setRowCount(0)

    def _make_type_combo(self, current: str | None = None):
        combo = QComboBox()
        combo.addItems(GLOBAL_VAR_TYPE_OPTIONS)
        if current in GLOBAL_VAR_TYPE_OPTIONS:
            combo.setCurrentText(current)
        else:
            combo.setCurrentText(DEFAULT_VAR_TYPE)
        combo.setFocusPolicy(Qt.StrongFocus)
        return combo

    def _make_macro_item(self, checked: bool):
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        item.setText("")
        return item

    def _make_delete_button(self, table):
        btn = QPushButton()
        icon = QIcon.fromTheme("edit-delete")
        if icon.isNull():
            btn.setText("🗑")
        else:
            btn.setIcon(icon)
        return btn

    def _remove_table_row(self, table, button):
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                if table.cellWidget(r, c) is button:
                    table.removeRow(r)
                    return
