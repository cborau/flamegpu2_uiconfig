from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QListWidgetItem, QHBoxLayout
from PySide6.QtGui import QColor

class ModelTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Defined Agent Types:"))
        self.agent_list = QListWidget()
        layout.addWidget(self.agent_list)

        self.export_btn = QPushButton("Export Files")
        self.export_btn.clicked.connect(self.export_model)
        layout.addWidget(self.export_btn)

        # Placeholder test data
        self.add_agent("Cell", QColor("red"))
        self.add_agent("Matrix", QColor("green"))

    def add_agent(self, name, color):
        item = QListWidgetItem(name)
        item.setForeground(color)
        self.agent_list.addItem(item)

    def export_model(self):
        print("[Export] Functionality not yet implemented")
