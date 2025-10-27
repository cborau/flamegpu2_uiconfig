from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from core.models import (
    AgentType,
    VisualizationAgentConfig,
    VisualizationInterpolation,
    VisualizationSettings,
    VISUALIZATION_COLOR_MODES,
    VISUALIZATION_SHAPES,
    DEFAULT_VISUALIZATION_COLOR,
    DEFAULT_VISUALIZATION_SHAPE,
)
from core.signals import signals


class VisualizationTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.agent_definitions: dict[str, AgentType] = {}
        self.agent_configs: dict[str, VisualizationAgentConfig] = {}
        self._block_agent_table = False
        self._block_interpolation_updates = False

        layout = QVBoxLayout(self)

        # General options
        general_group = QGroupBox("General Options")
        general_layout = QVBoxLayout()
        self.activate_checkbox = QCheckBox("Activate Visualization")
        self.activate_checkbox.setChecked(False)
        self.activate_checkbox.toggled.connect(self._on_activation_toggled)
        general_layout.addWidget(self.activate_checkbox)

        self.general_controls_widget = QWidget()
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        domain_row = QHBoxLayout()
        domain_label = QLabel("Domain width")
        self.domain_width_edit = QLineEdit()
        self.domain_width_edit.setPlaceholderText("Enter domain width")
        domain_validator = QDoubleValidator(0.0, 1e12, 3)
        domain_validator.setNotation(QDoubleValidator.StandardNotation)
        self.domain_width_edit.setValidator(domain_validator)
        domain_row.addWidget(domain_label)
        domain_row.addWidget(self.domain_width_edit)
        controls_layout.addLayout(domain_row)

        self.begin_paused_checkbox = QCheckBox("Begin paused")
        controls_layout.addWidget(self.begin_paused_checkbox)

        self.show_boundaries_checkbox = QCheckBox("Show domain boundaries")
        controls_layout.addWidget(self.show_boundaries_checkbox)

        controls_layout.addStretch(1)
        self.general_controls_widget.setLayout(controls_layout)
        general_layout.addWidget(self.general_controls_widget)
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Agent-specific visualization options
        self.agent_group = QGroupBox("Agent Visualization")
        agent_layout = QVBoxLayout()
        self.agent_table = QTableWidget(0, 3)
        self.agent_table.setHorizontalHeaderLabels(["Include agent", "Shape", "Color"])
        self.agent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.agent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.agent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.agent_table.verticalHeader().setVisible(False)
        self.agent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.agent_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.agent_table.itemChanged.connect(self._on_agent_item_changed)
        self.agent_table.itemSelectionChanged.connect(self._on_agent_selection_changed)
        agent_layout.addWidget(self.agent_table)
        self.agent_group.setLayout(agent_layout)
        layout.addWidget(self.agent_group)

        # Interpolation settings
        self.interpolation_group = QGroupBox("Interpolated Color Settings")
        interpolation_layout = QVBoxLayout()
        self.interpolation_placeholder = QLabel("Activate visualization and select an agent with interpolated color to configure settings.")
        self.interpolation_placeholder.setWordWrap(True)
        interpolation_layout.addWidget(self.interpolation_placeholder)

        self.interpolation_table = QTableWidget(0, 3)
        self.interpolation_table.setHorizontalHeaderLabels(["Variable", "Min Value", "Max Value"])
        self.interpolation_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.interpolation_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.interpolation_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.interpolation_table.verticalHeader().setVisible(False)
        interpolation_layout.addWidget(self.interpolation_table)
        self.interpolation_group.setLayout(interpolation_layout)
        layout.addWidget(self.interpolation_group)

        self._apply_activation_state(False)
        self.interpolation_table.setVisible(False)

        # Sync with agent updates
        signals.agent_added.connect(self._on_agent_added)
        signals.agent_updated.connect(self._on_agent_added)
        signals.agent_removed.connect(self._on_agent_removed)

    # ---------- Public API ----------
    def get_settings(self) -> VisualizationSettings:
        agents_settings: list[VisualizationAgentConfig] = []
        for name in sorted(self.agent_definitions.keys()):
            cfg = self.agent_configs.get(name, VisualizationAgentConfig(agent_name=name))
            interpolation = None
            if cfg.interpolation and cfg.color_mode == "Interpolated":
                interpolation = VisualizationInterpolation(
                    variable=cfg.interpolation.variable,
                    min_value=cfg.interpolation.min_value,
                    max_value=cfg.interpolation.max_value,
                )
            agents_settings.append(VisualizationAgentConfig(
                agent_name=name,
                include=cfg.include,
                shape=cfg.shape if cfg.shape in VISUALIZATION_SHAPES else DEFAULT_VISUALIZATION_SHAPE,
                color_mode=cfg.color_mode if cfg.color_mode in VISUALIZATION_COLOR_MODES else DEFAULT_VISUALIZATION_COLOR,
                interpolation=interpolation,
            ))
        return VisualizationSettings(
            activated=self.activate_checkbox.isChecked(),
            domain_width=self.domain_width_edit.text().strip(),
            begin_paused=self.begin_paused_checkbox.isChecked(),
            show_domain_boundaries=self.show_boundaries_checkbox.isChecked(),
            agents=agents_settings,
        )

    def load_config(self, settings: VisualizationSettings | None) -> None:
        if settings is None:
            settings = VisualizationSettings()

        with QSignalBlocker(self.activate_checkbox):
            self.activate_checkbox.setChecked(settings.activated)
        self.begin_paused_checkbox.setChecked(settings.begin_paused)
        self.show_boundaries_checkbox.setChecked(settings.show_domain_boundaries)
        with QSignalBlocker(self.domain_width_edit):
            self.domain_width_edit.setText(settings.domain_width or "")

        # Reset configs for existing agents
        for name in list(self.agent_configs.keys()):
            if name not in self.agent_definitions:
                self.agent_configs.pop(name)
        for name in self.agent_definitions.keys():
            self.agent_configs[name] = VisualizationAgentConfig(agent_name=name)

        for agent_cfg in settings.agents:
            if agent_cfg.agent_name not in self.agent_definitions:
                continue
            cfg = self.agent_configs[agent_cfg.agent_name]
            cfg.include = agent_cfg.include
            cfg.shape = agent_cfg.shape if agent_cfg.shape in VISUALIZATION_SHAPES else DEFAULT_VISUALIZATION_SHAPE
            cfg.color_mode = agent_cfg.color_mode if agent_cfg.color_mode in VISUALIZATION_COLOR_MODES else DEFAULT_VISUALIZATION_COLOR
            if agent_cfg.interpolation and cfg.color_mode == "Interpolated":
                cfg.interpolation = VisualizationInterpolation(
                    variable=agent_cfg.interpolation.variable,
                    min_value=agent_cfg.interpolation.min_value,
                    max_value=agent_cfg.interpolation.max_value,
                )
            else:
                cfg.interpolation = None

        self._apply_activation_state(settings.activated)
        self._refresh_agent_table()
        self._update_interpolation_table()

    # ---------- Activation handling ----------
    def _on_activation_toggled(self, checked: bool) -> None:
        self._apply_activation_state(checked)
        self._update_interpolation_table()

    def _apply_activation_state(self, active: bool) -> None:
        self.general_controls_widget.setEnabled(active)
        self.agent_group.setEnabled(active)
        self.interpolation_group.setEnabled(active)

    # ---------- Agent syncing ----------
    def _on_agent_added(self, agent: AgentType) -> None:
        self.agent_definitions[agent.name] = agent
        cfg = self.agent_configs.setdefault(agent.name, VisualizationAgentConfig(agent_name=agent.name))
        self._ensure_interpolation_valid(agent.name)
        self._refresh_agent_table()
        self._update_interpolation_table()

    def _on_agent_removed(self, agent_name: str) -> None:
        self.agent_definitions.pop(agent_name, None)
        self.agent_configs.pop(agent_name, None)
        self._refresh_agent_table()
        self._update_interpolation_table()

    def _ensure_interpolation_valid(self, agent_name: str) -> None:
        cfg = self.agent_configs.get(agent_name)
        agent = self.agent_definitions.get(agent_name)
        if not cfg or not cfg.interpolation or not agent:
            return
        variables = [var.name for var in agent.variables]
        if not variables:
            cfg.interpolation = None
            return
        if cfg.interpolation.variable not in variables:
            cfg.interpolation.variable = variables[0]

    # ---------- Agent table helpers ----------
    def _refresh_agent_table(self) -> None:
        self._block_agent_table = True
        current = self._current_agent_name()
        self.agent_table.setRowCount(0)

        for row, name in enumerate(sorted(self.agent_definitions.keys())):
            cfg = self.agent_configs.setdefault(name, VisualizationAgentConfig(agent_name=name))
            self.agent_table.insertRow(row)

            include_item = QTableWidgetItem(name)
            include_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            include_item.setCheckState(Qt.Checked if cfg.include else Qt.Unchecked)
            self.agent_table.setItem(row, 0, include_item)

            shape_combo = self._make_shape_combo(cfg.shape, name)
            self.agent_table.setCellWidget(row, 1, shape_combo)

            color_combo = self._make_color_combo(cfg.color_mode, name)
            self.agent_table.setCellWidget(row, 2, color_combo)

        self._block_agent_table = False

        if current:
            self._select_agent_by_name(current)
        if self.agent_table.currentRow() == -1 and self.agent_table.rowCount() > 0:
            self.agent_table.setCurrentCell(0, 0)

    def _select_agent_by_name(self, name: str) -> None:
        for row in range(self.agent_table.rowCount()):
            item = self.agent_table.item(row, 0)
            if item and item.text() == name:
                self.agent_table.setCurrentCell(row, 0)
                return

    def _make_shape_combo(self, current: str, agent_name: str) -> QComboBox:
        combo = QComboBox()
        combo.addItems(VISUALIZATION_SHAPES)
        combo.setCurrentText(current if current in VISUALIZATION_SHAPES else DEFAULT_VISUALIZATION_SHAPE)
        combo.currentTextChanged.connect(partial(self._on_shape_changed, agent_name))
        return combo

    def _make_color_combo(self, current: str, agent_name: str) -> QComboBox:
        combo = QComboBox()
        combo.addItems(VISUALIZATION_COLOR_MODES)
        combo.setCurrentText(current if current in VISUALIZATION_COLOR_MODES else DEFAULT_VISUALIZATION_COLOR)
        combo.currentTextChanged.connect(partial(self._on_color_changed, agent_name))
        return combo

    def _on_agent_item_changed(self, item: QTableWidgetItem) -> None:
        if self._block_agent_table or item.column() != 0:
            return
        cfg = self.agent_configs.get(item.text())
        if cfg:
            cfg.include = item.checkState() == Qt.Checked

    def _on_agent_selection_changed(self) -> None:
        if self._block_agent_table:
            return
        self._update_interpolation_table()

    def _on_shape_changed(self, agent_name: str, value: str) -> None:
        cfg = self.agent_configs.get(agent_name)
        if cfg:
            cfg.shape = value if value in VISUALIZATION_SHAPES else DEFAULT_VISUALIZATION_SHAPE

    def _on_color_changed(self, agent_name: str, value: str) -> None:
        cfg = self.agent_configs.get(agent_name)
        if not cfg:
            return
        cfg.color_mode = value if value in VISUALIZATION_COLOR_MODES else DEFAULT_VISUALIZATION_COLOR
        if cfg.color_mode != "Interpolated":
            cfg.interpolation = None
        self._update_interpolation_table()

    def _current_agent_name(self) -> str | None:
        row = self.agent_table.currentRow()
        if row < 0:
            return None
        item = self.agent_table.item(row, 0)
        return item.text() if item else None

    # ---------- Interpolation helpers ----------
    def _update_interpolation_table(self) -> None:
        active = self.activate_checkbox.isChecked()
        current_name = self._current_agent_name()
        cfg = self.agent_configs.get(current_name) if current_name else None
        agent = self.agent_definitions.get(current_name) if current_name else None

        message = None
        should_show = False

        if not active:
            message = "Activate visualization to edit interpolation settings."
        elif not current_name:
            message = "Select an agent to edit interpolation settings."
        elif not agent:
            message = "Add agents to configure visualization."
        elif cfg is None or cfg.color_mode != "Interpolated":
            message = "Set the agent color to 'Interpolated' to configure variable mapping."
        elif not agent.variables:
            message = "The selected agent has no variables available for interpolation."
        else:
            should_show = True

        if not should_show:
            self.interpolation_placeholder.setText(message or "")
            self.interpolation_placeholder.setVisible(True)
            self.interpolation_table.setVisible(False)
            self._block_interpolation_updates = True
            self.interpolation_table.setRowCount(0)
            self._block_interpolation_updates = False
            return

        cfg.interpolation = cfg.interpolation or VisualizationInterpolation()
        self._ensure_interpolation_valid(current_name)

        self.interpolation_placeholder.setVisible(False)
        self.interpolation_table.setVisible(True)

        self._block_interpolation_updates = True
        self.interpolation_table.setRowCount(1)
        variable_widget = self._make_variable_selector(current_name, agent, cfg.interpolation)
        self.interpolation_table.setCellWidget(0, 0, variable_widget)
        min_widget = self._make_float_edit(cfg.interpolation.min_value, current_name, "min")
        self.interpolation_table.setCellWidget(0, 1, min_widget)
        max_widget = self._make_float_edit(cfg.interpolation.max_value, current_name, "max")
        self.interpolation_table.setCellWidget(0, 2, max_widget)
        self._block_interpolation_updates = False

    def _make_variable_selector(
        self,
        agent_name: str,
        agent: AgentType,
        interpolation: VisualizationInterpolation,
    ) -> QComboBox:
        combo = QComboBox()
        variable_names = [var.name for var in agent.variables]
        combo.addItems(variable_names)
        if variable_names:
            if interpolation.variable in variable_names:
                combo.setCurrentText(interpolation.variable)
            else:
                combo.setCurrentIndex(0)
                interpolation.variable = variable_names[0]
        combo.currentTextChanged.connect(partial(self._on_interpolation_variable_changed, agent_name))
        return combo

    def _make_float_edit(self, value: float, agent_name: str, bound: str) -> QLineEdit:
        edit = QLineEdit()
        validator = QDoubleValidator(-1e12, 1e12, 6)
        validator.setNotation(QDoubleValidator.StandardNotation)
        edit.setValidator(validator)
        edit.setText(self._format_float(value))
        edit.editingFinished.connect(lambda name=agent_name, field=bound, widget=edit: self._on_interpolation_bounds_changed(name, field, widget.text()))
        return edit

    def _on_interpolation_variable_changed(self, agent_name: str, value: str) -> None:
        if self._block_interpolation_updates:
            return
        cfg = self.agent_configs.get(agent_name)
        if cfg and cfg.interpolation:
            cfg.interpolation.variable = value

    def _on_interpolation_bounds_changed(self, agent_name: str, bound: str, text: str) -> None:
        if self._block_interpolation_updates:
            return
        cfg = self.agent_configs.get(agent_name)
        if not cfg or not cfg.interpolation:
            return
        value = self._parse_float(text, 0.0 if bound == "min" else 1.0)
        if bound == "min":
            cfg.interpolation.min_value = value
        else:
            cfg.interpolation.max_value = value

    @staticmethod
    def _parse_float(value: str, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _format_float(value: float) -> str:
        return f"{value:.6g}"