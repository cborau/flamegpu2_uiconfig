from PySide6.QtWidgets import QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem
from PySide6.QtGui import QColor, QBrush

class CanvasScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 2000, 2000)

        # Temporary demo agent drawing
        self.draw_agent("Agent1", QColor("red"), 100, 100)
        self.draw_agent("Agent2", QColor("green"), 300, 100)

    def draw_agent(self, name, color, x, y):
        circle = QGraphicsEllipseItem(x, y, 40, 40)
        circle.setBrush(QBrush(color))
        self.addItem(circle)

        label = QGraphicsTextItem(name)
        label.setPos(x, y + 45)
        self.addItem(label)
