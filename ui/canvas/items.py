from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QPolygonF
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QPainter, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QPainter

PORT_R = 5.0
AGENT_R = 24.0
FUNC_W, FUNC_H = 120.0, 36.0
BAND_PAD = 16.0
H_SPACING = 80.0
F_SPACING = 28.0

class LayerBandItem(QGraphicsRectItem):
    def __init__(self, name: str, rect: QRectF):
        super().__init__(rect)
        self.setZValue(-10)
        self.setBrush(QBrush(QColor(255, 255, 255, 12)))
        self.setPen(QPen(QColor(200, 200, 200, 80), 1, Qt.DashLine))
        self.label = QGraphicsSimpleTextItem(name, self)
        self.label.setBrush(QBrush(Qt.white))
        self.label.setPos(rect.left() + 8.0, rect.top() + 4.0)

class AgentNodeItem(QGraphicsItem):
    def __init__(self, name: str, color: QColor):
        super().__init__()
        self.name = name
        self.color = color
        self._rect = QRectF(-AGENT_R, -AGENT_R, 2*AGENT_R, 2*AGENT_R)
        self.label = QGraphicsSimpleTextItem(name, self)
        self.label.setBrush(QBrush(Qt.white))
        self.label.setPos(-AGENT_R, AGENT_R + 6)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        r = self._rect.adjusted(-3, -3, 3, 18)
        return r

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(self.color))
        pen = QPen(Qt.black if not self.isSelected() else QColor("#00D1FF"), 2)
        p.setPen(pen)
        p.drawEllipse(self._rect)
    
    def set_movable(self, flag: bool):
        self.setFlag(QGraphicsItem.ItemIsMovable, flag)


class FunctionNodeItem(QGraphicsRectItem):
    """Rectangle with auto-sized box, ports and type metadata for validation."""
    def __init__(self, owner_agent: str, func_name: str, in_type: str, out_type: str):
        # start with a minimal rect, we’ll resize to label
        super().__init__(-40, -16, 80, 32)
        self.owner_agent = owner_agent
        self.func_name = func_name
        self.in_type = in_type
        self.out_type = out_type

        self.setBrush(QBrush(QColor(255, 255, 255, 28)))
        self.setPen(QPen(QColor(140, 140, 140), 1.2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

        self.label = QGraphicsSimpleTextItem(f"{func_name}", self)
        self.label.setBrush(QBrush(Qt.white))
        self.label.setPos(-35, -10)  # temporary, will be repositioned
        self.setToolTip(f"{owner_agent}::{func_name}\nInput: {in_type}\nOutput: {out_type}")

        # resize box to fit text tightly
        self._autosize()

        # hook for the scene to update connected edges when we move
        self.on_moved = None
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    @property
    def id_str(self) -> str:
        return f"{self.owner_agent}::{self.func_name}"

    def _autosize(self):
        br = self.label.boundingRect()
        pad_x, pad_y = 12.0, 8.0
        w = max(64.0, br.width() + 2 * pad_x)
        h = max(24.0, br.height() + 2 * pad_y)
        self.setRect(-w / 2, -h / 2, w, h)
        # re-center label
        self.label.setPos(-br.width() / 2, -br.height() / 2)

    def port_pos_in(self) -> QPointF:
        r = self.rect()
        return self.mapToScene(QPointF(r.left(), 0.0))

    def port_pos_out(self) -> QPointF:
        r = self.rect()
        return self.mapToScene(QPointF(r.right(), 0.0))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.on_moved:
            self.on_moved(self)
        return super().itemChange(change, value)

    def set_movable(self, flag: bool):
        self.setFlag(QGraphicsItem.ItemIsMovable, flag)


class ConnectionItem(QGraphicsPathItem):
    """Bezier-ish curved arrow from src.func out-port to dst.func in-port."""
    def __init__(self, src_item: FunctionNodeItem, dst_item: FunctionNodeItem):
        super().__init__()
        self.src = src_item
        self.dst = dst_item
        self.setZValue(-1)
        self.setPen(QPen(QColor("#8ad"), 2.0))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self._rebuild_path()

    def _rebuild_path(self):
        p0 = self.src.port_pos_out()
        p1 = self.dst.port_pos_in()
        dx = max(40.0, 0.5 * (p1.x() - p0.x()))
        c0 = QPointF(p0.x() + dx, p0.y())
        c1 = QPointF(p1.x() - dx, p1.y())

        path = QPainterPath(p0)
        path.cubicTo(c0, c1, p1)
        self.setPath(path)

    def paint(self, p, opt, widget=None):
        # Base path
        super().paint(p, opt, widget)
        # Arrowhead at end
        path = self.path()
        end = path.pointAtPercent(1.0)
        t = path.percentAtLength(path.length() - 1.0)
        prev = path.pointAtPercent(max(0.0, t))
        v = (end - prev)
        if v.manhattanLength() > 0.0001:
            v /= (v.manhattanLength())
        # simple triangular arrow
        left = QPointF(-v.y(), v.x())
        s = 8.0
        a = end
        b = end - v * s + left * (s*0.6)
        c = end - v * s - left * (s*0.6)
        arrow_poly = QPolygonF([a, b, c])
        p.setBrush(QBrush(QColor("#8ad")))
        p.drawPolygon(arrow_poly)
