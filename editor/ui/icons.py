"""Ícones desenhados por código com QPainter (sem ficheiros de imagem)."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

FG = QColor("#E6E8EE")
ACC = QColor("#5B8FFF")
RED = QColor("#FF6B6B")
_cache: dict[str, QIcon] = {}


def _pen(p: QPainter, color=FG, w: float = 1.8) -> None:
    pen = QPen(color, w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _poly(points) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in points])


def _star(cx, cy, r, inner, n=5):
    pts = []
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * inner
        a = -math.pi / 2 + math.pi * i / n
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _arrow_head(p, x, y, ang_deg, size=4.0):
    a = math.radians(ang_deg)
    for s in (-1, 1):
        b = a + math.pi + s * math.radians(35)
        p.drawLine(QPointF(x, y), QPointF(x + size * math.cos(b), y + size * math.sin(b)))


def _draw(name: str, p: QPainter) -> None:  # noqa: C901 (lista de ícones)
    _pen(p)
    if name == "select":
        p.setBrush(FG)
        p.drawPolygon(_poly([(6, 3), (6, 19), (10, 15.2), (12.8, 21), (15.4, 19.8), (12.6, 14), (18, 14)]))
    elif name == "hand":
        for (x0, y0, x1, y1) in ((12, 3, 12, 21), (3, 12, 21, 12)):
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        _arrow_head(p, 12, 3, -90)
        _arrow_head(p, 12, 21, 90)
        _arrow_head(p, 3, 12, 180)
        _arrow_head(p, 21, 12, 0)
    elif name == "rect":
        p.drawRoundedRect(QRectF(4, 6, 16, 12), 1.5, 1.5)
    elif name == "ellipse":
        p.drawEllipse(QRectF(3.5, 6, 17, 12))
    elif name == "triangle":
        p.drawPolygon(_poly([(12, 4.5), (20.5, 19), (3.5, 19)]))
    elif name == "line":
        p.drawLine(QPointF(5, 19), QPointF(19, 5))
        p.setBrush(FG)
        p.drawEllipse(QPointF(5, 19), 1.8, 1.8)
        p.drawEllipse(QPointF(19, 5), 1.8, 1.8)
    elif name == "polygon":
        pts = [(4, 9), (14, 4), (20, 12), (12, 13), (9, 20)]
        p.drawPolygon(_poly(pts))
        p.setBrush(ACC)
        p.setPen(Qt.PenStyle.NoPen)
        for x, y in pts:
            p.drawEllipse(QPointF(x, y), 1.5, 1.5)
    elif name == "freehand":
        path = QPainterPath(QPointF(3, 16))
        path.cubicTo(QPointF(7, 4), QPointF(10, 22), QPointF(14, 12))
        path.cubicTo(QPointF(16, 7), QPointF(19, 9), QPointF(21, 6))
        p.drawPath(path)
    elif name == "ngon":
        p.drawPolygon(_poly([(12 + 8.5 * math.cos(math.radians(90 + 60 * i)),
                              12 - 8.5 * math.sin(math.radians(90 + 60 * i))) for i in range(6)]))
    elif name == "star":
        p.drawPolygon(_poly(_star(12, 12.8, 9.5, 0.45)))
    elif name == "image":
        p.drawRoundedRect(QRectF(3.5, 5, 17, 14), 2, 2)
        p.drawPolyline(_poly([(5, 17), (10, 11), (13, 14), (15, 12), (19.5, 17)]))
        p.drawEllipse(QPointF(15.5, 9), 1.6, 1.6)
    elif name == "new":
        p.drawPolyline(_poly([(14, 3.5), (6, 3.5), (6, 20.5), (18, 20.5), (18, 7.5), (14, 3.5), (14, 7.5), (18, 7.5)]))
        _pen(p, ACC, 2)
        p.drawLine(QPointF(12, 10.5), QPointF(12, 17))
        p.drawLine(QPointF(8.8, 13.8), QPointF(15.2, 13.8))
    elif name == "open":
        p.drawPolyline(_poly([(3.5, 18.5), (3.5, 6), (9, 6), (11, 8), (19, 8), (19, 10.5)]))
        p.drawPolygon(_poly([(3.5, 18.5), (6.5, 11), (21, 11), (18, 18.5)]))
    elif name == "save":
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
        p.drawRect(QRectF(8, 4, 8, 5))
        p.drawRect(QRectF(7, 13, 10, 7))
    elif name in ("undo", "redo"):
        if name == "redo":
            p.translate(24, 0)
            p.scale(-1, 1)
        path = QPainterPath(QPointF(6, 10))
        path.cubicTo(QPointF(10, 5.5), QPointF(20, 6), QPointF(19, 14))
        path.cubicTo(QPointF(18.5, 18), QPointF(15, 19.5), QPointF(12, 19.5))
        p.drawPath(path)
        p.drawPolyline(_poly([(6, 4.5), (6, 10), (11.5, 10)]))
    elif name == "group":
        _pen(p, FG, 1.2)
        p.setPen(QPen(FG, 1.2, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(2.5, 2.5, 19, 19))
        _pen(p)
        p.drawRect(QRectF(5.5, 5.5, 8, 8))
        p.setBrush(ACC)
        p.drawEllipse(QRectF(10.5, 10.5, 8, 8))
    elif name == "ungroup":
        p.drawRect(QRectF(3, 3, 8, 8))
        p.setBrush(ACC)
        p.drawEllipse(QRectF(13, 13, 8, 8))
    elif name in ("front", "back"):
        a, b = QRectF(3.5, 3.5, 11, 11), QRectF(9.5, 9.5, 11, 11)
        if name == "front":
            p.drawRect(a)
            p.setBrush(ACC)
            p.drawRect(b)
        else:
            p.setBrush(ACC)
            p.drawRect(a)
            p.setBrush(QColor("#2E323A"))
            p.drawRect(b)
    elif name == "flip_h":
        p.setPen(QPen(FG, 1.2, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(12, 3), QPointF(12, 21))
        _pen(p)
        p.drawPolygon(_poly([(10, 6), (10, 18), (3, 18)]))
        p.setBrush(ACC)
        p.drawPolygon(_poly([(14, 6), (14, 18), (21, 18)]))
    elif name == "flip_v":
        p.setPen(QPen(FG, 1.2, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(3, 12), QPointF(21, 12))
        _pen(p)
        p.drawPolygon(_poly([(6, 10), (18, 10), (18, 3)]))
        p.setBrush(ACC)
        p.drawPolygon(_poly([(6, 14), (18, 14), (18, 21)]))
    elif name == "play":
        p.setBrush(QColor("#4ADE80"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(_poly([(7, 4.5), (19.5, 12), (7, 19.5)]))
    elif name == "stop":
        p.setBrush(RED)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)
    elif name == "export":
        p.drawRoundedRect(QRectF(3.5, 7, 13, 13), 2, 2)
        _pen(p, ACC, 2)
        p.drawLine(QPointF(11, 13), QPointF(20, 4))
        p.drawPolyline(_poly([(14, 4), (20, 4), (20, 10)]))
    elif name == "gif":
        p.drawRoundedRect(QRectF(2.5, 5.5, 19, 13), 2.5, 2.5)
        f = QFont()
        f.setBold(True)
        f.setPixelSize(8)
        p.setFont(f)
        p.drawText(QRectF(2.5, 5.5, 19, 13), Qt.AlignmentFlag.AlignCenter, "GIF")
    elif name == "fit":
        for (x, y, dx, dy) in ((4, 4, 1, 1), (20, 4, -1, 1), (4, 20, 1, -1), (20, 20, -1, -1)):
            p.drawPolyline(_poly([(x, y + 5 * dy), (x, y), (x + 5 * dx, y)]))
        p.drawRect(QRectF(9, 9, 6, 6))
    elif name == "grid":
        _pen(p, FG, 1.4)
        for i in (4, 9.33, 14.66, 20):
            p.drawLine(QPointF(i, 4), QPointF(i, 20))
            p.drawLine(QPointF(4, i), QPointF(20, i))
    elif name == "magnet":
        p.drawArc(QRectF(5, 4, 14, 14), 180 * 16, 180 * 16)
        p.drawLine(QPointF(5, 11), QPointF(5, 5))
        p.drawLine(QPointF(19, 11), QPointF(19, 5))
        _pen(p, ACC, 2.4)
        p.drawLine(QPointF(5, 5), QPointF(5, 7.5))
        p.drawLine(QPointF(19, 5), QPointF(19, 7.5))
    elif name == "minimap":
        p.drawRoundedRect(QRectF(3, 4, 18, 16), 2, 2)
        p.setBrush(ACC)
        p.drawRect(QRectF(12, 12, 7, 6))
    elif name == "aspect":
        p.drawRect(QRectF(3.5, 6.5, 17, 11))
        _pen(p, ACC, 1.6)
        p.drawLine(QPointF(7, 15), QPointF(17, 9))
        _arrow_head(p, 17, 9, -31, 3.5)
        _arrow_head(p, 7, 15, 149, 3.5)
    elif name == "add":
        _pen(p, FG, 2)
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif name == "delete":
        p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5))
        p.drawPolyline(_poly([(9, 6.5), (9.5, 3.5), (14.5, 3.5), (15, 6.5)]))
        p.drawPolyline(_poly([(6, 6.5), (7, 20.5), (17, 20.5), (18, 6.5)]))
        p.drawLine(QPointF(10, 10), QPointF(10, 17))
        p.drawLine(QPointF(14, 10), QPointF(14, 17))
    elif name == "duplicate":
        p.drawRoundedRect(QRectF(4, 4, 11, 11), 1.5, 1.5)
        p.setBrush(QColor("#2E323A"))
        p.drawRoundedRect(QRectF(9, 9, 11, 11), 1.5, 1.5)
    elif name in ("up", "down"):
        if name == "down":
            p.translate(0, 24)
            p.scale(1, -1)
        p.drawLine(QPointF(12, 19), QPointF(12, 5))
        p.drawPolyline(_poly([(6.5, 10.5), (12, 5), (17.5, 10.5)]))
    elif name in ("eye", "eye_off"):
        path = QPainterPath(QPointF(2.5, 12))
        path.quadTo(QPointF(12, 2.5), QPointF(21.5, 12))
        path.quadTo(QPointF(12, 21.5), QPointF(2.5, 12))
        if name == "eye":
            p.drawPath(path)
            p.setBrush(FG)
            p.drawEllipse(QPointF(12, 12), 2.6, 2.6)
        else:
            _pen(p, QColor("#6B7280"))
            p.drawPath(path)
            p.drawLine(QPointF(4, 20), QPointF(20, 4))
    elif name in ("lock", "unlock"):
        color = FG if name == "lock" else QColor("#6B7280")
        _pen(p, color)
        p.drawRoundedRect(QRectF(5.5, 11, 13, 9.5), 2, 2)
        if name == "lock":
            p.drawArc(QRectF(8, 4.5, 8, 12), 0, 180 * 16)
        else:
            p.drawArc(QRectF(11.5, 3.5, 8, 12), 0, 180 * 16)
    elif name == "help":
        p.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        f = QFont()
        f.setBold(True)
        f.setPixelSize(12)
        p.setFont(f)
        p.drawText(QRectF(3.5, 3.5, 17, 17), Qt.AlignmentFlag.AlignCenter, "?")
    elif name == "home":
        p.drawPolyline(_poly([(4, 11.5), (12, 4.5), (20, 11.5)]))
        p.drawPolyline(_poly([(6.5, 10), (6.5, 19.5), (17.5, 19.5), (17.5, 10)]))
    elif name == "layers":
        p.drawPolygon(_poly([(12, 4), (21, 9), (12, 14), (3, 9)]))
        p.drawPolyline(_poly([(3, 13), (12, 18), (21, 13)]))
    elif name == "rotate":
        p.drawArc(QRectF(4.5, 4.5, 15, 15), 30 * 16, 280 * 16)
        _arrow_head(p, 18.5, 8.2, 300, 4)
    elif name == "logo":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#5B8FFF"))
        p.drawPolygon(_poly([(12, 2.5), (21.5, 19.5), (2.5, 19.5)]))
        p.setBrush(QColor("#FFD166"))
        p.drawEllipse(QRectF(11, 10.5, 10, 10))
        p.setBrush(QColor(255, 107, 107, 220))
        p.drawRect(QRectF(3, 11, 8.5, 8.5))


def icon(name: str) -> QIcon:
    if name in _cache:
        return _cache[name]
    ic = QIcon()
    for size in (24, 48, 96):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(size / 24.0, size / 24.0)
        _draw(name, p)
        p.end()
        ic.addPixmap(pm)
    _cache[name] = ic
    return ic


def rotate_cursor() -> QCursor:
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(32 / 24.0, 32 / 24.0)
    _pen(p, QColor("#FFFFFF"), 4.2)
    p.drawArc(QRectF(4.5, 4.5, 15, 15), 30 * 16, 280 * 16)
    _pen(p, QColor("#111111"), 1.8)
    p.drawArc(QRectF(4.5, 4.5, 15, 15), 30 * 16, 280 * 16)
    _arrow_head(p, 18.5, 8.2, 300, 4)
    p.end()
    return QCursor(pm, 16, 16)
