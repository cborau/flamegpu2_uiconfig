from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QListWidgetItem,
    QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QComboBox, QHeaderView
)
from PySide6.QtGui import QColor
from core.signals import signals
from core.models import (
    AgentType,
    AgentVariable,
    AgentFunction,
    VAR_TYPE_OPTIONS,
    DEFAULT_VAR_TYPE,
    AGENT_LOGGING_OPTIONS,
    DEFAULT_LOGGING_OPTION,
)
from core.ui_helpers import show_quiet_message
from copy import deepcopy

class ModelTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Defined Agent Types:"))
        self.agent_list = QListWidget()
        self.agent_list.currentRowChanged.connect(self._on_select_agent)
        layout.addWidget(self.agent_list)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_edit = QPushButton("Edit in Agent Config")
        self.btn_remove = QPushButton("Remove Agent")
        self.btn_apply = QPushButton("Apply Table Edits")
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_apply)
        layout.addLayout(btn_row)

        # Summary tables
        layout.addWidget(QLabel("Variables of Selected Agent:"))
        self.vars_table = QTableWidget(0, 4)
        self.vars_table.setHorizontalHeaderLabels(["Variable", "Type", "Default Value", "Logging"])
        self.vars_table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.vars_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.vars_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.vars_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.vars_table)

        layout.addWidget(QLabel("Functions of Selected Agent:"))
        self.funcs_table = QTableWidget(0, 4)
        self.funcs_table.setHorizontalHeaderLabels(["Name", "Input", "Output", "Description"])
        self.funcs_table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        layout.addWidget(self.funcs_table)

        self.export_btn = QPushButton("Export Files")
        self.export_btn.clicked.connect(self.export_model)
        layout.addWidget(self.export_btn)

        # Store
        self.agents = []
        signals.agent_added.connect(self.add_agent)
        signals.agent_updated.connect(self.update_agent)
        signals.agent_removed.connect(self.remove_agent)

        # Button actions
        self.btn_edit.clicked.connect(self._edit_selected_agent)
        self.btn_remove.clicked.connect(self._remove_selected_agent)
        self.btn_apply.clicked.connect(self._apply_table_edits)

    # ------- Agent list management -------
    def add_agent(self, agent: AgentType):
        # replace if same name exists
        for i, a in enumerate(self.agents):
            if a.name == agent.name:
                self.agents[i] = agent
                break
        else:
            self.agents.append(agent)
        self.refresh_list()

    def update_agent(self, agent: AgentType):
        for i, ag in enumerate(self.agents):
            if ag.name == agent.name:
                self.agents[i] = agent
                break
        else:
            self.agents.append(agent)
        self.refresh_list()
        self._on_select_agent(self.agent_list.currentRow())

    def remove_agent(self, agent_name: str):
        self.agents = [a for a in self.agents if a.name != agent_name]
        self.refresh_list()
        self.vars_table.setRowCount(0)
        self.funcs_table.setRowCount(0)
        if self.agents:
            self.agent_list.setCurrentRow(0)

    def refresh_list(self):
        self.agent_list.clear()
        for agent in self.agents:
            item = QListWidgetItem(agent.name)
            item.setForeground(QColor(agent.color))
            self.agent_list.addItem(item)

    # ------- Selection & summary -------
    def _on_select_agent(self, row: int):
        if row < 0 or row >= len(self.agents):
            self.vars_table.setRowCount(0)
            self.funcs_table.setRowCount(0)
            return
        agent = self.agents[row]
        # Variables
        self.vars_table.setRowCount(0)
        for v in agent.variables:
            r = self.vars_table.rowCount()
            self.vars_table.insertRow(r)
            self.vars_table.setItem(r, 0, QTableWidgetItem(v.name))
            combo = self._make_type_combo(getattr(v, "var_type", DEFAULT_VAR_TYPE))
            self.vars_table.setCellWidget(r, 1, combo)
            self.vars_table.setItem(r, 2, QTableWidgetItem(v.default))
            logging_combo = self._make_logging_combo(getattr(v, "logging", DEFAULT_LOGGING_OPTION))
            self.vars_table.setCellWidget(r, 3, logging_combo)
        # Functions
        self.funcs_table.setRowCount(0)
        for f in agent.functions:
            r = self.funcs_table.rowCount()
            self.funcs_table.insertRow(r)
            self.funcs_table.setItem(r, 0, QTableWidgetItem(f.name))
            self.funcs_table.setItem(r, 1, QTableWidgetItem(f.input_type))
            self.funcs_table.setItem(r, 2, QTableWidgetItem(f.output_type))
            self.funcs_table.setItem(r, 3, QTableWidgetItem(f.description))

    # ------- Actions -------
    def _current_agent(self):
        row = self.agent_list.currentRow()
        if row < 0 or row >= len(self.agents):
            return None
        return self.agents[row]

    def _edit_selected_agent(self):
        agent = self._current_agent()
        if not agent:
            return
        signals.request_edit_agent.emit(agent)

    def _remove_selected_agent(self):
        agent = self._current_agent()
        if not agent:
            return
        ok = QMessageBox.question(self, "Remove Agent",
                                  f"Remove agent '{agent.name}'?",
                                  QMessageBox.Yes | QMessageBox.No,
                                  QMessageBox.No)
        if ok == QMessageBox.Yes:
            signals.agent_removed.emit(agent.name)

    def _apply_table_edits(self):
        agent = self._current_agent()
        if not agent:
            return
        # read back from tables into a new AgentType
        new_vars = []
        for r in range(self.vars_table.rowCount()):
            name_item = self.vars_table.item(r, 0)
            type_combo = self.vars_table.cellWidget(r, 1)
            val_item  = self.vars_table.item(r, 2)
            logging_combo = self.vars_table.cellWidget(r, 3)
            if not name_item:
                continue
            var_type = type_combo.currentText() if isinstance(type_combo, QComboBox) else DEFAULT_VAR_TYPE
            logging_value = logging_combo.currentText() if isinstance(logging_combo, QComboBox) else DEFAULT_LOGGING_OPTION
            new_vars.append(AgentVariable(name_item.text(), val_item.text() if val_item else "", var_type, logging_value))

        new_funcs = []
        for r in range(self.funcs_table.rowCount()):
            n = self.funcs_table.item(r, 0)
            i = self.funcs_table.item(r, 1)
            o = self.funcs_table.item(r, 2)
            d = self.funcs_table.item(r, 3)
            if not n:
                continue
            new_funcs.append(AgentFunction(
                n.text(),
                d.text() if d else "",
                i.text() if i else "MessageNone",
                o.text() if o else "MessageNone"
            ))

        updated = AgentType(agent.name, agent.color, new_vars, new_funcs)
        signals.agent_updated.emit(updated)
        show_quiet_message(self, "Updated", f"Edits applied to '{agent.name}'.")

    def export_model(self):
        signals.request_export_model.emit()

    # ------- Persistence helpers -------
    def get_agents(self):
        return deepcopy(self.agents)

    def clear_agents(self):
        self.agents = []
        self.agent_list.clear()
        self.vars_table.setRowCount(0)
        self.funcs_table.setRowCount(0)

    def load_agents(self, agents):
        self.agents = deepcopy(agents)
        self.refresh_list()
        if self.agents:
            self.agent_list.setCurrentRow(0)
        else:
            self.agent_list.setCurrentRow(-1)

    def replace_agents(self, agents):
        self.clear_agents()
        self.load_agents(agents)

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
