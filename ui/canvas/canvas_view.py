from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from ui.canvas.canvas_scene import CanvasScene
from core.signals import signals

class CanvasView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._scene = CanvasScene()
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints() |
                            QPainter.Antialiasing |
                            QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        signals.adjust_view_requested.connect(self.adjust_view)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    def adjust_view(self):
        r = self.sceneRect()
        if r.isValid():
            self.fitInView(r, Qt.KeepAspectRatio)
