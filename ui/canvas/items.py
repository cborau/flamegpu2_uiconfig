from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsSimpleTextItem

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
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.on_moved = None
        self.layer_name = None

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

    def port_pos_right(self) -> QPointF:
        return self.mapToScene(QPointF(self._rect.right(), 0.0))

    def port_pos_left(self) -> QPointF:
        return self.mapToScene(QPointF(self._rect.left(), 0.0))

    def port_pos_out(self) -> QPointF:
        return self.port_pos_right()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.on_moved:
            self.on_moved(self)
        return super().itemChange(change, value)


class FunctionNodeItem(QGraphicsRectItem):
    """Rectangle with auto-sized box, ports and type metadata for validation."""
    def __init__(self, owner_agent: str, func_name: str, in_type: str, out_type: str):
        # start with a minimal rect, we’ll resize to label
        super().__init__(-40, -16, 80, 32)
        self.owner_agent = owner_agent
        self.func_name = func_name
        self.in_type = in_type
        self.out_type = out_type
        self.layer_name = None

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
        return self.port_pos_left()

    def port_pos_out(self) -> QPointF:
        return self.port_pos_right()

    def port_pos_left(self) -> QPointF:
        r = self.rect()
        return self.mapToScene(QPointF(r.left(), 0.0))

    def port_pos_right(self) -> QPointF:
        r = self.rect()
        return self.mapToScene(QPointF(r.right(), 0.0))

    def port_pos_agent(self) -> QPointF:
        return self.port_pos_left()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.on_moved:
            self.on_moved(self)
        return super().itemChange(change, value)

    def set_movable(self, flag: bool):
        self.setFlag(QGraphicsItem.ItemIsMovable, flag)


class ConnectionItem(QGraphicsPathItem):
    """Bezier-ish curved arrow from src.func out-port to dst.func in-port."""

    def __init__(self, src_item: FunctionNodeItem, dst_item: FunctionNodeItem, message_type: str = "MessageNone"):
        super().__init__()
        self.src = src_item
        self.dst = dst_item
        self.message_type = message_type
        self.setZValue(-1)
        self.setPen(QPen(QColor("#8ad"), 2.0))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self._rebuild_path()

    def _rebuild_path(self):
        src_center = self.src.scenePos()
        dst_center = self.dst.scenePos()

        if self.src is self.dst:
            p0 = self.src.port_pos_right()
            p1 = self.dst.port_pos_right()
            direction = 1.0
        elif src_center.x() <= dst_center.x():
            p0 = self.src.port_pos_right()
            p1 = self.dst.port_pos_left()
            direction = 1.0
        else:
            p0 = self.src.port_pos_left()
            p1 = self.dst.port_pos_right()
            direction = -1.0

        dx = max(60.0, abs(p1.x() - p0.x()) * 0.3)
        dy = (p1.y() - p0.y()) * 0.5
        c0 = QPointF(p0.x() + direction * dx, p0.y() + dy)
        c1 = QPointF(p1.x() - direction * dx, p1.y() - dy)

        path = QPainterPath(p0)
        path.cubicTo(c0, c1, p1)
        self.setPath(path)

    def paint(self, p, opt, widget=None):
        # Base path
        super().paint(p, opt, widget)
        # Arrowhead at end
        path = self.path()
        color = self.pen().color()
        start = path.pointAtPercent(0.0)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(start, 3.5, 3.5)

        if path.length() <= 1.0:
            return
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
        p.setBrush(QBrush(color))
        p.drawPolygon(arrow_poly)


class AgentConnectionItem(QGraphicsPathItem):
    """Arrow linking an agent circle to one of its function rectangles."""

    def __init__(self, agent_item: AgentNodeItem, func_item: FunctionNodeItem, color: QColor):
        super().__init__()
        self.agent = agent_item
        self.func = func_item
        self.color = color
        self.setZValue(-2)
        self.setPen(QPen(color, 2.0))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self._rebuild_path()

    def _rebuild_path(self):
        agent_center = self.agent.scenePos()
        func_center = self.func.scenePos()

        if agent_center.x() <= func_center.x():
            start = self.agent.port_pos_right()
            end = self.func.port_pos_left()
            direction = 1.0
        else:
            start = self.agent.port_pos_left()
            end = self.func.port_pos_right()
            direction = -1.0

        dx = max(40.0, abs(end.x() - start.x()) * 0.5)
        dy = (end.y() - start.y()) * 0.5
        c0 = QPointF(start.x() + direction * dx, start.y() + dy)
        c1 = QPointF(end.x() - direction * dx, end.y() - dy)

        path = QPainterPath(start)
        path.cubicTo(c0, c1, end)
        self.setPath(path)

    def paint(self, p, opt, widget=None):
        super().paint(p, opt, widget)
        path = self.path()
        if path.length() <= 1.0:
            return
        end = path.pointAtPercent(1.0)
        t = path.percentAtLength(path.length() - 1.0)
        prev = path.pointAtPercent(max(0.0, t))
        v = (end - prev)
        if v.manhattanLength() > 0.0001:
            v /= (v.manhattanLength())
        left = QPointF(-v.y(), v.x())
        s = 8.0
        a = end
        b = end - v * s + left * (s * 0.6)
        c = end - v * s - left * (s * 0.6)
        arrow_poly = QPolygonF([a, b, c])
        p.setBrush(QBrush(self.color))
        p.drawPolygon(arrow_poly)
