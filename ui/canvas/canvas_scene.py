from typing import Dict, List, Tuple
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene
from core.signals import signals
from core.models import AgentType
from .items import (
    LayerBandItem, AgentNodeItem, FunctionNodeItem, ConnectionItem, AgentConnectionItem,
    AGENT_R, BAND_PAD, H_SPACING
)


class CanvasScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 4000, 3000)

        # Data caches
        self._agents_by_name: Dict[str, AgentType] = {}
        self._layers: List[Dict] = []  # [{"name": str, "functions": [ "Agent::Func", ... ]}, ...]

        # Graphics indexes
        self._bands: List[LayerBandItem] = []
        self._agent_items: Dict[Tuple[str, str], AgentNodeItem] = {}    # (layer_name, agent_name) -> item
        self._func_items: Dict[str, List[FunctionNodeItem]] = {}         # "Agent::Func" -> [items]
        self._connections: List[ConnectionItem] = []
        self._agent_connections: List[AgentConnectionItem] = []
        self._connection_specs: List[dict] = []
        self._connection_keys = set()
        self._connections_need_sync = False

        # Drag-wire state
        self._drag_src: FunctionNodeItem | None = None
        self._drag_temp: ConnectionItem | None = None

        # Manual layout state
        self.manual_mode = False
        self._edges_by_func: dict[FunctionNodeItem, list[ConnectionItem]] = {}
        self._edges_by_agent: dict[AgentNodeItem, list[AgentConnectionItem]] = {}

        # Listen to app state
        signals.agent_added.connect(self._add_or_update_agent)
        signals.agent_updated.connect(self._add_or_update_agent)
        signals.agent_removed.connect(self._remove_agent)
        signals.layers_changed.connect(self._set_layers)
        signals.redraw_canvas.connect(self.rebuild)
        signals.adjust_view_requested.connect(self.fit_whole_scene)
        signals.manual_layout_toggled.connect(self._set_manual_mode)

    # ----- Public helpers -----------------------------------------------------
    def fit_whole_scene(self):
        # The QGraphicsView handles fitInView via a slot. Nothing to do here.
        pass

    # ----- Signals handlers ---------------------------------------------------
    def _set_manual_mode(self, enabled: bool):
        self.manual_mode = enabled
        # toggle movability of nodes
        for (_, _), ag_item in self._agent_items.items():
            ag_item.set_movable(enabled)
        for items in self._func_items.values():
            for fn_item in items:
                fn_item.set_movable(enabled)
        # when turning OFF, snap back to auto layout
        if not enabled:
            self.rebuild()

    def _add_or_update_agent(self, a: AgentType):
        self._agents_by_name[a.name] = a
        self.rebuild()

    def _remove_agent(self, name: str):
        if name in self._agents_by_name:
            del self._agents_by_name[name]
        # purge any functions in layers referencing this agent
        for L in self._layers:
            L["functions"] = [f for f in L["functions"] if not f.startswith(f"{name}::")]
        self.rebuild()

    def _set_layers(self, layers_list: List[Dict]):
        self._layers = layers_list or []
        self.rebuild()

    # ----- Rebuild layout -----------------------------------------------------
    def rebuild(self):
        self.clear()
        self._clear_edge_registry()
        self._bands.clear()
        self._agent_items.clear()
        self._func_items.clear()
        self._connections.clear()
        self._connections_need_sync = True

        if not self._layers:
            return

        # Simple vertical stacking of layer bands
        y = 40.0
        band_h = 220.0
        left, right = 40.0, 3600.0

        for L in self._layers:
            rect = QRectF(left, y, right - left, band_h)
            band = LayerBandItem(L["name"], rect)
            self.addItem(band)
            self._bands.append(band)

            # Which agents are present in this layer?
            funcs = [f for f in L.get("functions", []) if "::" in f]
            agents_here: List[str] = []
            for f in funcs:
                ag_name, _ = f.split("::", 1)
                if ag_name not in agents_here:
                    agents_here.append(ag_name)

            # Horizontal placement of agents
            if agents_here:
                x = rect.left() + BAND_PAD + AGENT_R
                center_y = rect.center().y() - 12.0
                for ag_name in agents_here:
                    ag = self._agents_by_name.get(ag_name)
                    if not ag:
                        continue

                    # Agent circle
                    ag_item = AgentNodeItem(ag_name, QColor(ag.color))
                    ag_item.setPos(QPointF(x, center_y))
                    self.addItem(ag_item)
                    self._agent_items[(L["name"], ag_name)] = ag_item
                    ag_item.set_movable(self.manual_mode)
                    ag_item.on_moved = self._on_agent_moved
                    self._edges_by_agent.setdefault(ag_item, [])

                    # Functions belonging to this agent in this layer
                    f_for_agent = [f for f in funcs if f.startswith(f"{ag_name}::")]

                    # Create all function items first so we know their sizes
                    fn_items: List[FunctionNodeItem] = []
                    for f_id in f_for_agent:
                        f_name = f_id.split("::", 1)[1]
                        f_meta = next((ff for ff in ag.functions if ff.name == f_name), None)
                        if not f_meta:
                            continue
                        fn_item = FunctionNodeItem(ag_name, f_name, f_meta.input_type, f_meta.output_type)
                        self.addItem(fn_item)
                        fn_item.layer_name = L["name"]
                        self._func_items.setdefault(f"{ag_name}::{f_name}", []).append(fn_item)
                        fn_item.on_moved = self._on_func_moved
                        self._edges_by_func.setdefault(fn_item, [])
                        fn_item.set_movable(self.manual_mode)
                        fn_items.append(fn_item)

                    # Position function items to the right, tightly and without overlap
                    if fn_items:
                        # left edge for rectangles clear of the circle
                        base_left = x + AGENT_R + 24.0    # gap from circle
                        total_h = sum(it.rect().height() for it in fn_items) + 6.0 * (len(fn_items) - 1)
                        cur_y = center_y - total_h * 0.5
                        max_w = 0.0
                        for it in fn_items:
                            w = it.rect().width()
                            h = it.rect().height()
                            max_w = max(max_w, w)
                            # set center so that left edge stays at base_left + inner gap
                            inner_gap = 8.0
                            it.setPos(QPointF(base_left + inner_gap + w * 0.5, cur_y + h * 0.5))
                            cur_y += h + 6.0

                        # Draw colored connectors from agent to each function box
                        for it in fn_items:
                            link = AgentConnectionItem(ag_item, it, QColor(ag.color))
                            self.addItem(link)
                            self._agent_connections.append(link)
                            self._edges_by_agent[ag_item].append(link)
                            self._edges_by_func[it].append(link)

                        # Advance x according to the widest function box so we don't collide with next agent
                        x += max(
                            H_SPACING,
                            2 * AGENT_R + 160.0,
                            (AGENT_R + 24.0) + max_w + 200.0
                        )
                    else:
                        x += max(H_SPACING, 2 * AGENT_R + 160.0)

            y += band_h + 30.0

        self._restore_connections_from_specs(force=True)
        # Enable interactive wiring
        self.installEventFilter(self)

    # ----- Interaction: drag-to-connect with type checking -------------------
    def mousePressEvent(self, event):
        if self.manual_mode:
            return super().mousePressEvent(event)
        super().mousePressEvent(event)
        item = self._function_node_at(event.scenePos())
        if item:
            # start drag from this function's output
            self._drag_src = item
            # create a temporary connection to follow the mouse
            self._drag_temp = ConnectionItem(item, item)
            self.addItem(self._drag_temp)

    def mouseMoveEvent(self, event):
        if self._drag_temp and self._drag_src:
            # update temp path to current mouse as 'dst'
            fake_dst = type(self._drag_src)(
                self._drag_src.owner_agent, self._drag_src.func_name,
                self._drag_src.in_type, self._drag_src.out_type
            )
            fake_dst.setPos(event.scenePos())
            self._drag_temp.dst = fake_dst
            self._drag_temp._rebuild_path()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_src and self._drag_temp:
            # resolve drop target
            drop_item = self._function_node_at(event.scenePos())
            if drop_item and drop_item is not self._drag_src:
                # Validate types: src.out == dst.in
                if self._drag_src.out_type == drop_item.in_type:
                    self._create_connection_between(
                        self._drag_src,
                        drop_item,
                        self._drag_src.out_type,
                        emit_signal=True
                    )
                else:
                    # (optional) visual feedback on type mismatch
                    pass
            # cleanup temp
            self.removeItem(self._drag_temp)
            self._drag_temp = None
            self._drag_src = None
        super().mouseReleaseEvent(event)

    # Delete selected connections with Delete key
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for it in list(self.selectedItems()):
                if isinstance(it, ConnectionItem):
                    self._remove_connection(it, emit_signal=True)
        super().keyPressEvent(event)

    # ----- Edge maintenance ---------------------------------------------------
    def _on_func_moved(self, fn_item: FunctionNodeItem):
        for edge in self._edges_by_func.get(fn_item, []):
            edge._rebuild_path()

    def _on_agent_moved(self, agent_item: AgentNodeItem):
        for edge in self._edges_by_agent.get(agent_item, []):
            edge._rebuild_path()

    def _clear_edge_registry(self):
        self._edges_by_func.clear()
        self._edges_by_agent.clear()
        self._agent_connections.clear()

    def _function_node_at(self, pos: QPointF) -> FunctionNodeItem | None:
        if not self.views():
            return None
        item = self.itemAt(pos, self.views()[0].transform())
        while item and not isinstance(item, FunctionNodeItem):
            item = item.parentItem()
        return item if isinstance(item, FunctionNodeItem) else None

    def _find_function_item(self, func_id: str, layer_name: str | None):
        items = self._func_items.get(func_id, [])
        if not items:
            return None
        if layer_name:
            for item in items:
                if getattr(item, "layer_name", None) == layer_name:
                    return item
        return items[0]

    def _make_conn_key(self, spec: dict):
        return (
            spec.get("src"),
            spec.get("dst"),
            spec.get("type", "MessageNone"),
            spec.get("src_layer"),
            spec.get("dst_layer"),
        )

    def _normalize_spec(self, spec: dict, copy: bool = True):
        if not spec:
            return None
        src = spec.get("src")
        dst = spec.get("dst")
        if not src or not dst:
            return None
        norm = dict(spec) if copy else spec
        norm["src"] = src
        norm["dst"] = dst
        norm["type"] = spec.get("type", "MessageNone")
        norm["src_layer"] = spec.get("src_layer", spec.get("layer"))
        norm["dst_layer"] = spec.get("dst_layer", spec.get("layer"))
        return norm

    def _create_connection_between(
        self,
        src_item: FunctionNodeItem,
        dst_item: FunctionNodeItem,
        conn_type: str,
        spec: dict | None = None,
        record: bool = True,
        emit_signal: bool = False,
    ) -> bool:
        if spec is None:
            spec = self._normalize_spec({
                "src": src_item.id_str,
                "dst": dst_item.id_str,
                "type": conn_type,
                "src_layer": getattr(src_item, "layer_name", None),
                "dst_layer": getattr(dst_item, "layer_name", None),
            })
        else:
            spec = self._normalize_spec(spec, copy=record)
        if not spec:
            return False
        key = self._make_conn_key(spec)
        if record and key in self._connection_keys:
            return False

        conn = ConnectionItem(src_item, dst_item, spec.get("type", "MessageNone"))
        conn.spec = spec
        conn.key = key
        self.addItem(conn)
        self._connections.append(conn)
        self._edges_by_func.setdefault(src_item, []).append(conn)
        self._edges_by_func.setdefault(dst_item, []).append(conn)
        self._connection_keys.add(key)
        if record:
            self._connection_specs.append(spec)
        if emit_signal:
            signals.connection_added.emit(spec)
        self._connections_need_sync = False
        return True

    def _detach_connection_item(self, conn: ConnectionItem):
        if conn in self._connections:
            self._connections.remove(conn)
        edges = self._edges_by_func.get(conn.src)
        if edges and conn in edges:
            edges.remove(conn)
            if not edges:
                del self._edges_by_func[conn.src]
        edges = self._edges_by_func.get(conn.dst)
        if edges and conn in edges:
            edges.remove(conn)
            if not edges:
                del self._edges_by_func[conn.dst]
        if conn.scene() is self:
            self.removeItem(conn)

    def _remove_connection(self, conn: ConnectionItem, emit_signal: bool = False):
        spec = getattr(conn, "spec", None)
        key = getattr(conn, "key", None)
        self._detach_connection_item(conn)
        if key is not None:
            self._connection_keys.discard(key)
        if spec and spec in self._connection_specs:
            self._connection_specs.remove(spec)
        if emit_signal and spec:
            signals.connection_removed.emit(spec)
        self._connections_need_sync = False

    def _remove_all_manual_connections(self):
        for conn in list(self._connections):
            self._detach_connection_item(conn)
        self._connections.clear()

    def _restore_connections_from_specs(self, force: bool = False):
        if not self._connection_specs:
            self._connection_keys = set()
            self._connections_need_sync = False
            return
        if not force and not self._connections_need_sync:
            return
        if not self._func_items:
            self._connections_need_sync = True
            return

        specs_snapshot = list(self._connection_specs)
        self._remove_all_manual_connections()
        self._connection_keys = set()
        restored_specs = []
        for spec in specs_snapshot:
            src_item = self._find_function_item(spec.get("src"), spec.get("src_layer"))
            dst_item = self._find_function_item(spec.get("dst"), spec.get("dst_layer"))
            if not src_item or not dst_item:
                continue
            self._create_connection_between(
                src_item,
                dst_item,
                spec.get("type", "MessageNone"),
                spec=spec,
                record=False,
                emit_signal=False,
            )
            restored_specs.append(spec)

        self._connection_specs = restored_specs
        self._connections_need_sync = False

    def get_connections(self) -> list[dict]:
        return [dict(spec) for spec in self._connection_specs]

    def set_connections(self, specs: list[dict]):
        normalized: List[dict] = []
        keys = set()
        for spec in specs or []:
            norm = self._normalize_spec(spec)
            if not norm:
                continue
            key = self._make_conn_key(norm)
            if key in keys:
                continue
            normalized.append(norm)
            keys.add(key)

        self._connection_specs = normalized
        self._connection_keys = set()
        self._connections_need_sync = True
        self._remove_all_manual_connections()
        self._restore_connections_from_specs(force=True)
