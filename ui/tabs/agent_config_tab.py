from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QColorDialog,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QMessageBox,
    QAbstractItemView, QHeaderView
)
from PySide6.QtGui import QIcon, QColor
from core.models import (
    AgentType,
    AgentVariable,
    AgentFunction,
    VAR_TYPE_OPTIONS,
    DEFAULT_VAR_TYPE,
    AGENT_LOGGING_OPTIONS,
    DEFAULT_LOGGING_OPTION,
)
from core.signals import signals
from core.ui_helpers import show_quiet_message

class AgentConfigTab(QWidget):
    def __init__(self):
        super().__init__()

        # Color palette (cycled if user doesn’t pick one)
        self.default_colors = [
            "#e6194B", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe"
        ]

        # Local storage of created templates (by name)
        self.agent_templates = {}
        # Edit state
        self.edit_mode = False
        self.editing_original_name = None

        self.template_combo = QComboBox()
        self.template_combo.addItem("-- Select Template --")
        self.template_combo.currentTextChanged.connect(self.load_template)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Template:"))
        layout.addWidget(self.template_combo)

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

        layout.addWidget(QLabel("Variables (name, type, default):"))
        self.vars_table = QTableWidget(0, 5)
        self.vars_table.setHorizontalHeaderLabels(["Variable", "Type", "Default Value", "Logging", ""])
        self.vars_table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.vars_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.vars_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.vars_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.vars_table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(self.vars_table)

        add_var_btn = QPushButton("Add Variable")
        add_var_btn.clicked.connect(self.add_variable_row)
        layout.addWidget(add_var_btn)

        layout.addWidget(QLabel("Functions:"))
        self.funcs_table = QTableWidget(0, 5)
        self.funcs_table.setHorizontalHeaderLabels(["Name", "Description", "Input", "Output", ""])
        self.funcs_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.funcs_table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(self.funcs_table)

        add_func_btn = QPushButton("Add Function")
        add_func_btn.clicked.connect(self.add_function_row)
        layout.addWidget(add_func_btn)

        self.save_btn = QPushButton("Save Agent Type")
        self.save_btn.clicked.connect(self.save_agent_type)
        layout.addWidget(self.save_btn)

        self.selected_color = None
        self.populate_default_variables()

        # sync templates with global agent signals
        signals.agent_added.connect(self._register_agent_template)
        signals.agent_updated.connect(self._register_agent_template)
        signals.agent_removed.connect(self._remove_agent_template)

    # ---------- Helpers ----------
    def reset_fields(self):
        self.name_edit.clear()
        self.color_label.setText("None")
        self.color_label.setStyleSheet("")
        self.selected_color = None
        self.vars_table.setRowCount(0)
        self.funcs_table.setRowCount(0)
        self.populate_default_variables()
        self.edit_mode = False
        self.editing_original_name = None
        self.save_btn.setText("Save Agent Type")

    def populate_default_variables(self):
        for var in ["x", "y", "z", "vx", "vy", "vz"]:
            self.add_variable_row(name=var, var_type=DEFAULT_VAR_TYPE, default="0.0", logging=DEFAULT_LOGGING_OPTION)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color
            self.color_label.setText(color.name())
            self.color_label.setStyleSheet(f"background-color: {color.name()}")

    def add_variable_row(
        self,
        name: str = "",
        var_type: str = DEFAULT_VAR_TYPE,
        default: str = "",
        logging: str = DEFAULT_LOGGING_OPTION,
    ):
        row = self.vars_table.rowCount()
        self.vars_table.insertRow(row)
        self.vars_table.setItem(row, 0, QTableWidgetItem(name))
        combo = self._make_type_combo(var_type)
        self.vars_table.setCellWidget(row, 1, combo)
        self.vars_table.setItem(row, 2, QTableWidgetItem(default))
        logging_combo = self._make_logging_combo(logging)
        self.vars_table.setCellWidget(row, 3, logging_combo)
        btn = self._make_delete_button(self.vars_table)
        btn.clicked.connect(lambda _, b=btn: self.remove_variable_row(b))
        self.vars_table.setCellWidget(row, 4, btn)

    def _make_type_combo(self, current: str | None = None):
        combo = QComboBox()
        combo.addItems(VAR_TYPE_OPTIONS)
        if current in VAR_TYPE_OPTIONS:
            combo.setCurrentText(current)
        else:
            combo.setCurrentText(DEFAULT_VAR_TYPE)
        return combo


    def _make_logging_combo(self, current: str | None = None):
        combo = QComboBox()
        combo.addItems(AGENT_LOGGING_OPTIONS)
        if current in AGENT_LOGGING_OPTIONS:
            combo.setCurrentText(current)
        else:
            combo.setCurrentText(DEFAULT_LOGGING_OPTION)
        return combo


    def remove_variable_row(self, button):
        self._remove_table_row(self.vars_table, button)

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
        btn = self._make_delete_button(self.funcs_table)
        btn.clicked.connect(lambda _, b=btn: self.remove_function_row(b))
        self.funcs_table.setCellWidget(row, 4, btn)

    def remove_function_row(self, button):
        self._remove_table_row(self.funcs_table, button)

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

    def _register_agent_template(self, agent: AgentType):
        self.agent_templates[agent.name] = agent
        if self.template_combo.findText(agent.name) == -1:
            self.template_combo.addItem(agent.name)

    def _remove_agent_template(self, agent_name: str):
        if agent_name in self.agent_templates:
            del self.agent_templates[agent_name]
        idx = self.template_combo.findText(agent_name)
        if idx != -1:
            self.template_combo.removeItem(idx)
        if self.template_combo.count() == 0:
            self.template_combo.addItem("-- Select Template --")
        self.template_combo.setCurrentIndex(0)

    def set_agents(self, agents: list[AgentType]):
        self.agent_templates = {agent.name: agent for agent in agents}
        self.template_combo.blockSignals(True)
        current = self.template_combo.currentText()
        self.template_combo.clear()
        self.template_combo.addItem("-- Select Template --")
        for name in sorted(self.agent_templates.keys()):
            self.template_combo.addItem(name)
        if current and self.template_combo.findText(current) != -1:
            self.template_combo.setCurrentText(current)
        else:
            self.template_combo.setCurrentIndex(0)
        self.template_combo.blockSignals(False)

    # ---------- Template loading ----------
    def load_template(self, template_name):
        if template_name == "-- Select Template --":
            return
        agent = self.agent_templates.get(template_name)
        if not agent:
            return

        self.name_edit.setText("")
        self.color_label.setText(agent.color)
        self.color_label.setStyleSheet(f"background-color: {agent.color}")
        self.selected_color = QColor(agent.color)

        self.vars_table.setRowCount(0)
        for var in agent.variables:
            self.add_variable_row(
                var.name,
                getattr(var, "var_type", DEFAULT_VAR_TYPE),
                var.default,
                getattr(var, "logging", DEFAULT_LOGGING_OPTION),
            )

        self.funcs_table.setRowCount(0)
        for func in agent.functions:
            self.add_function_row()
            row = self.funcs_table.rowCount() - 1
            self.funcs_table.setItem(row, 0, QTableWidgetItem(func.name))
            self.funcs_table.setItem(row, 1, QTableWidgetItem(func.description))
            self.funcs_table.cellWidget(row, 2).setCurrentText(func.input_type)
            self.funcs_table.cellWidget(row, 3).setCurrentText(func.output_type)

    # ---------- Edit mode ----------
    def load_agent_for_edit(self, agent: AgentType):
        """Prefill fields to edit an existing agent."""
        self.edit_mode = True
        self.editing_original_name = agent.name
        self.save_btn.setText("Save Changes")

        self.name_edit.setText(agent.name)
        self.selected_color = QColor(agent.color)
        self.color_label.setText(agent.color)
        self.color_label.setStyleSheet(f"background-color: {agent.color}")

        self.vars_table.setRowCount(0)
        for v in agent.variables:
            self.add_variable_row(
                v.name,
                getattr(v, "var_type", DEFAULT_VAR_TYPE),
                v.default,
                getattr(v, "logging", DEFAULT_LOGGING_OPTION),
            )

        self.funcs_table.setRowCount(0)
        for f in agent.functions:
            self.add_function_row()
            row = self.funcs_table.rowCount() - 1
            self.funcs_table.setItem(row, 0, QTableWidgetItem(f.name))
            self.funcs_table.setItem(row, 1, QTableWidgetItem(f.description))
            self.funcs_table.cellWidget(row, 2).setCurrentText(f.input_type)
            self.funcs_table.cellWidget(row, 3).setCurrentText(f.output_type)

    # ---------- Save ----------
    def save_agent_type(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Agent name cannot be empty")
            return

        variables = []
        for row in range(self.vars_table.rowCount()):
            var_item = self.vars_table.item(row, 0)
            type_combo = self.vars_table.cellWidget(row, 1)
            val_item = self.vars_table.item(row, 2)
            logging_combo = self.vars_table.cellWidget(row, 3)
            if not var_item:
                continue
            var_type = type_combo.currentText() if isinstance(type_combo, QComboBox) else DEFAULT_VAR_TYPE
            logging_value = logging_combo.currentText() if isinstance(logging_combo, QComboBox) else DEFAULT_LOGGING_OPTION
            variables.append(AgentVariable(var_item.text(), val_item.text() if val_item else "", var_type, logging_value))
        functions = []
        for row in range(self.funcs_table.rowCount()):
            fname_item = self.funcs_table.item(row, 0)
            fdesc_item = self.funcs_table.item(row, 1)
            in_combo = self.funcs_table.cellWidget(row, 2)
            out_combo = self.funcs_table.cellWidget(row, 3)
            if not fname_item:
                continue
            functions.append(AgentFunction(
                fname_item.text(),
                fdesc_item.text() if fdesc_item else "",
                in_combo.currentText() if in_combo else "MessageNone",
                out_combo.currentText() if out_combo else "MessageNone"
            ))

        # Default color if none picked: cycle through palette
        if self.selected_color is None:
            idx = len(self.agent_templates) % len(self.default_colors)
            self.selected_color = QColor(self.default_colors[idx])

        color = self.selected_color.name()
        agent = AgentType(name, color, variables, functions)

        if self.edit_mode:
            # If the name changed, remove old key
            if self.editing_original_name and self.editing_original_name in self.agent_templates:
                if self.editing_original_name != name:
                    self.agent_templates.pop(self.editing_original_name, None)
            self.agent_templates[name] = agent
            signals.agent_updated.emit(agent)
            signals.redraw_canvas.emit()
            show_quiet_message(self, "Agent Updated", f"Agent '{name}' updated.")
            self.reset_fields()
        else:
            self.agent_templates[name] = agent
            signals.agent_added.emit(agent)
            signals.redraw_canvas.emit()
            show_quiet_message(self, "Agent Saved", f"Agent '{name}' created.")
            # Add as selectable template for reuse
            if self.template_combo.findText(name) == -1:
                self.template_combo.addItem(name)
            self.reset_fields()
