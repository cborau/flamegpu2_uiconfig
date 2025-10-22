from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from ui.canvas.canvas_scene import CanvasScene

class CanvasView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(CanvasScene())
        self.setRenderHints(self.renderHints() |
                            QPainter.Antialiasing |
                            QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)
