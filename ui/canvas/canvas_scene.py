from PySide6.QtWidgets import QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import QPointF
from core.signals import signals
from core.models import AgentType

class CanvasScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 2000, 2000)
        self.agents = []

        signals.agent_added.connect(self.add_or_replace_agent)
        signals.agent_updated.connect(self.add_or_replace_agent)
        signals.agent_removed.connect(self.remove_agent)
        signals.redraw_canvas.connect(self.redraw)

    def add_or_replace_agent(self, agent: AgentType):
        for i, a in enumerate(self.agents):
            if a.name == agent.name:
                self.agents[i] = agent
                break
        else:
            self.agents.append(agent)
        self.redraw()

    def remove_agent(self, agent_name: str):
        self.agents = [a for a in self.agents if a.name != agent_name]
        self.redraw()

    def redraw(self):
        self.clear()
        x, y = 80, 80
        for agent in self.agents:
            self.draw_agent(agent.name, QColor(agent.color), x, y)
            y += 120

    def draw_agent(self, name, color, x, y):
        circle = QGraphicsEllipseItem(x, y, 40, 40)
        circle.setBrush(QBrush(color))
        self.addItem(circle)

        label = QGraphicsTextItem(name)
        label.setPos(QPointF(x, y + 45))
        self.addItem(label)
