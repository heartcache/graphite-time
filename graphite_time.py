# -*- coding: utf-8 -*-
"""
Graphite Time — a minimalist focus timer with tasks, goals, profile and 6 languages.
© heartcache
Запуск:  pip install PySide6   →   python graphite_time.py
Иконка:  python graphite_time.py --make-icon
Сборка:  pyinstaller --noconsole --onefile --name "Graphite Time" --icon app.ico graphite_time.py
"""
from __future__ import annotations

import json, math, os, sys, time, uuid, threading, wave, array
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve, QEvent, QObject, QParallelAnimationGroup,
                            QPoint, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, Property, Signal, QLocale, QUrl)
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF, QIcon, QKeySequence, QLinearGradient,
                           QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF, QRadialGradient, QShortcut, QConicalGradient, QDesktopServices, QImage, QGuiApplication, QIntValidator)
from PySide6.QtWidgets import (QApplication, QGraphicsOpacityEffect, QLabel, QLineEdit, QMenu, QScrollArea,
                               QSystemTrayIcon, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)

try:
    import winsound
except ImportError:
    winsound = None

APP_NAME = "Graphite Time"
APP_VERSION = "3.0.0"
AUTHOR = "heartcache"
GITHUB_URL = "https://github.com/heartcache"
DONATE_ADDRESS = "TCWxfKSyEY6ee46J8LWZLqq8RY7BdKBHoP"  # USDT, сеть TRC20 (Tron)
QR_ROWS = (
    "11111110000111110001101111111",
    "10000010010111111010101000001",
    "10111010111111010000001011101",
    "10111010101110110110101011101",
    "10111010101000011101101011101",
    "10000010111010000010001000001",
    "11111110101010101010101111111",
    "00000000111000101010100000000",
    "10111110011010000001001111100",
    "10111101111101110000111110101",
    "00101111110111110110000110000",
    "10111100011011010011000111001",
    "10100110011100111001110000100",
    "01111000001010011100101111000",
    "10011011010110011010100000100",
    "11110101110110101001110111001",
    "00100111111100000110110100010",
    "11101000000111101000101010110",
    "10101110011011110100000111100",
    "10010001101011010000111001010",
    "10010010110110100001111111000",
    "00000000111110011010100010000",
    "11111110010000010110101011100",
    "10000010101010100011100011011",
    "10111010111100010100111111110",
    "10111010111000111010000110111",
    "10111010101101011000110111010",
    "10000010010111100011111111010",
    "11111110110010000000011110000",
)
CJK = {}
RADIUS = 14
BREAK = QColor("#4FB99F")
DANGER = QColor("#E5484D")

RH = (QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing |
      QPainter.RenderHint.SmoothPixmapTransform)
NOPEN = Qt.PenStyle.NoPen
NOBRUSH = Qt.BrushStyle.NoBrush
CAP_R = Qt.PenCapStyle.RoundCap
JOIN_R = Qt.PenJoinStyle.RoundJoin
OUT = QEasingCurve.Type.OutCubic
INOUT = QEasingCurve.Type.InOutCubic
IN = QEasingCurve.Type.InCubic
BACK = QEasingCurve.Type.OutBack
W_LIGHT, W_NORMAL, W_MED, W_SEMI = (QFont.Weight.Light, QFont.Weight.Normal,
                                    QFont.Weight.Medium, QFont.Weight.DemiBold)

FAMILY = "Segoe UI"
_ANIM = True
_TICKS = True


def set_animations(v: bool):
    global _ANIM
    _ANIM = bool(v)


def set_ticks(v):
    global _TICKS
    _TICKS = bool(v)


def dur(ms):
    return max(1, int(ms)) if _ANIM else 1


# ───────────────────────────── helpers ─────────────────────────────
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_back(t, s=1.70158):
    t = clamp(t) - 1
    return 1 + t * t * ((s + 1) * t + s)


def alpha(c, a):
    c = QColor(c)
    c.setAlphaF(clamp(a))
    return c


def mix(a, b, t):
    t = clamp(t)
    return QColor.fromRgbF(lerp(a.redF(), b.redF(), t), lerp(a.greenF(), b.greenF(), t),
                           lerp(a.blueF(), b.blueF(), t), lerp(a.alphaF(), b.alphaF(), t))


def fmt_minutes(m):
    m = int(round(m))
    h, mm = divmod(m, 60)
    return f"{h} {tr('u.hs')} {mm} {tr('u.ms')}" if h else f"{mm} {tr('u.min')}"


def fmt_total(m):
    return f"{int(m)} {tr('u.ms')}" if m < 60 else f"{m / 60:.1f} {tr('u.hs')}"


def F(px, weight=W_MED, spacing=0.0):
    f = QFont(CJK.get(LANG) or FAMILY)
    f.setPixelSize(int(px))
    f.setWeight(weight)
    if spacing and LANG not in ("zh", "ja"):
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return f


def text(p, rect, s, font, color, align="l", elide=True):
    fm = QFontMetricsF(font)
    if elide and fm.horizontalAdvance(s) > rect.width():
        s = fm.elidedText(s, Qt.TextElideMode.ElideRight, max(1.0, rect.width()))
    tw = fm.horizontalAdvance(s)
    x = rect.left() if align == "l" else rect.right() - tw if align == "r" else rect.center().x() - tw / 2
    y = rect.center().y() + (fm.ascent() - fm.descent()) / 2
    p.setFont(font)
    p.setPen(color)
    p.drawText(QPointF(x, y), s)
    return tw


def rr_path(r, tl, tr, br, bl):
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    p = QPainterPath()
    p.moveTo(x + tl, y)
    p.lineTo(x + w - tr, y)
    p.arcTo(x + w - 2 * tr, y, 2 * tr, 2 * tr, 90, -90)
    p.lineTo(x + w, y + h - br)
    p.arcTo(x + w - 2 * br, y + h - 2 * br, 2 * br, 2 * br, 0, -90)
    p.lineTo(x + bl, y + h)
    p.arcTo(x, y + h - 2 * bl, 2 * bl, 2 * bl, -90, -90)
    p.lineTo(x, y + tl)
    p.arcTo(x, y, 2 * tl, 2 * tl, 180, -90)
    p.closeSubpath()
    return p


def fprop(name, default=0.0):
    attr = "_p_" + name

    def getter(self):
        return getattr(self, attr, default)

    def setter(self, v):
        setattr(self, attr, v)
        self.update()
    return Property(float, getter, setter)


def A(obj, name, end, ms=300, curve=OUT, start=None, finished=None):
    key = "_a_" + name
    old = getattr(obj, key, None)
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass
    a = QPropertyAnimation(obj, name.encode(), obj)
    a.setDuration(dur(ms))
    a.setEasingCurve(curve)
    if start is not None:
        a.setStartValue(float(start))
    a.setEndValue(float(end))
    if finished:
        a.finished.connect(finished)
    setattr(obj, key, a)
    a.start()
    return a


def running(obj, name):
    a = getattr(obj, "_a_" + name, None)
    try:
        return a is not None and a.state() == QAbstractAnimation.State.Running
    except RuntimeError:
        return False


def partial_poly(pts, t):
    segs = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    left = sum(segs) * clamp(t)
    out = [QPointF(*pts[0])]
    for i, s in enumerate(segs):
        if left <= 0:
            break
        k = min(1.0, left / s) if s else 1.0
        out.append(QPointF(lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k)))
        left -= s
    return QPolygonF(out)


# ───────────────────────────── theme ─────────────────────────────
def _sys_dark():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


class Theme:
    ACCENTS = {"graphite": ("Графит", None), "blue": ("Синий", "#4C7DFF"), "mint": ("Мята", "#2FBF9B"),
               "amber": ("Янтарь", "#F2A93B"), "rose": ("Роза", "#F0548C"), "violet": ("Violet", "#8B6CFF"),
               "sky": ("Sky", "#2E9BFF"), "coral": ("Coral", "#FF6B57")}

    def apply(self, mode, accent):
        d = mode == "dark" or (mode == "auto" and _sys_dark())
        c = QColor
        self.dark, self.mode, self.accent_key = d, mode, accent
        self.body = c("#18181A") if d else c("#F4F4F5")
        self.card = c("#242427") if d else c("#FFFFFF")
        self.titlebar = c("#101011") if d else c("#ECECEE")
        self.header = c("#0B0B0C") if d else c("#1B1B1D")
        self.text = c("#F5F5F7") if d else c("#1C1C1E")
        self.text2 = c("#9A9AA0") if d else c("#6C6C70")
        self.text3 = c("#5F5F66") if d else c("#A6A6AB")
        self.hair = QColor(255, 255, 255, 22) if d else QColor(0, 0, 0, 22)
        self.border = QColor(255, 255, 255, 40) if d else QColor(0, 0, 0, 55)
        self.track = c("#38383D") if d else c("#E4E4E7")
        self.capsule = c("#080809") if d else c("#161618")
        self.thumb = c("#3C3C41") if d else c("#FFFFFF")
        hx = self.ACCENTS.get(accent, self.ACCENTS["graphite"])[1]
        if hx is None:
            self.accent = c("#F5F5F7") if d else c("#1C1C1E")
            self.on_primary = c("#1C1C1E") if d else c("#FFFFFF")
            self.header_line = c("#EDEDF0")
        else:
            self.accent, self.on_primary, self.header_line = c(hx), c("#FFFFFF"), c(hx)
        self.primary = self.accent


T = Theme()
T.apply("light", "graphite")


def pick_family():
    fams = set(QFontDatabase.families())
    CJK["zh"] = next((f for f in ("Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei") if f in fams), None)
    CJK["ja"] = next((f for f in ("Yu Gothic UI", "Meiryo UI", "Hiragino Sans", "Noto Sans CJK JP") if f in fams), None)
    for f in ("SF Pro Display", "Segoe UI Variable Display", "Inter", "Segoe UI", "Helvetica Neue", "Arial"):
        if f in fams:
            return f
    return QApplication.font().family()


# ───────────────────────────── icons / logo ─────────────────────────────
def draw_icon(p, name, cx, cy, size, color, t=0.0, w=1.9):
    P = QPointF
    p.save()
    p.translate(cx, cy)
    k = size / 24.0
    p.scale(k, k)
    pen = QPen(color, w)
    pen.setCapStyle(CAP_R)
    pen.setJoinStyle(JOIN_R)
    p.setPen(pen)
    p.setBrush(NOBRUSH)
    if name == "playpause":
        p.setBrush(color)
        dx = lerp(1.5, 0, t)
        L0 = [(-6, -10), (2, -5), (2, 5), (-6, 10)]
        L1 = [(-8, -10), (-3, -10), (-3, 10), (-8, 10)]
        R0 = [(2, -5), (10, 0), (10, 0), (2, 5)]
        R1 = [(3, -10), (8, -10), (8, 10), (3, 10)]
        for a, b in ((L0, L1), (R0, R1)):
            p.drawPolygon(QPolygonF([P(lerp(x0, x1, t) + dx, lerp(y0, y1, t))
                                     for (x0, y0), (x1, y1) in zip(a, b)]))
    elif name == "play":
        p.setBrush(color)
        p.drawPolygon(QPolygonF([P(-4, -7), P(8, 0), P(-4, 7)]))
    elif name == "reset":
        r = 8.0
        p.drawArc(QRectF(-r, -r, 2 * r, 2 * r), 40 * 16, 280 * 16)
        a = math.radians(320)
        ex, ey = r * math.cos(a), -r * math.sin(a)
        dx, dy = -math.sin(a), -math.cos(a)
        nx, ny = -dy, dx
        p.setBrush(color)
        p.drawPolygon(QPolygonF([P(ex + dx * 4.5, ey + dy * 4.5), P(ex + nx * 4, ey + ny * 4),
                                 P(ex - nx * 4, ey - ny * 4)]))
    elif name == "skip":
        p.setBrush(color)
        p.drawPolygon(QPolygonF([P(-7, -8), P(4, 0), P(-7, 8)]))
        p.drawLine(P(8, -8), P(8, 8))
    elif name == "plus":
        p.drawLine(P(-7, 0), P(7, 0))
        p.drawLine(P(0, -7), P(0, 7))
    elif name == "minus":
        p.drawLine(P(-7, 0), P(7, 0))
    elif name == "close":
        p.drawLine(P(-5, -5), P(5, 5))
        p.drawLine(P(-5, 5), P(5, -5))
    elif name == "check":
        p.drawPolyline(QPolygonF([P(-6, 0.5), P(-2, 5), P(6, -5)]))
    elif name == "chevron":
        p.drawPolyline(QPolygonF([P(-3, -6), P(3, 0), P(-3, 6)]))
    elif name == "timer":
        p.drawEllipse(P(0, 1.5), 8, 8)
        p.drawLine(P(0, 1.5), P(3.2, -1.5))
        p.drawLine(P(-2.5, -10), P(2.5, -10))
    elif name == "tasks":
        for y in (-6, 0, 6):
            p.drawEllipse(P(-7, y), 2, 2)
            p.drawLine(P(-2, y), P(8, y))
    elif name == "user":
        p.drawEllipse(P(0, -4.5), 4, 4)
        pa = QPainterPath()
        pa.moveTo(-8, 9)
        pa.cubicTo(-8, 2.5, 8, 2.5, 8, 9)
        p.drawPath(pa)
    elif name == "sliders":
        p.setBrush(color)
        for y, x in ((-6, -3), (0, 4), (6, -1)):
            p.drawLine(P(-9, y), P(9, y))
            p.drawEllipse(P(x, y), 2.4, 2.4)
    elif name == "back":
        p.drawPolyline(QPolygonF([P(3, -6), P(-3, 0), P(3, 6)]))
    elif name == "mini":
        p.drawRoundedRect(QRectF(-9, -7, 18, 14), 3, 3)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(1, 0, 6, 4.5), 1.2, 1.2)
    elif name == "expand":
        p.drawPolyline(QPolygonF([P(1, -8), P(8, -8), P(8, -1)]))
        p.drawPolyline(QPolygonF([P(-1, 8), P(-8, 8), P(-8, 1)]))
        p.drawLine(P(8, -8), P(2, -2))
        p.drawLine(P(-8, 8), P(-2, 2))
    elif name == "camera":
        p.drawRoundedRect(QRectF(-9, -5, 18, 13), 3, 3)
        p.drawEllipse(P(0, 1.5), 3.6, 3.6)
        p.drawLine(P(-3, -5), P(-1.5, -8))
        p.drawLine(P(3, -5), P(1.5, -8))
        p.drawLine(P(-1.5, -8), P(1.5, -8))
    elif name == "crown":
        p.setBrush(color)
        p.drawPolygon(QPolygonF([P(-9, 6), P(-10, -5), P(-4.5, 0), P(0, -8), P(4.5, 0), P(10, -5), P(9, 6)]))
    elif name == "heart":
        pa = QPainterPath()
        pa.moveTo(0, 8)
        pa.cubicTo(-14, -1, -6, -11, 0, -4)
        pa.cubicTo(6, -11, 14, -1, 0, 8)
        p.setBrush(color)
        p.drawPath(pa)
    elif name == "star":
        pts = []
        for i in range(10):
            a, r = math.radians(-90 + i * 36), (9 if i % 2 == 0 else 4)
            pts.append(P(r * math.cos(a), r * math.sin(a)))
        p.setBrush(color)
        p.drawPolygon(QPolygonF(pts))
    elif name == "sun":
        p.drawEllipse(P(0, 0), 4, 4)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(P(7 * math.cos(a), 7 * math.sin(a)), P(10 * math.cos(a), 10 * math.sin(a)))
    elif name == "moon":
        a, b = QPainterPath(), QPainterPath()
        a.addEllipse(P(0, 0), 8, 8)
        b.addEllipse(P(4.5, -3), 7, 7)
        p.setBrush(color)
        p.drawPath(a.subtracted(b))
    elif name == "target":
        p.drawEllipse(P(0, 0), 9, 9)
        p.drawEllipse(P(0, 0), 4.8, 4.8)
        p.setBrush(color)
        p.drawEllipse(P(0, 0), 1.2, 1.2)
    elif name == "flag":
        p.drawLine(P(-6, -9), P(-6, 9))
        p.setBrush(color)
        p.drawPolygon(QPolygonF([P(-6, -8), P(8, -4), P(-6, 1)]))
    elif name == "chart":
        pen2 = QPen(color, w * 1.5)
        pen2.setCapStyle(CAP_R)
        p.setPen(pen2)
        p.drawLine(P(-6, 8), P(-6, 1))
        p.drawLine(P(0, 8), P(0, -7))
        p.drawLine(P(6, 8), P(6, -2))
    elif name == "ext":
        p.drawLine(P(-6, 6), P(6, -6))
        p.drawPolyline(QPolygonF([P(-1, -6), P(6, -6), P(6, 1)]))
    elif name == "copy":
        p.drawRoundedRect(QRectF(-4, -8, 12, 12), 3, 3)
        p.drawRoundedRect(QRectF(-8, -4, 12, 12), 3, 3)
    elif name == "download":
        p.drawLine(P(0, -8), P(0, 4))
        p.drawPolyline(QPolygonF([P(-5, -1), P(0, 4), P(5, -1)]))
        p.drawLine(P(-8, 8), P(8, 8))
    p.restore()


def draw_logo(p, r):
    p.save()
    p.setRenderHints(RH)
    rad = r.width() * 0.235
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#3C3C42"))
    g.setColorAt(1, QColor("#0E0E10"))
    p.setPen(NOPEN)
    p.setBrush(g)
    p.drawRoundedRect(r, rad, rad)
    p.setPen(QPen(QColor(255, 255, 255, 30), max(1.0, r.width() * 0.008)))
    p.setBrush(NOBRUSH)
    p.drawRoundedRect(r.adjusted(.5, .5, -.5, -.5), rad, rad)
    c = r.center()
    R, w = r.width() * 0.27, r.width() * 0.075
    p.setPen(QPen(QColor(255, 255, 255, 40), w))
    p.drawEllipse(c, R, R)
    sg = QLinearGradient(r.topLeft(), r.bottomRight())
    sg.setColorAt(0, QColor("#FFFFFF"))
    sg.setColorAt(1, QColor("#9C9CA6"))
    p.setPen(QPen(sg, w, Qt.PenStyle.SolidLine, CAP_R))
    p.drawArc(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), 90 * 16, -250 * 16)
    a = math.radians(-160)
    p.setPen(NOPEN)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(c.x() + R * math.cos(a), c.y() - R * math.sin(a)), w * 0.62, w * 0.62)
    p.drawEllipse(c, w * 0.42, w * 0.42)
    p.restore()


def logo_pixmap(size):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    draw_logo(p, QRectF(size * .04, size * .04, size * .92, size * .92))
    p.end()
    return pm


# ───────────────────────────── i18n ─────────────────────────────
LANGS = ["en", "ru", "zh", "es", "pt", "ja"]
LANG_NAMES = {"en": "English", "ru": "Русский", "zh": "简体中文", "es": "Español", "pt": "Português (BR)", "ja": "日本語"}
LANG = "en"


def set_lang(l):
    global LANG
    LANG = l if l in LANGS else "en"


def detect_lang():
    name = QLocale.system().name().lower()
    for pref in ("ru", "zh", "es", "pt", "ja"):
        if name.startswith(pref):
            return pref
    return "en"


def tr(key, **kw):
    row = TR.get(key)
    if row is None:
        return key
    s = row[LANGS.index(LANG)] or row[0]
    return s.format(**kw) if kw else s


def cat_name(c):
    if c["id"] in {x["id"] for x in DEFAULT_CATEGORIES}:
        return tr("cat." + c["id"])
    return c["name"]


LEVEL_STEPS = (1, 3, 6, 10, 15, 22, 30, 40, 50)


def level_title(l):
    return tr("lv.%d" % (sum(1 for x in LEVEL_STEPS if l >= x) - 1))


TR = {
    "tab.focus": ("Focus", "Фокус", "专注", "Enfoque", "Foco", "集中"),
    "tab.tasks": ("Tasks", "Задачи", "任务", "Tareas", "Tarefas", "タスク"),
    "tab.profile": ("Profile", "Профиль", "我的", "Perfil", "Perfil", "プロフィール"),
    "tab.settings": ("Settings", "Настройки", "设置", "Ajustes", "Ajustes", "設定"),
    "mode.focus": ("FOCUS", "ФОКУС", "专注", "ENFOQUE", "FOCO", "集中"),
    "mode.short": ("BREAK", "ПЕРЕРЫВ", "休息", "DESCANSO", "PAUSA", "休憩"),
    "mode.long": ("LONG BREAK", "ДЛИННЫЙ ПЕРЕРЫВ", "长休息", "DESCANSO LARGO", "PAUSA LONGA", "長い休憩"),
    "mode.paused": ("PAUSED", "ПАУЗА", "已暂停", "EN PAUSA", "PAUSADO", "一時停止"),
    "u.min": ("min", "мин", "分钟", "min", "min", "分"),
    "u.ms": ("m", "м", "分", "m", "m", "分"),
    "u.hs": ("h", "ч", "小时", "h", "h", "時間"),
    "p.min": ("{n} min", "{n} мин", "{n} 分钟", "{n} min", "{n} min", "{n}分"),
    "version": ("Version {v}", "Версия {v}", "版本 {v}", "Versión {v}", "Versão {v}", "バージョン {v}"),
    "hd.today": ("Today", "Сегодня", "今天", "Hoy", "Hoje", "今日"),
    "hd.closed": ("Day closed", "День закрыт", "今日完成", "Día completado", "Dia concluído", "今日達成"),
    "hd.start": ("Starting up", "Запуск", "启动中", "Iniciando", "Iniciando", "起動中"),
    "hd.prep": ("Preparing your space", "Подготовка пространства", "正在准备", "Preparando tu espacio", "Preparando seu espaço", "準備中"),
    "hd.add_first": ("Add your first task", "Добавь первую задачу", "添加你的第一个任务", "Añade tu primera tarea", "Adicione sua primeira tarefa", "最初のタスクを追加"),
    "hd.done_of": ("Done {d} of {t}", "Выполнено {d} из {t}", "已完成 {d}/{t}", "Hechas {d} de {t}", "Concluídas {d} de {t}", "{t}件中{d}件完了"),
    "hd.focus": ("Focus {x}", "Фокус {x}", "专注 {x}", "Enfoque {x}", "Foco {x}", "集中 {x}"),
    "hd.all_done": ("All done", "Всё выполнено", "全部完成", "Todo hecho", "Tudo feito", "すべて完了"),
    "date.fmt": ("{wd}, {mo} {d}", "{wd}, {d} {mo}", "{mo}{d}日 {wd}", "{wd}, {d} de {mo}", "{wd}, {d} de {mo}", "{mo}{d}日 {wd}"),
    "tk.title": ("What are we doing today?", "Что сделаем сегодня?", "今天做什么？", "¿Qué hacemos hoy?", "O que vamos fazer hoje?", "今日は何をする？"),
    "tk.new": ("New task", "Новая задача", "新任务", "Nueva tarea", "Nova tarefa", "新しいタスク"),
    "tk.all": ("All", "Все", "全部", "Todas", "Todas", "すべて"),
    "tk.empty": ("Nothing here yet", "Пока пусто", "这里还空着", "Aún no hay nada", "Ainda vazio", "まだ空です"),
    "tk.empty2": ("Add your first task — small steps are easier", "Добавь первую задачу — маленькими шагами проще", "添加第一个任务——小步更轻松", "Añade tu primera tarea: los pasos pequeños son más fáciles", "Adicione a primeira tarefa — passos pequenos são mais fáceis", "最初のタスクを追加しよう。小さな一歩から"),
    "tk.done": ("Task completed  ·  +15 XP", "Задача выполнена  ·  +15 XP", "任务完成  ·  +15 XP", "Tarea completada  ·  +15 XP", "Tarefa concluída  ·  +15 XP", "タスク完了  ·  +15 XP"),
    "tk.infocus": ("In focus: {t}", "В фокусе: {t}", "专注中：{t}", "En foco: {t}", "Em foco: {t}", "集中中：{t}"),
    "tk.stop": ("Stop the timer first", "Сначала останови таймер", "请先停止计时器", "Detén primero el temporizador", "Pare o cronômetro primeiro", "先にタイマーを止めてください"),
    "chip.now": ("NOW IN FOCUS", "СЕЙЧАС В ФОКУСЕ", "当前专注", "EN FOCO AHORA", "EM FOCO AGORA", "いま集中中"),
    "chip.task": ("TASK", "ЗАДАЧА", "任务", "TAREA", "TAREFA", "タスク"),
    "chip.pick": ("Pick what you're working on", "Выбери, над чем работаешь", "选择你正在做的事", "Elige en qué trabajas", "Escolha no que está trabalhando", "取り組むタスクを選ぼう"),
    "tip.playpause": ("Start / pause  (Space)", "Старт / пауза  (Пробел)", "开始 / 暂停（空格）", "Iniciar / pausar  (Espacio)", "Iniciar / pausar  (Espaço)", "開始 / 一時停止（スペース）"),
    "tip.reset": ("Reset", "Сбросить", "重置", "Reiniciar", "Reiniciar", "リセット"),
    "tip.skip": ("Skip", "Пропустить", "跳过", "Saltar", "Pular", "スキップ"),
    "tip.mini": ("Mini mode", "Мини-режим", "迷你模式", "Modo mini", "Modo mini", "ミニモード"),
    "tip.expand": ("Open full window", "Открыть окно", "展开窗口", "Abrir ventana", "Abrir janela", "ウィンドウを開く"),
    "wd.0": ("Monday", "понедельник", "星期一", "lunes", "segunda-feira", "月曜日"),
    "wd.1": ("Tuesday", "вторник", "星期二", "martes", "terça-feira", "火曜日"),
    "wd.2": ("Wednesday", "среда", "星期三", "miércoles", "quarta-feira", "水曜日"),
    "wd.3": ("Thursday", "четверг", "星期四", "jueves", "quinta-feira", "木曜日"),
    "wd.4": ("Friday", "пятница", "星期五", "viernes", "sexta-feira", "金曜日"),
    "wd.5": ("Saturday", "суббота", "星期六", "sábado", "sábado", "土曜日"),
    "wd.6": ("Sunday", "воскресенье", "星期日", "domingo", "domingo", "日曜日"),
    "d.0": ("Mo", "Пн", "一", "L", "S", "月"),
    "d.1": ("Tu", "Вт", "二", "M", "T", "火"),
    "d.2": ("We", "Ср", "三", "X", "Q", "水"),
    "d.3": ("Th", "Чт", "四", "J", "Q", "木"),
    "d.4": ("Fr", "Пт", "五", "V", "S", "金"),
    "d.5": ("Sa", "Сб", "六", "S", "S", "土"),
    "d.6": ("Su", "Вс", "日", "D", "D", "日"),
    "mo.0": ("January", "января", "1月", "enero", "janeiro", "1月"),
    "mo.1": ("February", "февраля", "2月", "febrero", "fevereiro", "2月"),
    "mo.2": ("March", "марта", "3月", "marzo", "março", "3月"),
    "mo.3": ("April", "апреля", "4月", "abril", "abril", "4月"),
    "mo.4": ("May", "мая", "5月", "mayo", "maio", "5月"),
    "mo.5": ("June", "июня", "6月", "junio", "junho", "6月"),
    "mo.6": ("July", "июля", "7月", "julio", "julho", "7月"),
    "mo.7": ("August", "августа", "8月", "agosto", "agosto", "8月"),
    "mo.8": ("September", "сентября", "9月", "septiembre", "setembro", "9月"),
    "mo.9": ("October", "октября", "10月", "octubre", "outubro", "10月"),
    "mo.10": ("November", "ноября", "11月", "noviembre", "novembro", "11月"),
    "mo.11": ("December", "декабря", "12月", "diciembre", "dezembro", "12月"),
    "cat.study": ("Study", "Учёба", "学习", "Estudio", "Estudos", "勉強"),
    "cat.games": ("Games", "Игры", "游戏", "Juegos", "Jogos", "ゲーム"),
    "cat.design": ("Design & Art", "Дизайн и арт", "设计与艺术", "Diseño y arte", "Design e arte", "デザイン・アート"),
    "cat.work": ("Work", "Работа", "工作", "Trabajo", "Trabalho", "仕事"),
    "cat.money": ("Finance", "Финансы", "财务", "Finanzas", "Finanças", "お金"),
    "cat.sport": ("Sport", "Спорт", "运动", "Deporte", "Esporte", "運動"),
    "cat.reading": ("Reading", "Чтение", "阅读", "Lectura", "Leitura", "読書"),
    "cat.home": ("Home", "Дом и быт", "家务", "Casa", "Casa", "家事"),
    "cat.other": ("Other", "Другое", "其他", "Otros", "Outros", "その他"),
    "lv.0": ("Newcomer", "Новичок", "新手", "Novato", "Novato", "ビギナー"),
    "lv.1": ("Warming up", "Разогрев", "热身", "Calentando", "Aquecendo", "ウォームアップ"),
    "lv.2": ("In rhythm", "В ритме", "渐入佳境", "En ritmo", "No ritmo", "リズムに乗る"),
    "lv.3": ("Focused", "Сосредоточенный", "专注者", "Concentrado", "Focado", "集中モード"),
    "lv.4": ("Well done", "Молодец", "干得漂亮", "¡Bien hecho!", "Mandou bem", "よくできました"),
    "lv.5": ("Steel focus", "Стальной фокус", "钢铁专注", "Enfoque de acero", "Foco de aço", "鋼の集中力"),
    "lv.6": ("Flow master", "Мастер потока", "心流大师", "Maestro del flujo", "Mestre do fluxo", "フローの達人"),
    "lv.7": ("Grandmaster", "Гроссмейстер", "特级大师", "Gran maestro", "Grão-mestre", "グランドマスター"),
    "lv.8": ("Legend", "Легенда", "传奇", "Leyenda", "Lenda", "レジェンド"),
}

TR.update({
    "st.timer": ("Timer", "Таймер", "计时器", "Temporizador", "Cronômetro", "タイマー"),
    "st.behavior": ("Behavior", "Поведение", "行为", "Comportamiento", "Comportamento", "動作"),
    "st.sounds": ("Sounds", "Звуки", "声音", "Sonidos", "Sons", "サウンド"),
    "st.appearance": ("Appearance", "Внешний вид", "外观", "Apariencia", "Aparência", "外観"),
    "st.language": ("Language", "Язык", "语言", "Idioma", "Idioma", "言語"),
    "st.categories": ("Task categories", "Категории задач", "任务分类", "Categorías de tareas", "Categorias de tarefas", "タスクのカテゴリ"),
    "st.support": ("Support", "Поддержка", "支持", "Apoyo", "Apoio", "サポート"),
    "st.data": ("Data", "Данные", "数据", "Datos", "Dados", "データ"),
    "st.about": ("About", "О программе", "关于", "Acerca de", "Sobre", "このアプリについて"),
    "s.focus": ("Focus", "Фокус", "专注时长", "Enfoque", "Foco", "集中"),
    "s.short": ("Short break", "Короткий перерыв", "短休息", "Descanso corto", "Pausa curta", "短い休憩"),
    "s.long": ("Long break", "Длинный перерыв", "长休息", "Descanso largo", "Pausa longa", "長い休憩"),
    "s.cycles": ("Sessions before long break", "Сессий до длинного", "长休息前的专注次数", "Sesiones hasta el descanso largo", "Sessões até a pausa longa", "長い休憩までの回数"),
    "s.goal": ("Daily goal", "Дневная цель", "每日目标", "Meta diaria", "Meta diária", "1日の目標"),
    "s.week_start": ("Week starts on", "Неделя начинается", "每周开始于", "La semana empieza el", "A semana começa na", "週の開始"),
    "s.mon": ("Mon", "Пн", "周一", "Lun", "Seg", "月"),
    "s.sun": ("Sun", "Вс", "周日", "Dom", "Dom", "日"),
    "s.auto_break": ("Auto-start breaks", "Автозапуск перерывов", "自动开始休息", "Iniciar descansos solo", "Iniciar pausas sozinho", "休憩を自動開始"),
    "s.auto_focus": ("Auto-start focus", "Автозапуск фокуса", "自动开始专注", "Iniciar enfoque solo", "Iniciar foco sozinho", "集中を自動開始"),
    "s.end_warn": ("Warn 1 minute before end", "Предупреждать за минуту", "结束前1分钟提醒", "Avisar 1 minuto antes", "Avisar 1 minuto antes", "終了1分前に通知"),
    "s.notify": ("Notifications", "Уведомления", "通知", "Notificaciones", "Notificações", "通知"),
    "s.title_time": ("Time in window title", "Время в заголовке окна", "标题栏显示时间", "Tiempo en el título", "Tempo no título", "タイトルに時間を表示"),
    "s.on_top": ("Always on top", "Поверх всех окон", "窗口置顶", "Siempre visible", "Sempre no topo", "常に手前に表示"),
    "s.popup_end": ("Show window when time is up", "Показывать окно по окончании", "结束时弹出窗口", "Mostrar al terminar", "Mostrar ao terminar", "終了時にウィンドウを表示"),
    "s.mini_min": ("Mini mode on minimize", "Мини-режим при сворачивании", "最小化时进入迷你模式", "Modo mini al minimizar", "Modo mini ao minimizar", "最小化でミニモード"),
    "s.autostart": ("Launch with Windows", "Запускать с Windows", "开机自动启动", "Iniciar con Windows", "Iniciar com o Windows", "Windows起動時に開始"),
    "s.sound": ("Sounds", "Звук", "声音", "Sonido", "Som", "サウンド"),
    "s.volume": ("Volume", "Громкость", "音量", "Volumen", "Volume", "音量"),
    "snd.focus_end": ("When focus ends", "Конец фокуса", "专注结束时", "Al terminar el enfoque", "Ao fim do foco", "集中が終わったとき"),
    "snd.break_end": ("When break ends", "Конец перерыва", "休息结束时", "Al terminar el descanso", "Ao fim da pausa", "休憩が終わったとき"),
    "snd.chime": ("Chime", "Перезвон", "风铃", "Carillón", "Carrilhão", "チャイム"),
    "snd.bell": ("Bell", "Колокол", "钟声", "Campana", "Sino", "ベル"),
    "snd.glass": ("Glass", "Стекло", "玻璃", "Cristal", "Vidro", "グラス"),
    "snd.drop": ("Drop", "Капля", "水滴", "Gota", "Gota", "しずく"),
    "snd.pulse": ("Pulse", "Импульс", "脉冲", "Pulso", "Pulso", "パルス"),
    "snd.soft": ("Soft", "Мягкий", "柔和", "Suave", "Suave", "ソフト"),
    "s.theme": ("Theme", "Тема", "主题", "Tema", "Tema", "テーマ"),
    "s.light": ("Light", "Светлая", "浅色", "Claro", "Claro", "ライト"),
    "s.dark": ("Dark", "Тёмная", "深色", "Oscuro", "Escuro", "ダーク"),
    "s.auto": ("Auto", "Авто", "自动", "Auto", "Auto", "自動"),
    "s.accent": ("Accent", "Акцент", "强调色", "Acento", "Destaque", "アクセント"),
    "s.ticks": ("Ring tick marks", "Деления на кольце", "圆环刻度", "Marcas del anillo", "Marcas do anel", "リングの目盛り"),
    "s.opacity": ("Window opacity", "Прозрачность окна", "窗口不透明度", "Opacidad de la ventana", "Opacidade da janela", "ウィンドウの不透明度"),
    "s.animations": ("Animations", "Анимации", "动画", "Animaciones", "Animações", "アニメーション"),
    "s.sub_anim": ("Smooth transitions and effects", "Плавные переходы и эффекты", "流畅的过渡与效果", "Transiciones y efectos suaves", "Transições e efeitos suaves", "なめらかな遷移と効果"),
    "s.language": ("Interface language", "Язык интерфейса", "界面语言", "Idioma de la interfaz", "Idioma da interface", "表示言語"),
    "s.newcat": ("New category", "Новая категория", "新分类", "Nueva categoría", "Nova categoria", "新しいカテゴリ"),
    "s.support_open": ("Support the project", "Поддержать проект", "支持这个项目", "Apoyar el proyecto", "Apoiar o projeto", "プロジェクトを支援"),
    "s.support_sub": ("Optional crypto donation", "Необязательный донат криптой", "自愿加密货币捐赠", "Donación opcional en cripto", "Doação opcional em cripto", "任意の暗号資産での寄付"),
    "s.export": ("Export data", "Экспорт данных", "导出数据", "Exportar datos", "Exportar dados", "データを書き出す"),
    "s.exported": ("Saved: {p}", "Сохранено: {p}", "已保存：{p}", "Guardado: {p}", "Salvo: {p}", "保存しました：{p}"),
    "s.reset_stats": ("Reset statistics", "Сбросить статистику", "重置统计", "Restablecer estadísticas", "Redefinir estatísticas", "統計をリセット"),
    "s.reset_all": ("Delete all data", "Удалить все данные", "删除所有数据", "Borrar todos los datos", "Apagar todos os dados", "すべてのデータを削除"),
    "s.confirm": ("Tap again to confirm", "Нажми ещё раз, чтобы подтвердить", "再点一次确认", "Pulsa de nuevo para confirmar", "Toque de novo para confirmar", "もう一度タップして確認"),
    "off": ("Off", "Выкл", "关闭", "No", "Desl.", "オフ"),
    "about.made": ("Made by {a}", "Автор: {a}", "作者：{a}", "Creado por {a}", "Criado por {a}", "作者：{a}"),
    "tray.open": ("Open", "Открыть", "打开", "Abrir", "Abrir", "開く"),
    "tray.quit": ("Quit", "Выйти", "退出", "Salir", "Sair", "終了"),
    "tray.start": ("Start", "Старт", "开始", "Iniciar", "Iniciar", "開始"),
    "tray.pause": ("Pause", "Пауза", "暂停", "Pausar", "Pausar", "一時停止"),
    "tray.bg": ("Timer keeps running in the background", "Таймер продолжает работать в фоне", "计时器仍在后台运行", "El temporizador sigue en segundo plano", "O cronômetro continua em segundo plano", "タイマーはバックグラウンドで動作中"),
    "warn.1min": ("One minute left", "Осталась минута", "还剩1分钟", "Queda un minuto", "Falta um minuto", "残り1分"),
    "done.focus": ("Focus finished", "Фокус завершён", "专注结束", "Enfoque terminado", "Foco concluído", "集中終了"),
    "done.focus_sub": ("Time to rest — well done", "Время отдохнуть — ты молодец", "休息一下吧，你做得很好", "Hora de descansar: bien hecho", "Hora de descansar — mandou bem", "休憩しましょう。よく頑張りました"),
    "done.break": ("Break is over", "Перерыв окончен", "休息结束", "Descanso terminado", "Pausa encerrada", "休憩終了"),
    "done.break_sub": ("Back to focus", "Пора возвращаться в фокус", "该回到专注状态了", "Es hora de volver al enfoque", "Hora de voltar ao foco", "集中に戻りましょう"),
    "lvup": ("New level  ·  {l} — {t}", "Новый уровень  ·  {l} — {t}", "新等级  ·  {l} — {t}", "Nuevo nivel  ·  {l} — {t}", "Novo nível  ·  {l} — {t}", "レベルアップ  ·  {l} — {t}"),
    "ach.unlocked": ("Achievement  ·  {n}", "Награда  ·  {n}", "成就解锁  ·  {n}", "Logro  ·  {n}", "Conquista  ·  {n}", "実績  ·  {n}"),
})

TR.update({
    "pf.name": ("Your name", "Твоё имя", "你的名字", "Tu nombre", "Seu nome", "あなたの名前"),
    "pf.avatar": ("Change photo", "Сменить фото", "更换头像", "Cambiar foto", "Trocar foto", "写真を変更"),
    "pf.avatar_off": ("Remove photo", "Убрать фото", "移除头像", "Quitar foto", "Remover foto", "写真を削除"),
    "pf.pick": ("Choose an image", "Выберите изображение", "选择图片", "Elige una imagen", "Escolha uma imagem", "画像を選択"),
    "ix.title": ("WELL-DONE INDEX", "МОЛОДЕЦ-ИНДЕКС", "成就指数", "ÍNDICE DE LOGRO", "ÍNDICE DE CONQUISTA", "がんばり指数"),
    "ix.of": ("OUT OF 100", "ИЗ 100", "满分 100", "DE 100", "DE 100", "100点満点"),
    "ix.steady": ("Consistency", "Постоянство", "持续性", "Constancia", "Constância", "継続性"),
    "ix.b0": ("Getting started", "Разгоняемся", "起步中", "Arrancando", "Começando", "スタート"),
    "ix.b0s": ("every step counts", "каждый шаг считается", "每一步都算数", "cada paso cuenta", "cada passo conta", "一歩ずつ前進"),
    "ix.b1": ("Not bad", "Неплохо", "不错", "No está mal", "Nada mal", "いい感じ"),
    "ix.b1s": ("a rhythm is forming", "ритм уже появляется", "节奏正在形成", "el ritmo se está formando", "o ritmo está se formando", "リズムができてきた"),
    "ix.b2": ("Going well", "Хорошо идёшь", "进展顺利", "Vas bien", "Indo bem", "順調"),
    "ix.b2s": ("keep the pace", "держи темп", "保持节奏", "mantén el ritmo", "mantenha o ritmo", "このペースで"),
    "ix.b3": ("Well done", "Молодец", "干得漂亮", "¡Bien hecho!", "Mandou bem", "よくできました"),
    "ix.b3s": ("you're in great shape", "ты в хорошей форме", "状态很棒", "estás en gran forma", "você está em ótima forma", "絶好調です"),
    "ix.b4": ("On fire", "Огонь", "势如破竹", "Imparable", "Imparável", "燃えてる"),
    "ix.b4s": ("a very strong week", "очень сильная неделя", "非常出色的一周", "una semana muy fuerte", "uma semana muito forte", "素晴らしい一週間"),
    "ix.b5": ("Legend", "Легенда", "传奇", "Leyenda", "Lenda", "レジェンド"),
    "ix.b5s": ("master level", "уровень мастера", "大师级别", "nivel maestro", "nível mestre", "マスターレベル"),
    "ps.streak": ("Streak", "Серия", "连续", "Racha", "Sequência", "連続"),
    "ps.days": ("days in a row", "дн. подряд", "天", "días seguidos", "dias seguidos", "日連続"),
    "ps.total": ("all time", "всего", "累计", "en total", "no total", "累計"),
    "ps.done": ("completed", "выполнено", "已完成", "completadas", "concluídas", "完了"),
    "ps.sessions": ("Sessions", "Сессии", "专注次数", "Sesiones", "Sessões", "セッション"),
    "ps.sessions_u": ("finished", "завершено", "已完成", "terminadas", "finalizadas", "完了"),
    "wk.title": ("This week", "Эта неделя", "本周", "Esta semana", "Esta semana", "今週"),
    "bd.title": ("Achievements", "Награды", "成就", "Logros", "Conquistas", "実績"),
    "wg.title": ("Weekly goal", "Цель недели", "每周目标", "Meta semanal", "Meta semanal", "週間目標"),
    "wg.ph": ("e.g. Build a 3D character model", "Напр.: сделать 3D-модель человека", "例如：制作3D人物模型", "p. ej. Modelar un personaje 3D", "ex.: Modelar um personagem 3D", "例：3Dキャラクターを作る"),
    "wg.hours": ("Hours per week", "Часов в неделю", "每周小时数", "Horas por semana", "Horas por semana", "週の目標時間"),
    "wg.only": ("COUNT ONLY", "СЧИТАТЬ ТОЛЬКО", "仅统计", "CONTAR SOLO", "CONTAR APENAS", "対象"),
    "wg.of": ("of {b}", "из {b}", "/ {b}", "de {b}", "de {b}", "/ {b}"),
    "wg.pace": ("≈ {x} a day for {n} more days", "≈ {x} в день ещё {n} дн.", "剩余 {n} 天，每天约 {x}", "≈ {x} al día durante {n} días más", "≈ {x} por dia nos próximos {n} dias", "残り{n}日、1日あたり約{x}"),
    "wg.pace1": ("≈ {x} left for today", "≈ {x} осталось на сегодня", "今天还需约 {x}", "≈ {x} que faltan hoy", "≈ {x} que faltam hoje", "今日はあと約{x}"),
    "wg.reached": ("Goal reached — great work", "Цель достигнута — отличная работа", "目标达成，太棒了", "Meta alcanzada: ¡gran trabajo!", "Meta atingida — ótimo trabalho", "目標達成！お疲れさま"),
    "wg.none": ("Set a goal for a big project — a few hours every day add up", "Поставь цель на большой проект — по несколько часов в день складываются в результат", "为大项目设定目标——每天几小时，积少成多", "Fija una meta para un proyecto grande: unas horas al día suman", "Defina uma meta para um projeto grande — algumas horas por dia somam", "大きなプロジェクトの目標を決めよう。毎日数時間の積み重ねが力になります"),
    "wg.hit": ("Weekly goal reached!", "Цель недели достигнута!", "本周目标达成！", "¡Meta semanal alcanzada!", "Meta semanal atingida!", "週間目標を達成！"),
    "hd.week": ("Week {p}%", "Нед. {p}%", "本周 {p}%", "Sem. {p}%", "Sem. {p}%", "週 {p}%"),
    "sp.title": ("Support Graphite Time", "Поддержать Graphite Time", "支持 Graphite Time", "Apoya Graphite Time", "Apoie o Graphite Time", "Graphite Time を応援"),
    "ach.first": ("First step", "Первый шаг", "第一步", "Primer paso", "Primeiro passo", "最初の一歩"),
    "ach.first.d": ("Finish your first session", "Заверши первую сессию", "完成第一次专注", "Termina tu primera sesión", "Conclua sua primeira sessão", "最初のセッションを完了"),
    "ach.hour": ("Power hour", "Час силы", "一小时", "Hora de poder", "Hora de força", "1時間達成"),
    "ach.hour.d": ("60 minutes of focus", "60 минут фокуса", "累计专注60分钟", "60 minutos de enfoque", "60 minutos de foco", "集中60分"),
    "ach.ten": ("Ten tasks", "Десятка", "十项任务", "Diez tareas", "Dez tarefas", "10タスク"),
    "ach.ten.d": ("Complete 10 tasks", "10 выполненных задач", "完成10个任务", "Completa 10 tareas", "Conclua 10 tarefas", "10個のタスクを完了"),
    "ach.s3": ("3 days", "3 дня", "连续3天", "3 días", "3 dias", "3日連続"),
    "ach.s3.d": ("3 days in a row", "3 дня подряд", "连续3天有活动", "3 días seguidos", "3 dias seguidos", "3日連続で活動"),
    "ach.s7": ("Full week", "Неделя", "整整一周", "Semana", "Semana", "1週間"),
    "ach.s7.d": ("7 days in a row", "7 дней подряд", "连续7天", "7 días seguidos", "7 dias seguidos", "7日連続"),
    "ach.deep": ("Deep dive", "Глубина", "深度专注", "Inmersión", "Mergulho", "深く潜る"),
    "ach.deep.d": ("A session of 50+ minutes", "Сессия от 50 минут", "单次专注50分钟以上", "Una sesión de 50+ minutos", "Uma sessão de 50+ minutos", "50分以上のセッション"),
    "ach.five": ("Marathon", "Марафон", "马拉松", "Maratón", "Maratona", "マラソン"),
    "ach.five.d": ("5 hours of focus", "5 часов фокуса", "累计专注5小时", "5 horas de enfoque", "5 horas de foco", "集中5時間"),
    "ach.close": ("Day closed", "День закрыт", "清空待办", "Día cerrado", "Dia fechado", "今日完了"),
    "ach.close.d": ("Finish all tasks of the day (3+)", "Закрой все задачи дня (от 3)", "完成当天所有任务（3个以上）", "Termina todas las tareas del día (3+)", "Conclua todas as tarefas do dia (3+)", "その日のタスクを全部完了（3件以上）"),
    "ach.s30": ("30 days", "30 дней", "连续30天", "30 días", "30 dias", "30日連続"),
    "ach.s30.d": ("30 days in a row", "30 дней подряд", "连续30天", "30 días seguidos", "30 dias seguidos", "30日連続"),
    "ach.h25": ("25 hours", "25 часов", "25小时", "25 horas", "25 horas", "25時間"),
    "ach.h25.d": ("25 hours of focus in total", "25 часов фокуса всего", "累计专注25小时", "25 horas de enfoque en total", "25 horas de foco no total", "累計25時間の集中"),
    "ach.h100": ("Centurion", "Сотня", "百小时", "Centurión", "Centurião", "100時間"),
    "ach.h100.d": ("100 hours of focus in total", "100 часов фокуса всего", "累计专注100小时", "100 horas de enfoque en total", "100 horas de foco no total", "累計100時間の集中"),
    "ach.se25": ("25 sessions", "25 сессий", "25次专注", "25 sesiones", "25 sessões", "25セッション"),
    "ach.se25.d": ("Finish 25 sessions", "Заверши 25 сессий", "完成25次专注", "Termina 25 sesiones", "Conclua 25 sessões", "25セッションを完了"),
    "ach.se100": ("100 sessions", "100 сессий", "100次专注", "100 sesiones", "100 sessões", "100セッション"),
    "ach.se100.d": ("Finish 100 sessions", "Заверши 100 сессий", "完成100次专注", "Termina 100 sesiones", "Conclua 100 sessões", "100セッションを完了"),
    "ach.t25": ("25 tasks", "25 задач", "25个任务", "25 tareas", "25 tarefas", "25タスク"),
    "ach.t25.d": ("Complete 25 tasks", "Выполни 25 задач", "完成25个任务", "Completa 25 tareas", "Conclua 25 tarefas", "25個のタスクを完了"),
    "ach.t100": ("100 tasks", "100 задач", "100个任务", "100 tareas", "100 tarefas", "100タスク"),
    "ach.t100.d": ("Complete 100 tasks", "Выполни 100 задач", "完成100个任务", "Completa 100 tareas", "Conclua 100 tarefas", "100個のタスクを完了"),
    "ach.early": ("Early bird", "Жаворонок", "早起鸟", "Madrugador", "Madrugador", "早起き"),
    "ach.early.d": ("Finish a session before 8 AM", "Заверши сессию до 8 утра", "在早上8点前完成一次专注", "Termina una sesión antes de las 8", "Conclua uma sessão antes das 8h", "午前8時前にセッションを完了"),
    "ach.night": ("Night owl", "Сова", "夜猫子", "Búho nocturno", "Coruja", "夜型"),
    "ach.night.d": ("Finish a session after 11 PM", "Заверши сессию после 23:00", "在晚上11点后完成一次专注", "Termina una sesión después de las 23", "Conclua uma sessão após as 23h", "午後11時以降にセッションを完了"),
    "ach.daygoal": ("Goal hit", "Цель дня", "达成日标", "Meta cumplida", "Meta batida", "目標達成"),
    "ach.daygoal.d": ("Reach your daily focus goal", "Выполни дневную цель по фокусу", "达成每日专注目标", "Alcanza tu meta diaria de enfoque", "Atinja sua meta diária de foco", "1日の集中目標を達成"),
    "ach.wk1": ("Big picture", "Цель недели", "周目标", "Meta semanal", "Meta semanal", "週間目標"),
    "ach.wk1.d": ("Reach a weekly goal", "Выполни цель недели", "达成一次每周目标", "Alcanza una meta semanal", "Atinja uma meta semanal", "週間目標を達成"),
    "ach.lv5": ("Level 5", "5 уровень", "5级", "Nivel 5", "Nível 5", "レベル5"),
    "ach.lv5.d": ("Reach level 5", "Достигни 5 уровня", "达到5级", "Alcanza el nivel 5", "Alcance o nível 5", "レベル5に到達"),
    "sp.text": ("Free, no ads, no tracking. If it helps you focus and you'd like to say thanks, you can send a little crypto — completely optional.", "Бесплатно, без рекламы и слежки. Если программа помогает сосредоточиться и хочется сказать спасибо — можно отправить немного крипты. Это полностью по желанию.", "免费、无广告、不追踪。如果它帮你保持专注，想表达谢意，可以捐一点加密货币——完全自愿。", "Gratis, sin anuncios ni rastreo. Si te ayuda a concentrarte y quieres dar las gracias, puedes enviar un poco de cripto; es totalmente opcional.", "Grátis, sem anúncios nem rastreamento. Se ela ajuda você a focar e você quiser agradecer, pode enviar um pouco de cripto — totalmente opcional.", "無料・広告なし・追跡なし。集中の助けになってお礼をしたいときは、少額の暗号資産を送れます。まったく任意です。"),
    "sp.warn": ("Send only USDT on the TRC20 network to this address, or the funds may be lost.", "Отправляйте на этот адрес только USDT в сети TRC20, иначе средства могут быть потеряны.", "请仅通过 TRC20 网络向此地址发送 USDT，否则资产可能丢失。", "Envía solo USDT por la red TRC20 a esta dirección; de lo contrario, podrías perder los fondos.", "Envie apenas USDT pela rede TRC20 para este endereço, ou os fundos podem ser perdidos.", "このアドレスにはTRC20ネットワークのUSDTのみ送ってください。それ以外は資金を失う可能性があります。"),
    "sp.copy": ("Copy address", "Копировать адрес", "复制地址", "Copiar dirección", "Copiar endereço", "アドレスをコピー"),
    "sp.copied": ("Address copied", "Адрес скопирован", "地址已复制", "Dirección copiada", "Endereço copiado", "コピーしました"),
    "sp.scan": ("Scan the QR code or copy the address", "Отсканируй QR-код или скопируй адрес", "扫描二维码或复制地址", "Escanea el QR o copia la dirección", "Escaneie o QR ou copie o endereço", "QRコードを読み取るか、アドレスをコピー"),
    "cr.role": ("Creator", "Создатель", "作者", "Creador", "Criador", "作者"),
})



TR.update({
    "tab.stats": ("Stats", "Статистика", "统计", "Estadísticas", "Estatísticas", "統計"),
    "u.h1": ("h", "ч", "时", "h", "h", "時間"),
    "mode.free": ("FLOW", "ПОТОК", "心流", "FLUJO", "FLUXO", "フロー"),
    "tip.time": ("Time settings", "Настройка времени", "时间设置", "Ajustar tiempo", "Ajustar tempo", "時間の設定"),
    "tip.finish": ("Finish early", "Завершить досрочно", "提前完成", "Terminar antes", "Concluir antes", "早めに終了"),
    "pr.flow": ("Flow", "Поток", "心流", "Flujo", "Fluxo", "フロー"),
    "pr.nobreak": ("no break", "без перерыва", "无休息", "sin descanso", "sem pausa", "休憩なし"),
    "pr.custom": ("Custom…", "Своё…", "自定义…", "Otro…", "Outro…", "カスタム…"),
    "fo.free_hint": ("Free mode — finish whenever you're done", "Свободный режим — заверши, когда закончишь",
                     "自由模式 —— 完成时再结束", "Modo libre: termina cuando acabes", "Modo livre: conclua quando terminar",
                     "フリーモード — 終わったら完了"),
    "fin.title": ("Finish early?", "Завершить досрочно?", "提前完成？", "¿Terminar antes?", "Concluir antes?", "早めに終了しますか？"),
    "fin.of": ("{a} of {b}", "{a} из {b}", "已专注 {a} / {b}", "{a} de {b}", "{a} de {b}", "{b}中 {a}"),
    "fin.worked": ("You've focused for {a}", "Ты сфокусирован уже {a}", "已专注 {a}", "Llevas {a} de enfoque",
                   "Você focou por {a}", "{a} 集中しました"),
    "fin.counts": ("Your time and points will be saved.", "Время и очки сохранятся.", "时间和积分会被保存。",
                   "Se guardarán tu tiempo y tus puntos.", "Seu tempo e seus pontos serão salvos.", "時間とポイントが保存されます。"),
    "fin.short": ("Under {n} min — time is saved, but it won't count as a session.",
                  "Меньше {n} мин — время сохранится, но сессия не засчитается.",
                  "不足 {n} 分钟 —— 时间会保存，但不计为一次专注。",
                  "Menos de {n} min: se guarda el tiempo, pero no cuenta como sesión.",
                  "Menos de {n} min: o tempo é salvo, mas não conta como sessão.",
                  "{n}分未満 — 時間は保存されますが、セッションには数えません。"),
    "fin.task": ("Task done", "Задача выполнена", "任务已完成", "Tarea hecha", "Tarefa concluída", "タスク完了"),
    "fin.only": ("Just end the session", "Только завершить сессию", "仅结束本次专注", "Solo terminar la sesión",
                 "Só encerrar a sessão", "セッションのみ終了"),
    "fin.end": ("End session", "Завершить сессию", "结束专注", "Terminar sesión", "Encerrar sessão", "セッションを終了"),
    "fin.back": ("Keep going", "Продолжить", "继续", "Seguir", "Continuar", "続ける"),
    "fin.too_short": ("Too short to save", "Слишком мало, чтобы сохранить", "时间太短，未保存", "Demasiado corto",
                      "Muito curto para salvar", "短すぎて保存されません"),
    "fin.saved": ("Saved {m}  ·  +{p}", "Сохранено {m}  ·  +{p}", "已保存 {m}  ·  +{p}", "Guardado {m}  ·  +{p}",
                  "Salvo {m}  ·  +{p}", "保存 {m}  ·  +{p}"),
    "mini.saved": ("Saved {m} · +{p}", "Сохранено {m} · +{p}", "已保存 {m} · +{p}", "Guardado {m} · +{p}",
                   "Salvo {m} · +{p}", "保存 {m} · +{p}"),
    "mini.task_done": ("Task done", "Задача готова", "任务完成", "Tarea hecha", "Tarefa feita", "タスク完了"),
    "mini.only": ("Session only", "Только сессия", "仅专注", "Solo sesión", "Só sessão", "セッションのみ"),
    "ts.title": ("Time", "Время", "时间", "Tiempo", "Tempo", "時間"),
    "ts.focus": ("Focus", "Фокус", "专注时长", "Enfoque", "Foco", "集中"),
    "ts.breaks": ("Breaks", "Перерывы", "休息", "Descansos", "Pausas", "休憩"),
    "ts.breaks_sub": ("Turn off to go straight to the next focus", "Выключи, чтобы сразу идти к следующему фокусу",
                      "关闭后专注结束直接进入下一轮", "Desactiva para pasar directo al siguiente enfoque",
                      "Desative para ir direto ao próximo foco", "オフにすると次の集中へ直行"),
    "ts.flow": ("Flow mode", "Режим потока", "心流模式", "Modo flujo", "Modo fluxo", "フローモード"),
    "ts.flow_sub": ("Stopwatch with no limit; break is calculated for you", "Секундомер без лимита, перерыв считается сам",
                    "无限计时，休息时长自动计算", "Cronómetro sin límite; el descanso se calcula solo",
                    "Cronômetro sem limite; a pausa é calculada", "時間無制限。休憩は自動計算"),
    "ts.save": ("Save as preset", "Сохранить как пресет", "保存为预设", "Guardar como ajuste", "Salvar como predefinição", "プリセットとして保存"),
    "ts.remove": ("Remove this preset", "Удалить этот пресет", "删除此预设", "Quitar este ajuste", "Remover esta predefinição", "このプリセットを削除"),
    "gl.sw_tasks": ("Tasks", "Задачи", "任务", "Tareas", "Tarefas", "タスク"),
    "gl.sw_goals": ("Goals", "Цели", "目标", "Metas", "Metas", "目標"),
    "gl.title": ("Goals for today", "Цели на день", "今日目标", "Metas de hoy", "Metas de hoje", "今日の目標"),
    "gl.new": ("New goal for today", "Новая цель на сегодня", "添加今日目标", "Nueva meta para hoy", "Nova meta para hoje", "今日の新しい目標"),
    "gl.any": ("Any", "Любая", "不限", "Cualquiera", "Qualquer", "指定なし"),
    "gl.t0": ("No time", "Без времени", "不限时", "Sin tiempo", "Sem tempo", "時間なし"),
    "gl.done": ("Goal reached", "Цель достигнута", "目标达成", "Meta lograda", "Meta atingida", "目標達成"),
    "gl.auto": ("Goal reached  ·  {t}", "Цель достигнута  ·  {t}", "目标达成  ·  {t}", "Meta lograda  ·  {t}",
                "Meta atingida  ·  {t}", "目標達成  ·  {t}"),
    "gl.carry": ("Carry over yesterday's goals · {n}", "Перенести вчерашние цели · {n}", "转入昨日未完成目标 · {n}",
                 "Pasar las metas de ayer · {n}", "Trazer as metas de ontem · {n}", "昨日の目標を引き継ぐ · {n}"),
    "gl.empty": ("No goals yet", "Целей пока нет", "还没有目标", "Aún no hay metas", "Ainda sem metas", "目標はまだありません"),
    "gl.empty2": ("Add a goal — with a time and it fills itself while you focus.",
                  "Добавь цель — а если задать время, она заполнится сама, пока ты фокусируешься.",
                  "添加目标；设定时长后，专注时会自动累计。",
                  "Añade una meta: si le pones tiempo, se llena sola mientras te concentras.",
                  "Adicione uma meta: com tempo definido, ela se preenche sozinha enquanto você foca.",
                  "目標を追加。時間を設定すると、集中中に自動で進みます。"),
    "st.r_w": ("7 days", "7 дней", "7天", "7 días", "7 dias", "7日"),
    "st.r_m": ("30 days", "30 дней", "30天", "30 días", "30 dias", "30日"),
    "st.r_y": ("Year", "Год", "一年", "Año", "Ano", "1年"),
    "st.total_w": ("Focus · 7 days", "Фокус · 7 дней", "专注 · 7天", "Enfoque · 7 días", "Foco · 7 dias", "集中 · 7日間"),
    "st.total_m": ("Focus · 30 days", "Фокус · 30 дней", "专注 · 30天", "Enfoque · 30 días", "Foco · 30 dias", "集中 · 30日間"),
    "st.total_y": ("Focus · year", "Фокус · год", "专注 · 一年", "Enfoque · año", "Foco · ano", "集中 · 1年間"),
    "st.vs_w": ("vs previous week", "к прошлой неделе", "较上周", "vs semana anterior", "vs semana anterior", "先週比"),
    "st.vs_m": ("vs previous 30 days", "к прошлым 30 дням", "较前30天", "vs 30 días anteriores", "vs 30 dias anteriores", "前の30日比"),
    "st.vs_y": ("vs previous year", "к прошлому году", "较去年", "vs año anterior", "vs ano anterior", "前年比"),
    "st.nodata": ("Not enough data yet", "Пока мало данных", "暂无足够数据", "Aún hay pocos datos", "Ainda há poucos dados", "データがまだ足りません"),
    "st.avg_active": ("Average", "Среднее", "日均", "Media", "Média", "平均"),
    "st.best_day": ("Best day", "Лучший день", "最佳一天", "Mejor día", "Melhor dia", "ベストの日"),
    "st.peak": ("peak", "пик", "峰值", "máx.", "pico", "最大"),
    "st.bars": ("Focus time", "Время фокуса", "专注时间", "Tiempo de enfoque", "Tempo de foco", "集中時間"),
    "st.cats": ("By category", "По категориям", "按分类", "Por categoría", "Por categoria", "カテゴリ別"),
    "st.points": ("Points", "Очки", "积分", "Puntos", "Pontos", "ポイント"),
    "st.level_now": ("Level {l} · {t}", "Уровень {l} · {t}", "{l} 级 · {t}", "Nivel {l} · {t}", "Nível {l} · {t}", "Lv.{l} · {t}"),
    "st.pts_u": ("pts", "очк.", "分", "pts", "pts", "pt"),
    "st.heat": ("Activity", "Активность", "活跃度", "Actividad", "Atividade", "アクティビティ"),
    "st.active_days": ("{n} active days", "{n} активных дней", "{n} 个活跃日", "{n} días activos", "{n} dias ativos", "稼働 {n} 日"),
    "st.less": ("Less", "Меньше", "少", "Menos", "Menos", "少"),
    "st.more": ("More", "Больше", "多", "Más", "Mais", "多"),
    "st.hours": ("When you focus best", "Когда ты лучше всего в фокусе", "最佳专注时段", "Cuándo te concentras mejor",
                 "Quando você foca melhor", "集中できる時間帯"),
    "st.best_time": ("Best window: {a} – {b}", "Лучшее время: {a} – {b}", "最佳时段：{a} – {b}", "Mejor franja: {a} – {b}",
                     "Melhor janela: {a} – {b}", "ベストの時間帯：{a} – {b}"),
    "st.rec_streak": ("Longest streak", "Лучшая серия", "最长连续", "Mejor racha", "Maior sequência", "最長連続"),
    "st.avg_sess": ("Avg session", "Средняя сессия", "平均时长", "Sesión media", "Sessão média", "平均セッション"),
    "st.rec_early": ("Early finishes", "Досрочно", "提前完成", "Terminadas antes", "Concluídas antes", "早期完了"),
    "st.rec_early_u": ("sessions", "сессий", "次", "sesiones", "sessões", "回"),
    "rule.title": ("How points work", "Как начисляются очки", "积分如何计算", "Cómo se ganan puntos", "Como ganhar pontos", "ポイントの仕組み"),
    "rule.sub": ("Honest focus counts, not button-clicking", "Считается честная работа, а не нажатия кнопок",
                 "看重真实专注，而非点击", "Cuenta el enfoque real, no los clics", "Conta o foco real, não os cliques",
                 "ボタン操作でなく、実際の集中が評価されます"),
    "rule.focus": ("Focus time", "Время фокуса", "专注时间", "Tiempo de enfoque", "Tempo de foco", "集中時間"),
    "rule.streak": ("Day streak bonus (max)", "Бонус за серию дней (макс.)", "连续天数加成（上限）", "Bono por racha (máx.)",
                    "Bônus de sequência (máx.)", "連続日ボーナス（最大）"),
    "rule.session": ("Session of 10+ min", "Сессия от 10 мин", "10分钟以上的专注", "Sesión de 10+ min", "Sessão de 10+ min", "10分以上のセッション"),
    "rule.deep": ("Deep session of 50+ min", "Глубокая сессия от 50 мин", "50分钟以上的深度专注", "Sesión profunda de 50+ min",
                  "Sessão profunda de 50+ min", "50分以上の深い集中"),
    "rule.task": ("Task (more if you worked on it)", "Задача (больше, если работал над ней)", "任务（投入越多越高）",
                  "Tarea (más si trabajaste en ella)", "Tarefa (mais se trabalhou nela)", "タスク（取り組むほど多い）"),
    "rule.early": ("Finished ahead of plan", "Опередил план", "提前完成计划", "Adelantaste el plan", "Adiantou o plano", "予定より早く完了"),
    "rule.goal": ("Daily goal / timed goal", "Цель дня / цель со временем", "今日目标 / 限时目标", "Meta del día / con tiempo",
                  "Meta do dia / com tempo", "今日の目標 / 時間付き"),
    "rule.day": ("Daily focus norm reached", "Дневная норма фокуса", "达成每日专注目标", "Meta diaria de enfoque",
                 "Meta diária de foco", "1日の集中目標達成"),
    "rule.week": ("Weekly goal reached", "Цель недели достигнута", "达成每周目标", "Meta semanal lograda", "Meta semanal atingida", "週間目標達成"),
    "rule.note": ("Beyond 2× your daily norm minutes count half — rest is part of the work.",
                  "После 2× дневной нормы минуты весят вдвое меньше — отдых тоже часть работы.",
                  "超过每日目标2倍后，分钟只按一半计 —— 休息也是工作的一部分。",
                  "Pasado 2× tu meta diaria, los minutos valen la mitad: descansar también es trabajar.",
                  "Acima de 2× sua meta diária, os minutos valem metade: descansar também é trabalho.",
                  "1日の目標の2倍を超えた分は半分で計算。休むことも仕事のうちです。"),
    "st.mini": ("Mini panel", "Мини-панель", "迷你面板", "Mini panel", "Mini painel", "ミニパネル"),
    "s.flow_ratio": ("Flow break = 1/N of focus", "Перерыв в потоке = 1/N фокуса", "心流休息 = 专注的 1/N",
                     "Descanso en flujo = 1/N del enfoque", "Pausa no fluxo = 1/N do foco", "フロー休憩 = 集中の1/N"),
    "s.min_session": ("Min. minutes to count a session", "Минимум минут для зачёта сессии", "计为一次专注的最少分钟",
                      "Mín. de minutos para contar sesión", "Mín. de minutos para contar sessão", "セッションと数える最小分数"),
    "s.confirm_finish": ("Ask when finishing early", "Спрашивать при досрочном завершении", "提前完成时询问",
                         "Preguntar al terminar antes", "Perguntar ao concluir antes", "早期終了時に確認"),
    "s.mini_snap": ("Magnet to screen edges", "Магнит к краям экрана", "吸附屏幕边缘", "Imán a los bordes", "Ímã nas bordas", "画面端に吸着"),
    "s.mini_opacity": ("Mini panel when idle", "Прозрачность мини-панели в покое", "迷你面板空闲不透明度",
                       "Opacidad del mini panel en reposo", "Opacidade do mini painel em repouso", "待機時のミニパネル不透明度"),
    "tray.finish": ("Finish early", "Завершить досрочно", "提前完成", "Terminar antes", "Concluir antes", "早めに終了"),
    "ach.gl1": ("Goal setter", "Целеустремлённый", "目标达人", "Con metas", "Com metas", "目標達成者"),
    "ach.gl1.d": ("Complete a goal for the day", "Выполни цель дня", "完成一个今日目标", "Cumple una meta del día",
                  "Cumpra uma meta do dia", "今日の目標を1つ達成"),
    "ach.gl25": ("Goal machine", "Машина целей", "目标机器", "Máquina de metas", "Máquina de metas", "目標マシン"),
    "ach.gl25.d": ("Complete 25 daily goals", "Выполни 25 целей дня", "完成25个今日目标", "Cumple 25 metas del día",
                   "Cumpra 25 metas do dia", "今日の目標を25個達成"),
    "ach.fin5": ("Ahead of schedule", "Опережая график", "提前量", "Por delante", "Adiantado", "予定より先に"),
    "ach.fin5.d": ("Finish 5 sessions early", "Заверши досрочно 5 сессий", "提前完成5次专注", "Termina 5 sesiones antes",
                   "Conclua 5 sessões antes", "5回のセッションを早期完了"),
    "ach.flow": ("In the flow", "В потоке", "沉浸心流", "En el flujo", "No fluxo", "フロー状態"),
    "ach.flow.d": ("Flow session of 60+ minutes", "Сессия в режиме потока от 60 мин", "心流模式专注60分钟以上",
                   "Sesión en modo flujo de 60+ min", "Sessão em modo fluxo de 60+ min", "フローモードで60分以上"),
})


# ───────────────────────────── data store ─────────────────────────────
DEFAULT_SETTINGS = dict(
    focus=25, short=5, long=15, cycles=4, goal=120, week_start="mon",
    auto_break=True, auto_focus=True, end_warn=True, notify=True, title_time=True,
    on_top=False, popup_end=False, mini_min=True, autostart=False,
    sound=True, volume=70, sound_focus="chime", sound_break="drop",
    theme="light", accent="graphite", ticks=True, opacity=100, animations=True,
    lang="", mini_x=-1, mini_y=-1, mini_dock="", mini_snap=True, mini_opacity=85,
    breaks=True, free_focus=False, flow_ratio=5, min_session=5, confirm_finish=True)
DEFAULT_CATEGORIES = [
    {"id": "study", "name": "Study", "color": "#7D96F0"}, {"id": "games", "name": "Games", "color": "#A685E8"},
    {"id": "design", "name": "Design", "color": "#E8829F"}, {"id": "work", "name": "Work", "color": "#62B0A0"},
    {"id": "money", "name": "Finance", "color": "#D9B25F"}, {"id": "sport", "name": "Sport", "color": "#EE8F62"},
    {"id": "reading", "name": "Reading", "color": "#78B7DB"}, {"id": "home", "name": "Home", "color": "#9BBF7A"},
    {"id": "other", "name": "Other", "color": "#8E8E93"}]
CAT_COLORS = ["#7D96F0", "#A685E8", "#E8829F", "#62B0A0", "#D9B25F", "#EE8F62", "#78B7DB", "#9BBF7A", "#C07DD6", "#6FA8A0"]
# (id, glyph)  — glyph "icon:xxx" рисуется иконкой
ACH = [("first", "1"), ("hour", "60"), ("ten", "10"), ("s3", "3d"), ("s7", "7d"), ("deep", "50"), ("five", "5h"),
       ("close", "icon:check"), ("s30", "30d"), ("h25", "25h"), ("h100", "100h"), ("se25", "25"), ("se100", "100"),
       ("t25", "25"), ("t100", "100"), ("early", "icon:sun"), ("night", "icon:moon"), ("daygoal", "icon:target"),
       ("wk1", "icon:flag"), ("lv5", "icon:star"),
       ("gl1", "G1"), ("gl25", "G25"), ("fin5", "5×"), ("flow", "∞")]


def today():
    return date.today().isoformat()


XP_VER = 3


def level_xp(l):
    return int(round(40 * (max(l, 1) - 1) ** 1.9))


def level_of(xp):
    xp = max(float(xp), 0.0)
    l = int((xp / 40.0) ** (1 / 1.9)) + 1
    while level_xp(l + 1) <= xp:
        l += 1
    while l > 1 and level_xp(l) > xp:
        l -= 1
    return l


def level_bounds(l):
    return level_xp(l), level_xp(l + 1)


def data_dir():
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    d = Path(base) / "GraphiteTime"
    d.mkdir(parents=True, exist_ok=True)
    return d


def week_start_of(d, ws):
    off = d.weekday() if ws == "mon" else (d.weekday() + 1) % 7
    return d - timedelta(days=off)


def default_data():
    return {"profile": {"name": "", "xp": 0.0, "xp_ver": XP_VER}, "settings": dict(DEFAULT_SETTINGS),
            "categories": [dict(c) for c in DEFAULT_CATEGORIES], "tasks": [], "history": {},
            "achievements": {}, "current_task": None, "flags": {},
            "weekly": {"title": "", "target": 0, "cat": None, "week": "", "hit": False},
            "weekly_log": [], "supporters": None, "goals": [], "presets": []}


class Store(QObject):
    changed = Signal(str)
    levelup = Signal(int)
    unlocked = Signal(str)
    goal_hit = Signal()
    goal_done = Signal(str)

    def __init__(self):
        super().__init__()
        self.path = data_dir() / "data.json"
        self.d = default_data()
        try:
            raw = json.loads(self.path.read_text("utf-8"))
            for k, v in raw.items():
                if k == "settings" and isinstance(v, dict):
                    self.d["settings"].update({a: b for a, b in v.items() if a in DEFAULT_SETTINGS})
                    if "auto_next" in v:
                        self.d["settings"]["auto_break"] = self.d["settings"]["auto_focus"] = bool(v["auto_next"])
                elif k in ("profile", "weekly") and isinstance(v, dict):
                    self.d[k].update(v)
                elif k in self.d:
                    self.d[k] = v
        except Exception:
            pass
        self._migrate()
        self.avatar = None
        self._load_avatar()
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(600)
        self._t.timeout.connect(self.save)

    def _migrate(self):
        pr = self.d["profile"]
        if pr.get("xp_ver") != XP_VER:
            xp = 0.0
            for h in self.d["history"].values():
                v = h.get("focus", 0) + 5 * h.get("sessions", 0) + 8 * h.get("done", 0)
                h["xp"] = round(v, 1)
                xp += v
            pr["xp"], pr["xp_ver"] = round(xp, 1), XP_VER
        cut = (date.today() - timedelta(days=45)).isoformat()
        self.d["goals"] = [g for g in self.d.get("goals", []) if g.get("day", "") >= cut]
        if not isinstance(self.d.get("presets"), list):
            self.d["presets"] = []

    def save(self):
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), "utf-8")
            os.replace(tmp, self.path)
        except Exception:
            pass

    def touch(self, topic):
        self.changed.emit(topic)
        self._t.start()

    # settings
    def s(self, k):
        return self.d["settings"][k]

    def set_setting(self, k, v):
        self.d["settings"][k] = v
        if k == "lang":
            set_lang(v)
        self.touch("appearance" if k in ("theme", "accent") else "lang" if k == "lang" else "settings")

    def update_settings(self, dct):
        self.d["settings"].update(dct)
        self.touch("settings")

    def set_name(self, n):
        self.d["profile"]["name"] = n.strip()
        self.touch("profile")

    # presets (user)
    PRESET_KEYS = ("focus", "short", "long", "cycles", "breaks", "free_focus")

    def cur_preset(self):
        return {k: self.s(k) for k in self.PRESET_KEYS}

    def preset_index(self):
        cur = self.cur_preset()
        return next((i for i, p in enumerate(self.d["presets"]) if all(p.get(k) == cur[k] for k in cur)), -1)

    def toggle_preset(self):
        i = self.preset_index()
        if i >= 0:
            self.d["presets"].pop(i)
        elif len(self.d["presets"]) < 6:
            self.d["presets"].append(self.cur_preset())
        self.touch("presets")
        return i < 0

    # avatar
    def _load_avatar(self):
        p = data_dir() / "avatar.png"
        self.avatar = QPixmap(str(p)) if p.exists() else None
        if self.avatar is not None and self.avatar.isNull():
            self.avatar = None

    def set_avatar(self, path):
        img = QImage(path)
        if img.isNull():
            return False
        s = min(img.width(), img.height())
        img = img.copy((img.width() - s) // 2, (img.height() - s) // 2, s, s)
        img = img.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        img.save(str(data_dir() / "avatar.png"), "PNG")
        self._load_avatar()
        self.touch("profile")
        return True

    def clear_avatar(self):
        try:
            (data_dir() / "avatar.png").unlink()
        except OSError:
            pass
        self.avatar = None
        self.touch("profile")

    # categories
    def cat(self, cid):
        for c in self.d["categories"]:
            if c["id"] == cid:
                return c
        return self.d["categories"][-1]

    def add_category(self, name, color):
        self.d["categories"].insert(len(self.d["categories"]) - 1,
                                    {"id": uuid.uuid4().hex[:8], "name": name.strip(), "color": color})
        self.touch("categories")

    def remove_category(self, cid):
        if cid == "other":
            return
        self.d["categories"] = [c for c in self.d["categories"] if c["id"] != cid]
        for t in self.d["tasks"]:
            if t["cat"] == cid:
                t["cat"] = "other"
        for g in self.d["goals"]:
            if g.get("cat") == cid:
                g["cat"] = None
        if self.d["weekly"].get("cat") == cid:
            self.d["weekly"]["cat"] = None
        self.touch("categories")
        self.touch("tasks")
        self.touch("goals")

    # points
    def mult(self):
        return 1.0 + 0.02 * min(self.streak(), 20)

    def award(self, v, key=None):
        """Начислить (или снять) очки. Возвращает реально изменённое значение."""
        if not v:
            return 0.0
        pr = self.d["profile"]
        before = level_of(pr["xp"])
        new = max(0.0, pr["xp"] + v)
        real = new - pr["xp"]
        pr["xp"] = round(new, 2)
        d = self.day(key or today(), True)
        d["xp"] = round(max(0.0, d.get("xp", 0.0) + real), 2)
        if level_of(pr["xp"]) > before:
            self.levelup.emit(level_of(pr["xp"]))
        return real

    # tasks
    def task(self, tid):
        return next((t for t in self.d["tasks"] if t["id"] == tid), None)

    def add_task(self, title, cat):
        t = {"id": uuid.uuid4().hex[:10], "title": title.strip(), "cat": cat, "done": False,
             "created": datetime.now().isoformat(timespec="seconds"), "done_at": None, "focus": 0.0}
        self.d["tasks"].insert(0, t)
        if not self.d["current_task"]:
            self.d["current_task"] = t["id"]
        self.touch("tasks")
        return t

    def toggle_task(self, tid, early=False):
        t = self.task(tid)
        if not t:
            return False
        self.last_gain = 0.0
        if not t["done"]:
            t["done"], t["done_at"] = True, datetime.now().isoformat(timespec="seconds")
            self.day(today(), True)["done"] += 1
            pts = 6 + min(14.0, t.get("focus", 0) / 3.0) + (8 if early else 0)
            t["xp"] = round(self.award(pts), 2)
            self.last_gain = t["xp"]
            if self.d["current_task"] == tid:
                self.d["current_task"] = None
        else:
            k = (t["done_at"] or "")[:10]
            t["done"], t["done_at"] = False, None
            if k in self.d["history"]:
                self.d["history"][k]["done"] = max(0, self.d["history"][k]["done"] - 1)
            self.award(-t.pop("xp", 0.0) if t.get("xp") else -15.0, k or None)
        self.check_achievements()
        self.touch("tasks")
        self.touch("stats")
        return t["done"]

    def remove_task(self, tid):
        self.d["tasks"] = [t for t in self.d["tasks"] if t["id"] != tid]
        if self.d["current_task"] == tid:
            self.d["current_task"] = None
        self.touch("tasks")

    def set_current(self, tid):
        self.d["current_task"] = None if self.d["current_task"] == tid else tid
        self.touch("tasks")

    def visible_tasks(self, cat):
        ts = [t for t in self.d["tasks"] if cat in (None, "all") or t["cat"] == cat]
        return [t for t in ts if not t["done"]] + sorted([t for t in ts if t["done"]],
                                                         key=lambda t: t["done_at"] or "", reverse=True)

    def today_progress(self):
        k = today()
        done = sum(1 for t in self.d["tasks"] if t["done"] and (t["done_at"] or "")[:10] == k)
        return done, done + sum(1 for t in self.d["tasks"] if not t["done"])

    # daily goals
    def today_goals(self):
        k = today()
        gs = [g for g in self.d["goals"] if g["day"] == k]
        return [g for g in gs if not g["done"]] + sorted([g for g in gs if g["done"]],
                                                         key=lambda g: g["done_at"] or "", reverse=True)

    def add_goal(self, title, cat, target):
        g = {"id": uuid.uuid4().hex[:10], "title": title.strip(), "cat": None if cat in (None, "all") else cat,
             "target": int(target), "spent": 0.0, "done": False, "day": today(), "done_at": None}
        self.d["goals"].insert(0, g)
        self.touch("goals")
        return g

    def _finish_goal(self, g, undo=False):
        k = today()
        if not undo:
            g["done"], g["done_at"] = True, datetime.now().isoformat(timespec="seconds")
            self.day(k, True)["goals"] = self.day(k, True).get("goals", 0) + 1
            g["xp"] = round(self.award(12 if g["target"] > 0 else 8), 2)
        else:
            dk = (g["done_at"] or k)[:10]
            g["done"], g["done_at"] = False, None
            if dk in self.d["history"]:
                h = self.d["history"][dk]
                h["goals"] = max(0, h.get("goals", 0) - 1)
            self.award(-g.pop("xp", 0.0), dk)

    def toggle_goal(self, gid):
        g = next((x for x in self.d["goals"] if x["id"] == gid), None)
        if not g:
            return False
        self._finish_goal(g, undo=g["done"])
        self.check_achievements()
        self.touch("goals")
        self.touch("stats")
        return g["done"]

    def remove_goal(self, gid):
        self.d["goals"] = [g for g in self.d["goals"] if g["id"] != gid]
        self.touch("goals")

    def stale_goals(self):
        y = (date.today() - timedelta(days=1)).isoformat()
        return [g for g in self.d["goals"] if g["day"] == y and not g["done"]]

    def carry_over(self):
        n = 0
        for g in self.stale_goals():
            g["day"], g["spent"] = today(), 0.0
            n += 1
        self.touch("goals")
        return n

    def goals_done_today(self):
        gs = [g for g in self.d["goals"] if g["day"] == today()]
        return sum(1 for g in gs if g["done"]), len(gs)

    # stats
    def day(self, key, create=False):
        h = self.d["history"]
        if key not in h:
            if not create:
                return {"focus": 0.0, "sessions": 0, "done": 0, "xp": 0.0, "goals": 0, "early": 0}
            h[key] = {"focus": 0.0, "sessions": 0, "done": 0, "xp": 0.0, "goals": 0, "early": 0}
        return h[key]

    def add_focus(self, minutes, session, task_id=None, early=False, planned=0.0, free=False):
        """Записать время фокуса и начислить очки. Возвращает начисленные очки."""
        if minutes <= 0:
            return 0.0
        k = today()
        d = self.day(k, True)
        before = d["focus"]
        d["focus"] = round(before + minutes, 3)
        if session:
            d["sessions"] += 1
            if early:
                d["early"] = d.get("early", 0) + 1
        t = self.task(task_id) if task_id else None
        cid = t["cat"] if t else "other"
        cats = d.setdefault("cats", {})
        cats[cid] = round(cats.get(cid, 0) + minutes, 3)
        hrs = d.setdefault("hours", {})
        hk = str(datetime.now().hour)
        hrs[hk] = round(hrs.get(hk, 0) + minutes, 3)
        if t:
            t["focus"] = round(t.get("focus", 0) + minutes, 3)
        fl = self.d["flags"]
        if session:
            h = datetime.now().hour
            if 4 <= h < 8:
                fl["early"] = True
            if h >= 23 or h < 4:
                fl["night"] = True
            if early:
                fl["early_fin"] = fl.get("early_fin", 0) + 1
        if free and minutes >= 60:
            fl["flow"] = True
        # цели дня со временем
        for g in self.d["goals"]:
            if g["day"] == k and not g["done"] and g["target"] > 0 and g.get("cat") in (None, cid):
                g["spent"] = round(g.get("spent", 0) + minutes, 3)
                if g["spent"] >= g["target"]:
                    self._finish_goal(g)
                    self.goal_done.emit(g["title"])
        # очки
        goal = max(1, self.s("goal"))
        full = max(0.0, min(minutes, 2 * goal - before))
        pts = (full + 0.5 * (minutes - full)) * self.mult()
        if session and minutes >= 10:
            pts += 5
        if session and minutes >= 50:
            pts += 5
        gained = self.award(pts)
        if before < goal <= d["focus"] and not d.get("goal_bonus"):
            d["goal_bonus"] = True
            gained += self.award(20)
        self.check_goal()
        self.check_achievements(deep=session and minutes >= 50)
        self.touch("stats")
        self.touch("tasks")
        self.touch("goals")
        return gained

    def active(self, key):
        d = self.d["history"].get(key)
        return bool(d and (d["focus"] >= 1 or d["done"] > 0 or d["sessions"] > 0 or d.get("goals", 0) > 0))

    def streak(self):
        n, day = 0, date.today()
        if not self.active(day.isoformat()):
            day -= timedelta(days=1)
        while self.active(day.isoformat()):
            n += 1
            day -= timedelta(days=1)
        return n

    def longest_streak(self):
        keys = sorted(k for k in self.d["history"] if self.active(k))
        best = cur = 0
        prev = None
        for k in keys:
            dd = date.fromisoformat(k)
            cur = cur + 1 if prev and (dd - prev).days == 1 else 1
            best, prev = max(best, cur), dd
        return best

    def best_day(self):
        h = self.d["history"]
        if not h:
            return None, 0.0
        k = max(h, key=lambda x: h[x]["focus"])
        return (k, h[k]["focus"]) if h[k]["focus"] > 0 else (None, 0.0)

    def totals(self):
        h = self.d["history"].values()
        return sum(x["focus"] for x in h), sum(x["sessions"] for x in h), sum(x["done"] for x in h)

    def early_total(self):
        return sum(x.get("early", 0) for x in self.d["history"].values())

    def span(self, n, offset=0):
        """n последних дней (старые → новые), сдвиг offset дней назад. [(date, dict)]"""
        out = []
        for i in range(n - 1 + offset, offset - 1, -1):
            d = date.today() - timedelta(days=i)
            out.append((d, self.day(d.isoformat())))
        return out

    def months(self, n=12):
        """n последних месяцев: [(first_day, focus, xp, sessions)]"""
        out, y, m = [], date.today().year, date.today().month
        for _ in range(n):
            out.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        res = []
        for (y, m) in reversed(out):
            pre = f"{y:04d}-{m:02d}"
            ds = [v for k, v in self.d["history"].items() if k.startswith(pre)]
            res.append((date(y, m, 1), sum(v["focus"] for v in ds), sum(v.get("xp", 0) for v in ds),
                        sum(v["sessions"] for v in ds)))
        return res

    def cat_totals(self, days):
        out = {}
        for _, v in days:
            for c, m in v.get("cats", {}).items():
                out[c] = out.get(c, 0.0) + m
        return out

    def hour_totals(self):
        out = [0.0] * 24
        for v in self.d["history"].values():
            for h, m in v.get("hours", {}).items():
                if h.isdigit() and 0 <= int(h) < 24:
                    out[int(h)] += m
        return out

    def week(self):
        return [(d, v["focus"]) for d, v in self.span(7)]

    def index(self):
        goal = max(1, self.s("goal"))
        days = [(date.today() - timedelta(days=i)).isoformat() for i in range(7)]
        focus = sum(min(1.0, self.day(k)["focus"] / goal) for k in days) / 7
        act = sum(1 for k in days if self.active(k)) / 7
        done = min(1.0, sum(self.day(k)["done"] + self.day(k).get("goals", 0) for k in days) / 10.0)
        return 50 * focus + 30 * act + 20 * done, focus, act, done

    # weekly goal
    def wk_start(self):
        return week_start_of(date.today(), self.s("week_start"))

    def goal_day_minutes(self, d):
        day = self.day(d.isoformat())
        cat = self.d["weekly"].get("cat")
        return day.get("cats", {}).get(cat, 0.0) if cat else day["focus"]

    def week_goal_days(self):
        s = self.wk_start()
        return [(s + timedelta(days=i), self.goal_day_minutes(s + timedelta(days=i))) for i in range(7)]

    def roll_week(self):
        w, cur = self.d["weekly"], self.wk_start().isoformat()
        if w.get("week") != cur:
            if w.get("week") and w.get("target", 0) > 0:
                self.d["weekly_log"] = (self.d["weekly_log"] + [{"week": w["week"], "title": w["title"],
                                                                 "target": w["target"], "hit": bool(w.get("hit"))}])[-12:]
            w["week"], w["hit"] = cur, False

    def goal_progress(self):
        self.roll_week()
        return sum(m for _, m in self.week_goal_days()), self.d["weekly"].get("target", 0)

    def set_weekly(self, **kw):
        self.roll_week()
        self.d["weekly"].update(kw)
        if "target" in kw or "cat" in kw:
            self.d["weekly"]["hit"] = False
            self.check_goal()
        self.touch("goal")
        self.touch("stats")

    def check_goal(self):
        done, target = self.goal_progress()
        w = self.d["weekly"]
        if target > 0 and not w.get("hit") and done >= target:
            w["hit"] = True
            if w.get("counted") != w["week"]:
                w["counted"] = w["week"]
                self.d["flags"]["goal_hits"] = self.d["flags"].get("goal_hits", 0) + 1
                self.award(100)
                self.goal_hit.emit()
            self.check_achievements()

    def check_achievements(self, deep=False):
        a, fl = self.d["achievements"], self.d["flags"]
        tf, ss, dn = self.totals()
        dd, tt = self.today_progress()
        st = self.streak()
        gl = sum(v.get("goals", 0) for v in self.d["history"].values())
        conds = {"first": ss >= 1, "hour": tf >= 60, "ten": dn >= 10, "s3": st >= 3, "s7": st >= 7, "deep": deep,
                 "five": tf >= 300, "close": tt >= 3 and dd == tt, "s30": st >= 30, "h25": tf >= 1500,
                 "h100": tf >= 6000, "se25": ss >= 25, "se100": ss >= 100, "t25": dn >= 25, "t100": dn >= 100,
                 "early": bool(fl.get("early")), "night": bool(fl.get("night")),
                 "daygoal": self.day(today())["focus"] >= self.s("goal"), "wk1": fl.get("goal_hits", 0) >= 1,
                 "lv5": level_of(self.d["profile"]["xp"]) >= 5,
                 "gl1": gl >= 1, "gl25": gl >= 25, "fin5": fl.get("early_fin", 0) >= 5, "flow": bool(fl.get("flow"))}
        for k, ok in conds.items():
            if ok and k not in a:
                a[k] = datetime.now().isoformat(timespec="seconds")
                self.unlocked.emit(k)

    def reset_stats(self):
        self.d["history"], self.d["achievements"], self.d["flags"] = {}, {}, {}
        self.d["profile"]["xp"] = 0.0
        for t in self.d["tasks"]:
            t["focus"] = 0.0
            t.pop("xp", None)
        for g in self.d["goals"]:
            g["spent"] = 0.0
            g.pop("xp", None)
        self.touch("stats")
        self.touch("tasks")
        self.touch("goals")

    def reset_all(self):
        lang = self.s("lang")
        self.clear_avatar()
        self.d = default_data()
        self.d["settings"]["lang"] = lang
        self.touch("all")

    def export(self, path):
        Path(path).write_text(json.dumps(self.d, ensure_ascii=False, indent=1), "utf-8")


# ───────────────────────────── sounds ─────────────────────────────
SOUND_IDS = ["chime", "bell", "glass", "drop", "pulse", "soft"]
_H = [(1, 1.0), (2, 0.25), (3, 0.08)]
_SOUNDS = {
    "chime": ([(1046.5, 0.00, 0.9), (1318.5, 0.11, 0.9), (1568.0, 0.22, 1.4)], _H, 0.004),
    "bell": ([(880.0, 0.0, 2.0)], [(1, 1.0), (2.76, 0.45), (5.4, 0.2), (8.9, 0.08)], 0.002),
    "glass": ([(1760.0, 0.0, 1.5), (2637.0, 0.0, 1.2)], [(1, 1.0), (2, 0.1)], 0.01),
    "drop": ([(988.0, 0.0, 0.5), (659.3, 0.17, 0.8)], [(1, 1.0), (2, 0.12)], 0.003),
    "pulse": ([(660.0, 0.0, 0.16), (660.0, 0.2, 0.16), (880.0, 0.4, 0.3)], [(1, 1.0), (2, 0.15)], 0.003),
    "soft": ([(523.3, 0.0, 1.4), (659.3, 0.08, 1.4)], [(1, 1.0), (2, 0.18)], 0.06),
}
_qt_sounds = []


def _wav_path(sid, vol):
    d = data_dir() / "sounds"
    d.mkdir(exist_ok=True)
    p = d / f"{sid}_{vol}.wav"
    if not p.exists():
        notes, partials, attack = _SOUNDS.get(sid, _SOUNDS["chime"])
        sr = 22050
        n = int((max(s + dd for _, s, dd in notes) + 0.1) * sr)
        buf = [0.0] * n
        for f, s, dd in notes:
            i0, m = int(s * sr), int(dd * sr)
            for k, (mult, amp) in enumerate(partials):
                w, decay = 2 * math.pi * f * mult / sr, 5.0 / (dd * (1 + 0.6 * k))
                for i in range(m):
                    t = i / sr
                    buf[i0 + i] += amp * min(1.0, t / attack) * math.exp(-decay * t) * math.sin(w * i)
        peak = max(1e-9, max(abs(x) for x in buf))
        sc = 32767 * 0.85 * (vol / 100.0) / peak
        data = array.array("h", (int(x * sc) for x in buf))
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(data.tobytes())
    return p


def play_sound(sid, volume):
    vol = int(clamp(volume, 0, 100) // 10 * 10)
    if vol <= 0:
        return

    def run():
        try:
            p = _wav_path(sid, vol)
            if winsound:
                winsound.PlaySound(str(p), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                QTimer.singleShot(0, lambda: _qt_play(p))
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def _qt_play(p):
    try:
        from PySide6.QtMultimedia import QSoundEffect
        e = QSoundEffect()
        e.setSource(QUrl.fromLocalFile(str(p)))
        e.play()
        _qt_sounds[:] = (_qt_sounds + [e])[-4:]
    except Exception:
        QApplication.beep()


def set_autostart(on):
    if sys.platform != "win32":
        return
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_SET_VALUE)
        if on:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}"'
            else:
                py = Path(sys.executable).with_name("pythonw.exe")
                cmd = f'"{py if py.exists() else sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, "GraphiteTime", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "GraphiteTime")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


# ───────────────────────────── timer engine ─────────────────────────────
class Engine(QObject):
    tick = Signal()
    state = Signal()
    completed = Signal(str)
    warning = Signal()
    finished_early = Signal(float, float, bool)      # минут, очков, закрыта ли задача

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.mode, self.running, self.cycle, self.warned = "focus", False, 0, False
        self.base, self.t0, self.free, self.total = 0.0, 0.0, False, 0.0
        self.last_gain = 0.0
        self._flow_el = 0.0
        self._flow_override = False
        self._setup()
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_tick)

    # --- модель времени ---
    @property
    def elapsed(self):
        return self.base + (time.monotonic() - self.t0 if self.running else 0.0)

    @property
    def remaining(self):
        """Секунды для показа: остаток (обычный режим) или прошедшее время (свободный режим)."""
        return self.elapsed if self.free else max(0.0, self.total - self.elapsed)

    @property
    def prog(self):
        if self.free:
            return (self.elapsed % 3600.0) / 3600.0
        return 0.0 if self.total <= 0 else clamp(self.elapsed / self.total)

    @property
    def started(self):
        return self.running or self.base > 0.05

    def duration(self, mode):
        return float(self.store.s(mode)) * 60.0

    def _setup(self):
        self.free = self.mode == "focus" and bool(self.store.s("free_focus"))
        self.total = 0.0 if self.free else self.duration(self.mode)
        self.base, self.warned = 0.0, False

    # --- управление ---
    def start(self):
        if self.running or (not self.free and self.elapsed >= self.total):
            return
        self.t0 = time.monotonic()
        self.running = True
        self.warned = (not self.free) and self.remaining <= 60
        self._timer.start()
        self.state.emit()

    def pause(self):
        if not self.running:
            return
        self.base = self.elapsed
        self.running = False
        self._timer.stop()
        self.state.emit()
        self.tick.emit()

    def toggle(self):
        self.pause() if self.running else self.start()

    def reset(self):
        self._timer.stop()
        self.running = False
        self.base = 0.0
        self.warned = False
        self.state.emit()
        self.tick.emit()

    def extend(self, minutes):
        """Добавить (или убрать) минуты у текущего отрезка."""
        if self.free:
            return
        self.total = max(self.elapsed + 30.0, self.total + minutes * 60.0)
        self.warned = self.remaining <= 60
        self.state.emit()
        self.tick.emit()

    def skip(self):
        """Фокус: завершить досрочно (только время). Перерыв: пропустить."""
        if self.mode == "focus":
            self.finish_early(False)
            return
        self._timer.stop()
        self.running = False
        self._advance(self.mode)

    def finish_early(self, task_done=False):
        """Досрочное завершение фокус-сессии: время и очки сохраняются, задачу можно закрыть."""
        if self.mode != "focus":
            self.skip()
            return 0.0
        st = self.store
        if not self.started and not task_done:
            return 0.0
        el = self.elapsed
        mins = el / 60.0
        self._timer.stop()
        self.running = False
        sid = st.d.get("current_task")
        session = mins >= st.s("min_session")
        planned = 0.0 if self.free else self.total / 60.0
        gain, closed = 0.0, False
        if mins >= 1.0:
            gain += st.add_focus(mins, session, sid, early=True, planned=planned, free=self.free)
        if task_done and sid and st.task(sid) and not st.task(sid)["done"]:
            st.toggle_task(sid, early=(planned > 0 and mins < planned * 0.8))
            gain += st.last_gain
            closed = True
        self.last_gain = gain
        self.finished_early.emit(mins, gain, closed)
        if mins < 1.0 and not closed:
            self.reset()
            return 0.0
        if session:
            self.cycle += 1
        was_free = self.free
        self._flow_el = el if was_free else 0.0
        self._advance("focus")
        if st.s("breaks") and st.s("auto_break"):
            QTimer.singleShot(1400, self._auto)
        return mins

    def apply_settings(self):
        if not self.started:
            if self.mode != "focus" and not self.store.s("breaks"):
                self.mode = "focus"
                self._flow_override = False
            if not (self._flow_override and self.mode != "focus"):
                self._setup()
        self.state.emit()
        self.tick.emit()

    # --- ход времени ---
    def _on_tick(self):
        self.tick.emit()
        if self.free:
            return
        rem = self.total - self.elapsed
        if (not self.warned and self.mode == "focus" and self.total >= 180 and rem <= 60
                and self.store.s("end_warn")):
            self.warned = True
            self.warning.emit()
        if rem <= 0.0:
            self._finish()

    def _finish(self):
        self._timer.stop()
        self.running = False
        mode = self.mode
        if mode == "focus":
            self.last_gain = self.store.add_focus(self.total / 60.0, True, self.store.d.get("current_task"))
            self.cycle += 1
        self.completed.emit(mode)
        self._flow_el = 0.0
        self._advance(mode)
        if self.store.s("breaks"):
            if self.store.s("auto_break" if mode == "focus" else "auto_focus"):
                QTimer.singleShot(1400, self._auto)

    def _auto(self):
        if not self.running and not self.started:
            self.start()

    def _advance(self, prev):
        s = self.store
        n = s.s("cycles")
        if prev == "focus":
            if not s.s("breaks"):
                self.mode = "focus"
                if n and self.cycle >= n:
                    self.cycle = 0
            else:
                self.mode = "long" if (n and self.cycle >= n) else "short"
        else:
            if prev == "long":
                self.cycle = 0
            self.mode = "focus"
        self._setup()
        self._flow_override = False
        if prev == "focus" and self.mode != "focus" and self._flow_el > 0:
            self._flow_override = True
            ratio = max(2, int(s.s("flow_ratio")))
            self.total = float(max(1, int(round(self._flow_el / 60.0 / ratio)))) * 60.0
        self.state.emit()
        self.tick.emit()


# ───────────────────────────── base widgets ─────────────────────────────
class Hoverable(QWidget):
    hover = fprop("hover")
    press = fprop("press")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def enterEvent(self, e):
        A(self, "hover", 1, 180)
        super().enterEvent(e)

    def leaveEvent(self, e):
        A(self, "hover", 0, 260)
        super().leaveEvent(e)


class RoundButton(Hoverable):
    clicked = Signal()
    morph = fprop("morph")

    def __init__(self, icon, size=48, kind="ghost", parent=None):
        super().__init__(parent)
        self.icon, self.kind, self._down = icon, kind, False
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_morph(self, v):
        A(self, "morph", v, 320, BACK if v else OUT)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._down = True
            A(self, "press", 1, 90)

    def mouseReleaseEvent(self, e):
        if self._down:
            self._down = False
            A(self, "press", 0, 380, BACK)
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        w = self.width()
        if not self.isEnabled():
            p.setOpacity(.32)
        s = 1 - 0.07 * self.press + 0.025 * self.hover
        p.translate(w / 2, w / 2)
        p.scale(s, s)
        r = w / 2 - 2
        if self.kind == "primary":
            p.setPen(NOPEN)
            p.setBrush(T.primary)
            p.drawEllipse(QPointF(0, 0), r, r)
            hg = QLinearGradient(0, -r, 0, r)
            hg.setColorAt(0, QColor(255, 255, 255, 38 if not T.dark else 0))
            hg.setColorAt(0.5, QColor(255, 255, 255, 0))
            p.setBrush(hg)
            p.drawEllipse(QPointF(0, 0), r, r)
            col = T.on_primary
        else:
            p.setPen(NOPEN)
            p.setBrush(mix(T.body, T.track, 0.45 * self.hover + 0.4 * self.press))
            p.drawEllipse(QPointF(0, 0), r, r)
            col = T.text
        draw_icon(p, self.icon, 0, 0, w * 0.4, col, self.morph)


class Label(QWidget):
    def __init__(self, s="", size=14, weight=W_MED, role="text", align="l", spacing=0.0, parent=None):
        super().__init__(parent)
        self._s, self.size, self.weight, self.role, self.align, self.spacing = s, size, weight, role, align, spacing
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(int(size * 1.7))

    def setText(self, s):
        self._s = s
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        s = tr(self._s)
        if self.spacing >= 1.2:
            s = s.upper()
        text(p, QRectF(self.rect()), s, F(self.size, self.weight, self.spacing), getattr(T, self.role), self.align)


class Sheet(QWidget):
    def __init__(self, parent=None, top=30):
        super().__init__(parent)
        self.top = top

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        path = rr_path(QRectF(self.rect()), self.top, self.top, RADIUS, RADIUS)
        p.fillPath(path, T.card)
        p.setPen(QPen(T.hair, 1))
        p.drawPath(path)


class SmoothScroll(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self.setBackgroundRole(QPalette.ColorRole.NoRole)
        self.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:8px;margin:6px 2px 96px 2px;}"
            "QScrollBar::handle:vertical{background:rgba(128,128,128,90);border-radius:2px;min-height:40px;}"
            "QScrollBar::handle:vertical:hover{background:rgba(128,128,128,150);}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}")
        self._target = 0.0
        self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._anim.setEasingCurve(OUT)

    def setWidget(self, w):
        super().setWidget(w)
        w.setAutoFillBackground(False)
        self.viewport().setAutoFillBackground(False)

    def wheelEvent(self, e):
        bar = self.verticalScrollBar()
        if self._anim.state() != QAbstractAnimation.State.Running:
            self._target = float(bar.value())
        self._target = clamp(self._target - e.angleDelta().y() * 0.9, bar.minimum(), bar.maximum())
        self._anim.stop()
        self._anim.setDuration(dur(380))
        self._anim.setStartValue(bar.value())
        self._anim.setEndValue(int(self._target))
        self._anim.start()
        e.accept()


# ───────────────────────────── window chrome ─────────────────────────────
class TitleBar(QWidget):
    def __init__(self, win, parent):
        super().__init__(parent)
        self.win, self._hot, self._down = win, None, None
        self.setFixedHeight(36)
        self.setMouseTracking(True)

    def _rects(self):
        w = self.width()
        return {"close": QRectF(w - 46, 0, 46, 36), "min": QRectF(w - 92, 0, 46, 36)}

    def _hit(self, pos):
        return next((k for k, r in self._rects().items() if r.contains(pos)), None)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        w = self.width()
        p.fillPath(rr_path(QRectF(self.rect()), RADIUS, RADIUS, 0, 0), T.titlebar)
        draw_logo(p, QRectF(13, 10, 16, 16))
        text(p, QRectF(38, 0, w - 140, 36), self.win.windowTitle(), F(12, W_NORMAL), T.text2)
        rs = self._rects()
        if self._hot == "close":
            p.fillPath(rr_path(rs["close"], 0, RADIUS, 0, 0), QColor("#E81123"))
        elif self._hot == "min":
            p.fillRect(rs["min"], T.hair)
        c = rs["min"].center()
        draw_icon(p, "minus", c.x(), c.y(), 14, T.text2, w=1.5)
        c = rs["close"].center()
        draw_icon(p, "close", c.x(), c.y(), 14, QColor("#FFFFFF") if self._hot == "close" else T.text2, w=1.5)

    def mouseMoveEvent(self, e):
        h = self._hit(e.position())
        if h != self._hot:
            self._hot = h
            self.update()

    def leaveEvent(self, e):
        self._hot = None
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self._down = self._hit(e.position())
        if not self._down and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()

    def mouseReleaseEvent(self, e):
        k = self._hit(e.position())
        if k and k == self._down:
            self.win.minimize() if k == "min" else self.win.close()
        self._down = None


class Header(QWidget):
    pct = fprop("pct")
    shimmer = fprop("shimmer")
    txt_a = fprop("txt_a", 1.0)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self._title, self._sub, self._show, self._pending = "Сегодня", "", True, None
        a = QPropertyAnimation(self, b"shimmer", self)
        a.setDuration(2800)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setLoopCount(-1)
        a.start()
        self._shim = a

    def set_state(self, title, sub, pct, show_pct=True, instant=False, ms=900):
        self._show = show_pct
        if (title, sub) != (self._title, self._sub):
            if instant:
                self._title, self._sub = title, sub
            else:
                self._pending = (title, sub)
                A(self, "txt_a", 0, 110, finished=self._swap)
        A(self, "pct", pct, ms, OUT)

    def _swap(self):
        if self._pending:
            self._title, self._sub = self._pending
            self._pending = None
        A(self, "txt_a", 1, 240)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), T.header)
        a = self.txt_a
        p.setOpacity(a)
        title = f"{self._title} ({int(round(self.pct))}%)" if self._show else self._title
        text(p, QRectF(22, 12 + (1 - a) * 5, w - 44, 30), title, F(20, W_MED), QColor("#FFFFFF"))
        text(p, QRectF(22, 42 + (1 - a) * 5, w - 44, 18), self._sub.upper(), F(11, W_MED, 1.2), QColor("#8E8E93"))
        p.setOpacity(1)
        y = h - 3
        p.fillRect(QRectF(0, y, w, 3), QColor(255, 255, 255, 36))
        fw = w * clamp(self.pct / 100.0)
        if fw > 0.5:
            p.fillRect(QRectF(0, y, fw, 3), T.header_line)
            bw = 140.0
            x0 = -bw + self.shimmer * (fw + bw)
            g = QLinearGradient(x0, 0, x0 + bw, 0)
            g.setColorAt(0, QColor(255, 255, 255, 0))
            g.setColorAt(0.5, QColor(255, 255, 255, 150))
            g.setColorAt(1, QColor(255, 255, 255, 0))
            p.setClipRect(QRectF(0, y, fw, 3))
            p.fillRect(QRectF(x0, y, bw, 3), g)


# ───────────────────────────── timer ring ─────────────────────────────
class TimerRing(QWidget):
    clicked = Signal()
    prog = fprop("prog")
    brk = fprop("brk")
    run = fprop("run")
    breath = fprop("breath")
    roll = fprop("roll", 1.0)
    pulse = fprop("pulse", 1.0)
    intro = fprop("intro", 1.0)
    press = fprop("press")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 276)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._txt = self._old = "25:00"
        self._mode, self._running, self._started, self._total = "focus", False, False, 1500.0
        self._cycle, self._cycles = 0, 4
        self._free = False
        self._br = QPropertyAnimation(self, b"breath", self)
        self._br.setDuration(4200)
        self._br.setStartValue(0.0)
        self._br.setEndValue(1.0)
        self._br.setLoopCount(-1)

    def play_intro(self):
        A(self, "intro", 1, 900, OUT, start=0)

    def celebrate(self):
        A(self, "pulse", 1, 1100, OUT, start=0)

    def set_view(self, shown, prog, mode, running, started, cycle, cycles, free=False, total=0.0):
        txt = fmt_clock(shown, up=free)
        if txt != self._txt:
            self._old, self._txt = self._txt, txt
            if len(self._old) == len(txt):
                A(self, "roll", 1, 360, OUT, start=0)
        prog = clamp(prog)
        jump = (mode != self._mode or total != self._total or (self._started and not started) or free != self._free
                or (free and self.prog - prog > 0.5))
        if jump:
            A(self, "prog", prog, 700, INOUT)
        elif not running_anim(self, "prog"):
            self.prog = prog
        if mode != self._mode:
            A(self, "brk", 0.0 if mode == "focus" else 1.0, 700)
        if running != self._running:
            A(self, "run", 1.0 if running else 0.0, 600)
        if started and self._br.state() != QAbstractAnimation.State.Running:
            self._br.start()
        elif not started:
            self._br.stop()
        self._mode, self._running, self._started, self._total, self._free = mode, running, started, total, free
        self._cycle, self._cycles = cycle, cycles
        self.update()

    def mousePressEvent(self, e):
        c = QPointF(self.width() / 2, self.height() / 2)
        if math.dist((e.position().x(), e.position().y()), (c.x(), c.y())) < 125:
            self._dn = True
            A(self, "press", 1, 100)

    def mouseReleaseEvent(self, e):
        if getattr(self, "_dn", False):
            self._dn = False
            A(self, "press", 0, 400, BACK)
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        c = QPointF(self.width() / 2, self.height() / 2)
        R = 116.0
        it = ease_out(self.intro)
        sc = (0.96 + 0.04 * it) * (1 - 0.012 * self.press)
        p.translate(c)
        p.scale(sc, sc)
        p.translate(-c)
        p.setOpacity(it)
        run, brk, prog = self.run, self.brk, self.prog
        col = mix(T.accent, BREAK, brk)
        br = 0.5 + 0.5 * math.sin(self.breath * 2 * math.pi)
        # halo
        ext = 30.0
        g = QRadialGradient(c, R + ext)
        g.setColorAt((R - 6) / (R + ext), alpha(col, 0))
        g.setColorAt((R + 4) / (R + ext), alpha(col, 0.17 * run * (0.65 + 0.35 * br)))
        g.setColorAt(1.0, alpha(col, 0))
        p.setPen(NOPEN)
        p.setBrush(g)
        p.drawEllipse(c, R + ext, R + ext)
        # disc + shadow
        sg = QRadialGradient(QPointF(c.x(), c.y() + 10), R - 4)
        sg.setColorAt(0.8, QColor(0, 0, 0, 90 if T.dark else 26))
        sg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(sg)
        p.drawEllipse(QPointF(c.x(), c.y() + 10), R - 4, R - 4)
        p.setBrush(T.card)
        p.drawEllipse(c, R - 10, R - 10)
        p.setPen(QPen(T.hair, 1))
        p.setBrush(NOBRUSH)
        p.drawEllipse(c, R - 10, R - 10)
        # ticks
        for i in (range(60) if _TICKS else ()):
            a = math.radians(i * 6 - 90)
            r1, r2 = (R - 37, R - 26) if i % 5 == 0 else (R - 33, R - 26)
            lit = (i + 0.5) / 60 <= prog
            pen = QPen(alpha(col, 0.95) if lit else T.track, 1.6)
            pen.setCapStyle(CAP_R)
            p.setPen(pen)
            p.drawLine(QPointF(c.x() + r1 * math.cos(a), c.y() + r1 * math.sin(a)),
                       QPointF(c.x() + r2 * math.cos(a), c.y() + r2 * math.sin(a)))
        # track + arc
        rect = QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R)
        p.setPen(QPen(T.track, 6))
        p.drawEllipse(c, R, R)
        span = int(-prog * 360 * 16)
        if abs(span) > 8:
            cg = QConicalGradient(c, 90)
            cg.setColorAt(0.0, col)
            cg.setColorAt(max(0.0001, 1 - prog), col)
            cg.setColorAt(1.0, alpha(col, 0.35))
            p.setPen(QPen(cg, 6, Qt.PenStyle.SolidLine, CAP_R))
            p.drawArc(rect, 90 * 16, span)
        a = math.radians(90 - prog * 360)
        hp = QPointF(c.x() + R * math.cos(a), c.y() - R * math.sin(a))
        if run > 0.01:
            hg = QRadialGradient(hp, 20)
            hg.setColorAt(0, alpha(col, 0.35 * run))
            hg.setColorAt(1, alpha(col, 0))
            p.setPen(NOPEN)
            p.setBrush(hg)
            p.drawEllipse(hp, 20, 20)
        p.setBrush(T.card)
        p.setPen(QPen(col, 2.6))
        p.drawEllipse(hp, 7, 7)
        # texts
        cap = tr("mode.free") if (self._free and self._mode == "focus") else tr("mode." + self._mode)
        if self._started and not self._running:
            cap = tr("mode.paused")
        text(p, QRectF(c.x() - 90, c.y() - 66, 180, 18), cap, F(11, W_MED, 2.4),
             col if self._running else T.text3, "c")
        size = 58 if len(self._txt) <= 5 else 58 * 5 / len(self._txt)
        f = F(size, W_LIGHT)
        fm = QFontMetricsF(f)
        cw, kw = fm.horizontalAdvance("0"), fm.horizontalAdvance(":") * 0.8
        widths = [kw if ch == ":" else cw for ch in self._txt]
        x = c.x() - sum(widths) / 2
        base = 1.0 if (self._running or not self._started) else 0.55 + 0.45 * br
        roll = self.roll
        for i, ch in enumerate(self._txt):
            cell = QRectF(x, c.y() - 42, widths[i], 84)
            if ch == ":":
                p.setOpacity(it * base * (0.45 + 0.55 * (1 - ease_out(roll)) if self._running else 1.0))
                p.setPen(NOPEN)
                p.setBrush(T.text)
                for dy in (-0.15, 0.15):
                    p.drawEllipse(QPointF(cell.center().x(), c.y() + dy * size), size * 0.045, size * 0.045)
            elif roll < 1 and len(self._old) == len(self._txt) and self._old[i] != ch:
                r_ = ease_out(roll)
                p.setOpacity(it * base * (1 - r_))
                text(p, cell.translated(0, -r_ * 16), self._old[i], f, T.text, "c")
                p.setOpacity(it * base * r_)
                text(p, cell.translated(0, (1 - r_) * 16), ch, f, T.text, "c")
            else:
                p.setOpacity(it * base)
                text(p, cell, ch, f, T.text, "c")
            x += widths[i]
        p.setOpacity(it)
        # cycle dots
        n = min(self._cycles, 8)
        filled = n if self._mode == "long" else min(self._cycle, n)
        x0 = c.x() - (n - 1) * 7
        for i in range(n):
            pt = QPointF(x0 + i * 14, c.y() + 56)
            p.setPen(NOPEN)
            if i < filled:
                p.setBrush(col)
                p.drawEllipse(pt, 3.5, 3.5)
            elif i == filled and self._mode == "focus":
                p.setBrush(NOBRUSH)
                p.setPen(QPen(col, 1.6))
                rr = 3.5 + (1.2 * br if self._running else 0)
                p.drawEllipse(pt, rr, rr)
            else:
                p.setBrush(T.track)
                p.drawEllipse(pt, 3.5, 3.5)
        if self.pulse < 1:
            q = ease_out(self.pulse)
            p.setBrush(NOBRUSH)
            p.setPen(QPen(alpha(col, 0.5 * (1 - q)), 2))
            p.drawEllipse(c, R + 6 + 40 * q, R + 6 + 40 * q)


def running_anim(obj, name):
    return running(obj, name)


# ───────────────────────────── chips ─────────────────────────────
class ChipBar(QWidget):
    selected = Signal(str)
    sel = fprop("sel")
    off = fprop("off")
    hl = fprop("hl", 1.0)

    def __init__(self, parent=None, bg="card", center=False, pad=20):
        super().__init__(parent)
        self.items, self.cur, self.bg, self.center, self.pad = [], -1, bg, center, pad
        self._rects, self._total, self._press, self._moved = [], 0.0, None, False
        self.setFixedHeight(36)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_items(self, items, current=None):
        self.items = items
        fm = QFontMetricsF(F(13))
        x, self._rects = 0.0, []
        for it in items:
            w = fm.horizontalAdvance(tr(it[1])) + 30 + (16 if len(it) > 2 and it[2] else 0)
            self._rects.append(QRectF(x, 0, w, 36))
            x += w + 8
        self._total = max(0.0, x - 8)
        self.cur = next((i for i, it in enumerate(items) if it[0] == current), -1)
        self.sel = float(max(self.cur, 0))
        self.hl = 1.0 if self.cur >= 0 else 0.0
        self.off = 0.0
        self.update()

    def relayout(self):
        self.set_items(self.items, self.current_id())

    def current_id(self):
        return self.items[self.cur][0] if 0 <= self.cur < len(self.items) else None

    def _max_off(self):
        return max(0.0, self._total + 2 * self.pad - self.width())

    def _origin(self):
        if self._total + 2 * self.pad <= self.width():
            return (self.width() - self._total) / 2 if self.center else self.pad
        return self.pad - self.off

    def select(self, cid, animate=True, emit=False):
        idx = next((i for i, it in enumerate(self.items) if it[0] == cid), -1)
        self.cur = idx
        if idx < 0:
            A(self, "hl", 0, 200)
            return
        if animate:
            A(self, "sel", idx, 420, QEasingCurve.Type.OutQuint)
        else:
            self.sel = float(idx)
        A(self, "hl", 1, 200)
        m, r = self._max_off(), self._rects[idx]
        if m > 0:
            vis = self.width() - 2 * self.pad
            if r.left() - self.off < 0:
                A(self, "off", clamp(r.left(), 0, m), 380)
            elif r.right() - self.off > vis:
                A(self, "off", clamp(r.right() - vis, 0, m), 380)
        if emit:
            self.selected.emit(cid)

    def wheelEvent(self, e):
        m = self._max_off()
        if m > 0:
            d = e.angleDelta().y() or e.angleDelta().x()
            A(self, "off", clamp(self.off - d * 0.6, 0, m), 220)
            e.accept()

    def mousePressEvent(self, e):
        self._press, self._off0, self._moved = e.position(), self.off, False

    def mouseMoveEvent(self, e):
        if self._press is not None:
            dx = e.position().x() - self._press.x()
            if abs(dx) > 5:
                self._moved = True
            if self._moved and self._max_off() > 0:
                self.off = clamp(self._off0 - dx, 0, self._max_off())

    def mouseReleaseEvent(self, e):
        if self._press is not None and not self._moved:
            x = e.position().x() - self._origin()
            for i, r in enumerate(self._rects):
                if r.left() <= x <= r.right():
                    self.select(self.items[i][0], emit=True)
                    break
        self._press = None

    def paintEvent(self, e):
        n = len(self.items)
        if not n:
            return
        p = QPainter(self)
        p.setRenderHints(RH)
        ox = self._origin()
        base = T.card if self.bg == "card" else T.body
        for r in self._rects:
            rr = r.translated(ox, 0)
            p.setPen(QPen(T.hair, 1))
            p.setBrush(base)
            p.drawRoundedRect(rr.adjusted(.5, .5, -.5, -.5), 18, 18)
        sel = clamp(self.sel, 0, n - 1)
        i0 = int(sel)
        i1 = min(i0 + 1, n - 1)
        f = sel - i0
        a, b = self._rects[i0], self._rects[i1]
        p.setOpacity(self.hl)
        p.setPen(NOPEN)
        p.setBrush(T.primary)
        p.drawRoundedRect(QRectF(lerp(a.x(), b.x(), f) + ox, 0, lerp(a.width(), b.width(), f), 36), 18, 18)
        p.setOpacity(1)
        for i, (r, it) in enumerate(zip(self._rects, self.items)):
            wgt = clamp(1 - abs(sel - i)) * self.hl
            col = mix(T.text2, T.on_primary, wgt)
            rr = r.translated(ox, 0)
            tx = rr.left() + 15
            if len(it) > 2 and it[2]:
                p.setPen(NOPEN)
                p.setBrush(QColor(it[2]))
                p.drawEllipse(QPointF(rr.left() + 16, 18), 4, 4)
                tx += 16
            text(p, QRectF(tx, 0, rr.right() - 12 - tx, 36), tr(it[1]), F(13, W_MED), col, "l", False)


# ───────────────────────────── toast / tabs / pages ─────────────────────────────
def style_edit(edit, px=15, weight=W_NORMAL, center=False):
    edit.setFrame(False)
    edit.setFont(F(px, weight))
    edit.setStyleSheet("QLineEdit{background:transparent;border:none;color:%s;"
                       "selection-background-color:%s;selection-color:%s;}" %
                       (T.text.name(), alpha(T.accent, .35).name(QColor.NameFormat.HexArgb), T.text.name()))
    pal = edit.palette()
    pal.setColor(QPalette.ColorRole.PlaceholderText, T.text3)
    edit.setPalette(pal)
    if center:
        edit.setAlignment(Qt.AlignmentFlag.AlignCenter)


class Toast(QWidget):
    a = fprop("a")

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._s, self._q, self._busy = "", [], False
        self.hide()

    def queue(self, s):
        self._q.append(s)
        if not self._busy:
            self._next()

    def _next(self):
        if not self._q:
            self._busy = False
            return
        self._busy, self._s = True, self._q.pop(0)
        w = int(QFontMetricsF(F(13)).horizontalAdvance(self._s)) + 56
        self.setFixedSize(w, 44)
        self.move((self.parent().width() - w) // 2, 124)
        self.show()
        self.raise_()
        A(self, "a", 1, 350, OUT, start=0)
        QTimer.singleShot(dur(2300) if _ANIM else 2300, self._out)

    def _out(self):
        A(self, "a", 0, 300, OUT, finished=self._done)

    def _done(self):
        self.hide()
        QTimer.singleShot(60, self._next)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        a = self.a
        p.setOpacity(a)
        p.translate(0, (1 - a) * -12)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(alpha(T.capsule, 0.96))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 22, 22)
        p.setPen(NOPEN)
        p.setBrush(T.accent if not T.dark else QColor("#F5F5F7"))
        p.drawEllipse(QPointF(20, 22), 3.5, 3.5)
        text(p, QRectF(34, 0, self.width() - 46, 44), self._s, F(13), QColor("#F5F5F7"), "l", False)


class TabBar(QWidget):
    changed = Signal(int)
    sel = fprop("sel")
    pop = fprop("pop", 1.0)
    vis = fprop("vis")
    ITEMS = [("timer", "tab.focus"), ("tasks", "tab.tasks"), ("chart", "tab.stats"), ("user", "tab.profile"),
             ("sliders", "tab.settings")]

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(390, 92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.index = 0

    def set_index(self, i, animate=True):
        self.index = i
        if animate:
            A(self, "sel", i, 520, QEasingCurve.Type.OutQuint)
            A(self, "pop", 1, 500, OUT, start=0)
        else:
            self.sel = float(i)

    def mousePressEvent(self, e):
        x = e.position().x() - 15
        if 0 <= x < 360 and 14 <= e.position().y() <= 74:
            i = int(x // 72)
            if i != self.index:
                self.changed.emit(i)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        v = ease_out(self.vis)
        p.setOpacity(v)
        p.translate(0, (1 - v) * 40)
        cap = QRectF(15, 14, 360, 60)
        p.setPen(NOPEN)
        for i in range(14):
            p.setBrush(QColor(0, 0, 0, int(255 * 0.022 * (1 - i / 14) ** 1.5)))
            p.drawRoundedRect(cap.adjusted(-i, -i + 7, i, i + 7), 30 + i, 30 + i)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.setBrush(T.capsule)
        p.drawRoundedRect(cap.adjusted(.5, .5, -.5, -.5), 30, 30)
        cw = 72.0
        p.setPen(NOPEN)
        p.setBrush(QColor(255, 255, 255, 34))
        p.drawRoundedRect(QRectF(cap.x() + 4 + self.sel * cw, cap.y() + 4, cw - 8, 52), 26, 26)
        for i, (ic, label) in enumerate(self.ITEMS):
            wgt = clamp(1 - abs(self.sel - i))
            col = mix(QColor(255, 255, 255, 120), QColor(255, 255, 255, 255), wgt)
            cx = cap.x() + i * cw + cw / 2
            sc = lerp(0.8, 1.0, ease_back(self.pop)) if i == self.index else 1.0
            draw_icon(p, ic, cx, cap.y() + 21, 22 * sc, col)
            text(p, QRectF(cx - 36, cap.y() + 34, 72, 16), tr(label), F(10, W_MED), col, "c")


class PageHost(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.pages, self.cur, self._grp, self.overlay = [], -1, None, None

    def add(self, page):
        page.setParent(self)
        self.pages.append(page)
        page.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillPath(rr_path(QRectF(self.rect()), 0, 0, RADIUS, RADIUS), T.body)

    def resizeEvent(self, e):
        for pg in self.pages:
            pg.setGeometry(self.rect())

    def _finish(self):
        if self._grp:
            g, self._grp = self._grp, None
            g.stop()
            g.deleteLater()
        for k, pg in enumerate(self.pages):
            pg.setGraphicsEffect(None)
            pg.setGeometry(self.rect())
            pg.setVisible(k == self.cur)
        if self.overlay:
            self.overlay.raise_()

    def show_page(self, i, animate=True):
        if i == self.cur:
            return
        self._finish()
        old = self.pages[self.cur] if self.cur >= 0 else None
        new, d = self.pages[i], (1 if self.cur < 0 or i > self.cur else -1)
        self.cur = i
        new.setGeometry(self.rect())
        new.show()
        new.raise_()
        if hasattr(new, "on_show"):
            new.on_show()
        if self.overlay:
            self.overlay.raise_()
        if not animate or not _ANIM or old is None:
            if old:
                old.hide()
            return
        g = QParallelAnimationGroup(self)

        def mk(target, prop, a, b, ms, curve):
            an = QPropertyAnimation(target, prop, g)
            an.setDuration(ms)
            an.setStartValue(a)
            an.setEndValue(b)
            an.setEasingCurve(curve)
        en, eo = QGraphicsOpacityEffect(new), QGraphicsOpacityEffect(old)
        new.setGraphicsEffect(en)
        old.setGraphicsEffect(eo)
        mk(en, b"opacity", 0.0, 1.0, 420, OUT)
        mk(new, b"pos", QPoint(d * 38, 0), QPoint(0, 0), 480, QEasingCurve.Type.OutQuint)
        mk(eo, b"opacity", 1.0, 0.0, 220, OUT)
        mk(old, b"pos", QPoint(0, 0), QPoint(-d * 26, 0), 300, IN)
        g.finished.connect(self._finish)
        self._grp = g
        g.start()


class Outline(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.setPen(QPen(T.border, 1))
        p.setBrush(NOBRUSH)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), RADIUS, RADIUS)


class Splash(QWidget):
    t = fprop("t")
    out = fprop("out")

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        o = 1 - ease_out(self.out)
        p.setOpacity(o)
        p.fillPath(rr_path(QRectF(self.rect()), 0, 0, RADIUS, RADIUS), T.body)
        w, h = self.width(), self.height()
        t = self.t
        s = lerp(0.78, 1.0, ease_back(t)) * (1 + 0.1 * self.out)
        sz = 112 * s
        p.setOpacity(o * ease_out(t * 1.4))
        draw_logo(p, QRectF(w / 2 - sz / 2, h * 0.36 - sz / 2, sz, sz))
        text(p, QRectF(0, h * 0.36 + 82, w, 40), APP_NAME, F(32, W_LIGHT), T.text, "c")
        text(p, QRectF(0, h * 0.36 + 118, w, 20), tr("version", v=APP_VERSION), F(13, W_NORMAL), T.text2, "c")


# ───────────────────────────── tasks ─────────────────────────────
ROW_H = 64


class TaskRow(QWidget):
    toggled = Signal(str)
    played = Signal(str)
    deleted = Signal(str)
    hover = fprop("hover")
    done_t = fprop("done_t")
    sel_t = fprop("sel_t")

    def _geth(self):
        return getattr(self, "_p_h", 0.0)

    def _seth(self, v):
        self._p_h = v
        self.setFixedHeight(max(0, int(round(v))))
        self.update()
    h = Property(float, _geth, _seth)

    def __init__(self, task, store, current):
        super().__init__()
        self.store, self.task, self._hot, self._dying = store, task, None, False
        self._p_done_t = 1.0 if task["done"] else 0.0
        self._p_sel_t = 1.0 if current else 0.0
        self.setMouseTracking(True)
        self.setFixedHeight(0)

    def update_task(self, task, current):
        self.task = task
        A(self, "done_t", 1.0 if task["done"] else 0.0, 520, OUT)
        A(self, "sel_t", 1.0 if current else 0.0, 350, OUT)
        self.update()

    def expand(self):
        A(self, "h", ROW_H, 420, OUT, start=0)

    def collapse(self):
        self._dying = True
        A(self, "h", 0, 280, IN, finished=self.deleteLater)

    def _rects(self):
        w = self.width()
        play = QRectF(w - 24 - 36, (ROW_H - 36) / 2, 36, 36)
        dele = QRectF(play.left() - 6 - 30, (ROW_H - 30) / 2, 30, 30)
        return QRectF(10, 10, 56, 44), play, dele

    def enterEvent(self, e):
        A(self, "hover", 1, 160)

    def leaveEvent(self, e):
        self._hot = None
        A(self, "hover", 0, 240)

    def mouseMoveEvent(self, e):
        chk, play, dele = self._rects()
        pos = e.position()
        self._hot = "check" if chk.contains(pos) else "play" if play.contains(pos) and not self.task["done"] \
            else "del" if dele.contains(pos) else None
        self.setCursor(Qt.CursorShape.PointingHandCursor if self._hot else Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, e):
        if self._dying or e.button() != Qt.MouseButton.LeftButton:
            return
        tid = self.task["id"]
        if self._hot == "check":
            self.toggled.emit(tid)
        elif self._hot == "play":
            self.played.emit(tid)
        elif self._hot == "del":
            self.deleted.emit(tid)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        w, t = self.width(), self.task
        p.setOpacity(clamp(self.h / ROW_H))
        hv, dt, sl = self.hover, self.done_t, self.sel_t
        p.setPen(NOPEN)
        if hv > .01:
            p.setBrush(alpha(T.body, .9 * hv))
            p.drawRoundedRect(QRectF(10, 2, w - 20, ROW_H - 4), 16, 16)
        if sl > .01:
            p.setBrush(alpha(T.accent, .07 * sl))
            p.drawRoundedRect(QRectF(10, 2, w - 20, ROW_H - 4), 16, 16)
        chk, play, dele = self._rects()
        c = QPointF(35, ROW_H / 2)
        p.setBrush(NOBRUSH)
        p.setPen(QPen(mix(T.text3, T.text2, hv + (0.5 if self._hot == "check" else 0)), 1.8))
        p.drawEllipse(c, 12, 12)
        if dt > 0.01:
            p.setPen(NOPEN)
            p.setBrush(T.primary)
            rr = 13 * ease_back(dt)
            p.drawEllipse(c, rr, rr)
            pen = QPen(T.on_primary, 2.2)
            pen.setCapStyle(CAP_R)
            pen.setJoinStyle(JOIN_R)
            p.setPen(pen)
            p.setBrush(NOBRUSH)
            p.drawPolyline(partial_poly([(c.x() - 5, c.y() + .5), (c.x() - 1.5, c.y() + 4.5),
                                         (c.x() + 5, c.y() - 4)], (dt - .3) / .7))
        tx, tw = 62, dele.left() - 12 - 62
        f = F(15, W_MED)
        col = mix(T.text, T.text3, dt)
        adv = text(p, QRectF(tx, 12, tw, 24), t["title"], f, col)
        if dt > .01:
            p.setPen(QPen(alpha(T.text3, .9), 1.5))
            p.drawLine(QPointF(tx, 24), QPointF(tx + adv * ease_out(dt), 24))
        cat = self.store.cat(t["cat"])
        p.setPen(NOPEN)
        p.setBrush(QColor(cat["color"]))
        p.drawEllipse(QPointF(tx + 4, 46), 3.5, 3.5)
        sub = cat_name(cat) + (f"  ·  {fmt_minutes(t['focus'])}" if t.get("focus", 0) >= 1 else "")
        text(p, QRectF(tx + 14, 36, tw - 14, 20), sub, F(12, W_NORMAL), mix(T.text2, T.text3, dt))
        if hv > .01:
            draw_icon(p, "close", dele.center().x(), dele.center().y(), 12,
                      alpha(DANGER if self._hot == "del" else T.text3, hv), w=1.6)
        if not t["done"]:
            p.setPen(QPen(mix(T.track, T.accent, sl), 1.5))
            p.setBrush(mix(QColor(0, 0, 0, 0), T.primary, sl) if sl > .01 else (
                alpha(T.body, 1.0) if self._hot == "play" else NOBRUSH))
            p.drawEllipse(play.center(), 16, 16)
            draw_icon(p, "play", play.center().x() + 1, play.center().y(), 15,
                      mix(T.text2, T.on_primary, sl), w=1.4)


class TaskList(QWidget):
    empty_t = fprop("empty_t")

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store, self.rows, self.filter = store, {}, "all"
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 4, 0, 110)
        self.lay.setSpacing(0)
        self.lay.addStretch(1)
        self.setMinimumHeight(330)
        self.callbacks = None

    def sync(self):
        tasks = self.store.visible_tasks(self.filter)
        ids = [t["id"] for t in tasks]
        cur = self.store.d.get("current_task")
        for tid in list(self.rows):
            if tid not in ids:
                self.rows.pop(tid).collapse()
        for i, t in enumerate(tasks):
            row = self.rows.get(t["id"])
            if row is None:
                row = TaskRow(t, self.store, t["id"] == cur)
                row.toggled.connect(self.callbacks[0])
                row.played.connect(self.callbacks[1])
                row.deleted.connect(self.callbacks[2])
                self.rows[t["id"]] = row
                self.lay.insertWidget(i, row)
                row.expand()
            else:
                row.update_task(t, t["id"] == cur)
                if self.lay.indexOf(row) != i:
                    self.lay.removeWidget(row)
                    self.lay.insertWidget(i, row)
        A(self, "empty_t", 1.0 if not tasks else 0.0, 450)

    def paintEvent(self, e):
        if self.empty_t < .01:
            return
        p = QPainter(self)
        p.setRenderHints(RH)
        a = ease_out(self.empty_t)
        p.setOpacity(a)
        cx, cy = self.width() / 2, 90 + (1 - a) * 10
        p.setPen(QPen(T.track, 2))
        p.setBrush(NOBRUSH)
        p.drawEllipse(QPointF(cx, cy), 30, 30)
        draw_icon(p, "check", cx, cy, 30, T.text3, w=2.2)
        text(p, QRectF(0, cy + 48, self.width(), 24), tr("tk.empty"), F(17, W_MED), T.text2, "c")
        text(p, QRectF(0, cy + 74, self.width(), 20), tr("tk.empty2"),
             F(13, W_NORMAL), T.text3, "c")


class InputPill(QWidget):
    submitted = Signal(str)
    focus_t = fprop("focus_t")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.edit = QLineEdit(self)
        self.edit.installEventFilter(self)
        self.edit.returnPressed.connect(self._submit)
        self.btn = RoundButton("plus", 38, "primary", self)
        self.btn.clicked.connect(self._submit)
        self.restyle()

    def restyle(self):
        style_edit(self.edit, 15)

    def resizeEvent(self, e):
        self.btn.move(self.width() - 45, 7)
        self.edit.setGeometry(22, 0, self.width() - 80, self.height())

    def eventFilter(self, o, e):
        if o is self.edit and e.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            A(self, "focus_t", 1.0 if e.type() == QEvent.Type.FocusIn else 0.0, 260)
        return False

    def _submit(self):
        s = self.edit.text().strip()
        if s:
            self.edit.clear()
            self.submitted.emit(s)
        else:
            self.edit.setFocus()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        f = self.focus_t
        if f > .01:
            p.setPen(QPen(alpha(T.accent, .12 * f), 5))
            p.setBrush(NOBRUSH)
            p.drawRoundedRect(r.adjusted(-1, -1, 1, 1), 26, 26)
        p.setPen(QPen(mix(T.hair, alpha(T.accent, .7), f), 1.3))
        p.setBrush(T.card)
        p.drawRoundedRect(r, 25, 25)


def fmt_date():
    d = date.today()
    return tr("date.fmt", wd=tr("wd.%d" % d.weekday()), mo=tr("mo.%d" % (d.month - 1)), d=d.day)


class GoalRow(QWidget):
    toggled = Signal(str)
    deleted = Signal(str)
    hover = fprop("hover")
    done_t = fprop("done_t")

    def _geth(self):
        return getattr(self, "_p_h", 0.0)

    def _seth(self, v):
        self._p_h = v
        self.setFixedHeight(max(0, int(round(v))))
        self.update()
    h = Property(float, _geth, _seth)

    def __init__(self, goal, store):
        super().__init__()
        self.store, self.goal, self._hot, self._dying = store, goal, None, False
        self._p_done_t = 1.0 if goal["done"] else 0.0
        self.setMouseTracking(True)
        self.setFixedHeight(0)

    def update_goal(self, goal):
        self.goal = goal
        A(self, "done_t", 1.0 if goal["done"] else 0.0, 520, OUT)
        self.update()

    def expand(self):
        A(self, "h", ROW_H, 420, OUT, start=0)

    def collapse(self):
        self._dying = True
        A(self, "h", 0, 280, IN, finished=self.deleteLater)

    def _rects(self):
        w = self.width()
        return QRectF(10, 10, 56, 44), QRectF(w - 24 - 30, (ROW_H - 30) / 2, 30, 30)

    def enterEvent(self, e):
        A(self, "hover", 1, 160)

    def leaveEvent(self, e):
        self._hot = None
        A(self, "hover", 0, 240)

    def mouseMoveEvent(self, e):
        chk, dele = self._rects()
        pos = e.position()
        self._hot = "check" if chk.contains(pos) else "del" if dele.contains(pos) else None
        self.setCursor(Qt.CursorShape.PointingHandCursor if self._hot else Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, e):
        if self._dying or e.button() != Qt.MouseButton.LeftButton:
            return
        if self._hot == "check":
            self.toggled.emit(self.goal["id"])
        elif self._hot == "del":
            self.deleted.emit(self.goal["id"])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        w, g = self.width(), self.goal
        p.setOpacity(clamp(self.h / ROW_H))
        hv, dt = self.hover, self.done_t
        p.setPen(NOPEN)
        if hv > .01:
            p.setBrush(alpha(T.body, .9 * hv))
            p.drawRoundedRect(QRectF(10, 2, w - 20, ROW_H - 4), 16, 16)
        chk, dele = self._rects()
        c = QPointF(35, ROW_H / 2)
        cat = self.store.cat(g["cat"]) if g.get("cat") else None
        col = QColor(cat["color"]) if cat else T.accent
        frac = clamp(g.get("spent", 0) / g["target"]) if g["target"] > 0 else 0.0
        p.setBrush(NOBRUSH)
        if g["target"] > 0 and dt < 0.99:
            p.setPen(QPen(T.track, 2.6))
            p.drawEllipse(c, 12, 12)
            if frac > .005:
                p.setPen(QPen(col, 2.6, Qt.PenStyle.SolidLine, CAP_R))
                p.drawArc(QRectF(c.x() - 12, c.y() - 12, 24, 24), 90 * 16, int(-frac * 360 * 16))
            text(p, QRectF(c.x() - 12, c.y() - 12, 24, 24), "", F(9), T.text2, "c")
        else:
            p.setPen(QPen(mix(T.text3, T.text2, hv + (0.5 if self._hot == "check" else 0)), 1.8))
            p.drawEllipse(c, 12, 12)
        if dt > 0.01:
            p.setPen(NOPEN)
            p.setBrush(T.primary)
            rr = 13 * ease_back(dt)
            p.drawEllipse(c, rr, rr)
            pen = QPen(T.on_primary, 2.2)
            pen.setCapStyle(CAP_R)
            pen.setJoinStyle(JOIN_R)
            p.setPen(pen)
            p.setBrush(NOBRUSH)
            p.drawPolyline(partial_poly([(c.x() - 5, c.y() + .5), (c.x() - 1.5, c.y() + 4.5),
                                         (c.x() + 5, c.y() - 4)], (dt - .3) / .7))
        tx, tw = 62, dele.left() - 12 - 62
        adv = text(p, QRectF(tx, 12, tw, 24), g["title"], F(15, W_MED), mix(T.text, T.text3, dt))
        if dt > .01:
            p.setPen(QPen(alpha(T.text3, .9), 1.5))
            p.drawLine(QPointF(tx, 24), QPointF(tx + adv * ease_out(dt), 24))
        p.setPen(NOPEN)
        p.setBrush(col)
        p.drawEllipse(QPointF(tx + 4, 46), 3.5, 3.5)
        sub = cat_name(cat) if cat else tr("gl.any")
        if g["target"] > 0:
            sub += f"  ·  {fmt_minutes(min(g.get('spent', 0), g['target']))} / {fmt_minutes(g['target'])}"
        text(p, QRectF(tx + 14, 36, tw - 14, 20), sub, F(12, W_NORMAL), mix(T.text2, T.text3, dt))
        if hv > .01:
            draw_icon(p, "close", dele.center().x(), dele.center().y(), 12,
                      alpha(DANGER if self._hot == "del" else T.text3, hv), w=1.6)


class CarryRow(Hoverable):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.n = 0
        self.setFixedHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        r = QRectF(self.rect()).adjusted(18, 4, -18, -4)
        p.setPen(QPen(mix(T.text3, T.text2, self.hover), 1.4, Qt.PenStyle.DashLine))
        p.setBrush(alpha(T.body, .8 * self.hover))
        p.drawRoundedRect(r, 19, 19)
        s = tr("gl.carry", n=self.n)
        wd = QFontMetricsF(F(13, W_MED)).horizontalAdvance(s)
        x = r.center().x() - (wd + 24) / 2
        draw_icon(p, "reset", x + 8, r.center().y(), 15, T.text2, w=1.7)
        text(p, QRectF(x + 24, r.top(), wd + 4, r.height()), s, F(13, W_MED), T.text2, "l", False)


class GoalList(QWidget):
    empty_t = fprop("empty_t")

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store, self.rows = store, {}
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 4, 0, 110)
        self.lay.setSpacing(0)
        self.carry = CarryRow()
        self.carry.clicked.connect(self.store.carry_over)
        self.carry.hide()
        self.lay.addWidget(self.carry)
        self.lay.addStretch(1)
        self.setMinimumHeight(330)
        self.callbacks = None

    def sync(self):
        goals = self.store.today_goals()
        ids = [g["id"] for g in goals]
        for gid in list(self.rows):
            if gid not in ids:
                self.rows.pop(gid).collapse()
        stale = len(self.store.stale_goals())
        self.carry.n = stale
        self.carry.setVisible(stale > 0)
        self.carry.update()
        for i, g in enumerate(goals):
            row = self.rows.get(g["id"])
            if row is None:
                row = GoalRow(g, self.store)
                row.toggled.connect(self.callbacks[0])
                row.deleted.connect(self.callbacks[1])
                self.rows[g["id"]] = row
                self.lay.insertWidget(i + 1, row)
                row.expand()
            else:
                row.update_goal(g)
                if self.lay.indexOf(row) != i + 1:
                    self.lay.removeWidget(row)
                    self.lay.insertWidget(i + 1, row)
        A(self, "empty_t", 1.0 if not goals else 0.0, 450)

    def paintEvent(self, e):
        if self.empty_t < .01:
            return
        p = QPainter(self)
        p.setRenderHints(RH)
        a = ease_out(self.empty_t)
        p.setOpacity(a)
        cx, cy = self.width() / 2, (150 if self.carry.isVisible() else 100) + (1 - a) * 10
        p.setPen(QPen(T.track, 2))
        p.setBrush(NOBRUSH)
        p.drawEllipse(QPointF(cx, cy), 30, 30)
        draw_icon(p, "target", cx, cy, 30, T.text3, w=2.0)
        text(p, QRectF(0, cy + 48, self.width(), 24), tr("gl.empty"), F(17, W_MED), T.text2, "c")
        wrap_text(p, QRectF(40, cy + 78, self.width() - 80, 44), tr("gl.empty2"), F(13, W_NORMAL), T.text3,
                  Qt.AlignmentFlag.AlignHCenter)


class GoalsView(QWidget):
    """Цели дня: список без жёсткой привязки ко времени; время (по желанию) заполняется само."""
    TIMES = (0, 30, 60, 120, 180, 240)

    def __init__(self, store, parent):
        super().__init__(parent)
        self.store, self.toast = store, lambda s: None
        self.pill = InputPill(self)
        self.pill.setGeometry(20, 6, 390, 52)
        self.pill.submitted.connect(self.add)
        self.cats = ChipBar(self, bg="card")
        self.cats.setGeometry(0, 70, 430, 36)
        self.times = ChipBar(self, bg="card")
        self.times.setGeometry(0, 112, 430, 36)
        self.sheet = Sheet(self)
        self.sheet.setGeometry(0, 160, 430, 378)
        self.scroll = SmoothScroll(self.sheet)
        self.scroll.setGeometry(0, 14, 430, 364)
        self.list = GoalList(store)
        self.list.callbacks = (self.on_toggle, self.on_delete)
        self.scroll.setWidget(self.list)
        self.build()
        self.hide()

    def build(self):
        keep_c = self.cats.current_id() or "all"
        keep_t = self.times.current_id() or "0"
        ci = [("all", "gl.any", None)] + [(c["id"], cat_name(c), c["color"]) for c in self.store.d["categories"]]
        self.cats.set_items(ci, keep_c if any(i[0] == keep_c for i in ci) else "all")
        ti = [(str(m), "gl.t0" if m == 0 else fmt_hm(m)) for m in self.TIMES]
        self.times.set_items(ti, keep_t)
        self.pill.edit.setPlaceholderText(tr("gl.new"))

    def add(self, s):
        cat = self.cats.current_id() or "all"
        self.store.add_goal(s, cat, int(self.times.current_id() or 0))

    def on_toggle(self, gid):
        if self.store.toggle_goal(gid):
            self.toast(tr("gl.done"))

    def on_delete(self, gid):
        self.store.remove_goal(gid)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillPath(rr_path(QRectF(self.rect()), 0, 0, RADIUS, RADIUS), T.body)


class TasksPage(QWidget):
    def __init__(self, store, engine):
        super().__init__()
        self.store, self.engine, self.toast = store, engine, lambda s: None
        self.mode = "t"
        self.title = Label("tk.title", 24, W_SEMI, parent=self)
        self.title.setGeometry(24, 6, 380, 40)
        self.date = Label(fmt_date(), 11, W_MED, "text3", spacing=1.4, parent=self)
        self.date.setGeometry(25, 44, 380, 20)
        self.pill = InputPill(self)
        self.pill.setGeometry(20, 72, 390, 52)
        self.pill.submitted.connect(self.add)
        self.chips = ChipBar(self, bg="card")
        self.chips.setGeometry(0, 136, 430, 36)
        self.sheet = Sheet(self)
        self.sheet.setGeometry(0, 186, 430, 418)
        self.scroll = SmoothScroll(self.sheet)
        self.scroll.setGeometry(0, 14, 430, 404)
        self.list = TaskList(store)
        self.list.callbacks = (self.on_toggle, self.on_play, self.on_delete)
        self.scroll.setWidget(self.list)
        self.chips.selected.connect(self.on_filter)
        self.goals = GoalsView(store, self)
        self.goals.setGeometry(0, 66, 430, 538)
        self.sw = Segmented([("t", "gl.sw_tasks"), ("g", "gl.sw_goals")], "t", 196, self)
        self.sw.move(210, 12)
        self.sw.changed.connect(self.set_mode)
        self.build_chips()
        store.changed.connect(self.on_changed)
        self.list.sync()
        self.goals.list.sync()

    def set_mode(self, m):
        self.mode = m
        self.title.setText("tk.title" if m == "t" else "gl.title")
        self.sw.raise_()
        if m == "g":
            self.goals.build()
            self.goals.list.sync()
            self.goals.raise_()
            self.sw.raise_()
        fade(self.goals, m == "g")

    def build_chips(self, keep="all"):
        items = [("all", "tk.all", None)] + [(c["id"], cat_name(c), c["color"]) for c in self.store.d["categories"]]
        self.chips.set_items(items, keep if any(i[0] == keep for i in items) else "all")
        self.list.filter = self.chips.current_id() or "all"
        self.update_placeholder()

    def update_placeholder(self):
        f = self.list.filter
        self.pill.edit.setPlaceholderText(tr("tk.new") + ("" if f == "all" else f" · {cat_name(self.store.cat(f))}"))

    def on_filter(self, cid):
        self.list.filter = cid
        self.update_placeholder()
        self.list.sync()

    def on_changed(self, topic):
        if topic == "lang":
            self.date.setText(fmt_date())
            self.title.setText("tk.title" if self.mode == "t" else "gl.title")
        if topic in ("categories", "all", "lang"):
            self.build_chips(self.list.filter)
            self.goals.build()
        if topic in ("tasks", "categories", "all"):
            self.list.sync()
        if topic in ("goals", "categories", "all", "stats"):
            self.goals.list.sync()
            self.goals.toast = self.toast

    def add(self, s):
        f = self.list.filter
        self.store.add_task(s, "other" if f == "all" else f)

    def on_toggle(self, tid):
        if self.store.toggle_task(tid):
            self.toast(tr("tk.done"))

    def on_play(self, tid):
        self.store.set_current(tid)
        t = self.store.task(tid)
        if self.store.d["current_task"] == tid and t:
            self.toast(tr("tk.infocus", t=t["title"]))

    def on_delete(self, tid):
        self.store.remove_task(tid)

    def restyle(self):
        pass

    def on_show(self):
        self.goals.toast = self.toast
        self.list.sync()
        self.goals.list.sync()


# ───────────────────────────── focus page ─────────────────────────────
class TaskChip(Hoverable):
    clicked = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setFixedSize(382, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.setPen(NOPEN)
        p.setBrush(mix(T.body, T.track, .5 * self.hover))
        p.drawRoundedRect(QRectF(self.rect()), 18, 18)
        t = self.store.task(self.store.d.get("current_task"))
        if t:
            p.setBrush(QColor(self.store.cat(t["cat"])["color"]))
            p.drawEllipse(QPointF(26, 26), 5, 5)
            text(p, QRectF(44, 9, 300, 14), tr("chip.now"), F(9, W_MED, 1.4), T.text3)
            text(p, QRectF(44, 23, 300, 22), t["title"], F(15, W_MED), T.text)
        else:
            p.setBrush(NOBRUSH)
            p.setPen(QPen(T.text3, 1.6))
            p.drawEllipse(QPointF(26, 26), 5, 5)
            text(p, QRectF(44, 9, 300, 14), tr("chip.task"), F(9, W_MED, 1.4), T.text3)
            text(p, QRectF(44, 23, 300, 22), tr("chip.pick"), F(15, W_MED), T.text3)
        draw_icon(p, "chevron", self.width() - 24 + 2 * self.hover, 26, 14, T.text3, w=1.8)


def fmt_clock(s, up=False):
    s = int(math.floor(s + 1e-6)) if up else int(math.ceil(s - 1e-6))
    s = max(0, s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def fade(w, show, ms=240):
    """Плавно показать/скрыть виджет."""
    if show and w.isVisible() and not getattr(w, "_fading_out", False):
        return
    if not show and not w.isVisible():
        return
    old = getattr(w, "_fade_an", None)
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass
    if not _ANIM:
        w.setGraphicsEffect(None)
        w.setVisible(show)
        return
    eff = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(eff)
    if show:
        eff.setOpacity(0.0)
        w.show()
    an = QPropertyAnimation(eff, b"opacity", w)
    an.setDuration(dur(ms))
    an.setStartValue(0.0 if show else 1.0)
    an.setEndValue(1.0 if show else 0.0)
    an.setEasingCurve(OUT)

    def done():
        if not show:
            w.hide()
        w.setGraphicsEffect(None)
        w._fading_out = False
    w._fading_out = not show
    an.finished.connect(done)
    w._fade_an = an
    an.start()


class PillButton(Hoverable):
    clicked = Signal()

    def __init__(self, label="", kind="soft", icon=None, h=46, parent=None):
        super().__init__(parent)
        self.label, self.kind, self.icon, self._down = label, kind, icon, False
        self.setFixedHeight(h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_label(self, s, kind=None):
        self.label = s
        if kind:
            self.kind = kind
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._down = True
            A(self, "press", 1, 90)

    def mouseReleaseEvent(self, e):
        if self._down:
            self._down = False
            A(self, "press", 0, 320, BACK)
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        if not self.isEnabled():
            p.setOpacity(.4)
        w, h, hv = self.width(), self.height(), self.hover
        s = 1 - 0.025 * self.press
        p.translate(w / 2, h / 2)
        p.scale(s, s)
        p.translate(-w / 2, -h / 2)
        r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        if self.kind == "primary":
            p.setPen(NOPEN)
            p.setBrush(mix(T.primary, T.text, .12 * hv))
            fg = T.on_primary
        elif self.kind == "soft":
            p.setPen(QPen(T.hair, 1))
            p.setBrush(mix(T.body, T.track, .55 * hv))
            fg = T.text
        else:
            p.setPen(NOPEN)
            p.setBrush(alpha(T.track, .55 * hv))
            fg = mix(T.text2, T.text, hv)
        p.drawRoundedRect(r, h / 2, h / 2)
        f = F(14 if h >= 40 else 13, W_MED)
        s_ = tr(self.label)
        wd = QFontMetricsF(f).horizontalAdvance(s_)
        iw = 24 if self.icon else 0
        x0 = (w - wd - iw) / 2
        if self.icon:
            draw_icon(p, self.icon, x0 + 9, h / 2, 17, fg, w=1.9)
        text(p, QRectF(x0 + iw, 0, wd + 4, h), s_, f, fg, "l", False)


# ───────────────────────────── focus page ─────────────────────────────
class FinishSheet(QWidget):
    """Карточка «Завершить досрочно»: что сделать с уже отработанным временем."""
    t = fprop("t")
    choose = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self._title = self._sub = self._task = self._hint = ""
        self._has_task, self._h = False, 300
        self.b_task = PillButton("fin.task", "primary", "check", 50, self)
        self.b_only = PillButton("fin.only", "soft", None, 50, self)
        self.b_back = PillButton("fin.back", "ghost", None, 44, self)
        self.b_task.clicked.connect(lambda: self.choose.emit("task"))
        self.b_only.clicked.connect(lambda: self.choose.emit("only"))
        self.b_back.clicked.connect(lambda: self.choose.emit("cancel"))

    def card(self):
        return QRectF(14, 40 + (1 - ease_out(self.t)) * 26, self.width() - 28, self._h)

    def open_sheet(self, sub, task, hint, has_task):
        self._sub, self._task, self._hint, self._has_task = sub, task, hint, has_task
        self._h = 330 if has_task else 262
        self.b_task.setVisible(has_task)
        self.b_only.set_label("fin.only" if has_task else "fin.end", "soft" if has_task else "primary")
        self.b_only.icon = None if has_task else "check"
        self._layout()
        self.show()
        self.raise_()
        A(self, "t", 1.0, 420, QEasingCurve.Type.OutQuint, start=0)

    def close_sheet(self):
        if self.isVisible():
            A(self, "t", 0.0, 220, IN, finished=self.hide)

    def _layout(self):
        c = self.card()
        x, w = int(c.left()) + 22, int(c.width()) - 44
        y = int(c.top()) + 128
        if self._has_task:
            self.b_task.setGeometry(x, y, w, 50)
            y += 58
        self.b_only.setGeometry(x, y, w, 50)
        self.b_back.setGeometry(x, y + 58, w, 44)

    def resizeEvent(self, e):
        self._layout()

    def mousePressEvent(self, e):
        if not self.card().contains(e.position()):
            self.choose.emit("cancel")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        t = ease_out(self.t)
        p.fillPath(rr_path(QRectF(self.rect()), 0, 0, RADIUS, RADIUS), QColor(0, 0, 0, int(110 * t)))
        c = self.card()
        for i in range(14):
            p.setPen(NOPEN)
            p.setBrush(QColor(0, 0, 0, int(255 * 0.03 * (1 - i / 14) ** 2 * t)))
            p.drawRoundedRect(c.adjusted(-i, -i + 6, i, i + 6), 28 + i, 28 + i)
        p.setOpacity(clamp(t * 1.4))
        p.setPen(QPen(T.hair, 1))
        p.setBrush(T.card)
        p.drawRoundedRect(c, 28, 28)
        text(p, QRectF(c.left() + 20, c.top() + 20, c.width() - 40, 28), tr("fin.title"), F(20, W_SEMI), T.text, "c")
        text(p, QRectF(c.left() + 20, c.top() + 54, c.width() - 40, 20), self._sub, F(14, W_MED), T.text2, "c")
        y = c.top() + 78
        if self._has_task:
            text(p, QRectF(c.left() + 28, y, c.width() - 56, 20), "«" + self._task + "»", F(13, W_MED), T.accent
                 if T.accent_key != "graphite" else T.text, "c")
            y += 24
        if self._hint:
            wrap_text(p, QRectF(c.left() + 28, y, c.width() - 56, 34), self._hint, F(12, W_NORMAL), T.text3,
                      Qt.AlignmentFlag.AlignHCenter)


class TimeSheet(QWidget):
    """Гибкая настройка времени: фокус, перерывы, длинный перерыв, режим потока, свои пресеты."""
    t = fprop("t")

    def __init__(self, store, parent):
        super().__init__(parent)
        self.store = store
        self.hide()
        self._h = 496
        self.box = QWidget(self)
        self.lay = QVBoxLayout(self.box)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.close_btn = RoundButton("close", 34, "ghost", self)
        self.close_btn.clicked.connect(self.close_sheet)
        self.save = PillButton("ts.save", "soft", None, 46, self)
        self.save.clicked.connect(self.on_save)
        store.changed.connect(self.on_store)

    def card(self):
        return QRectF(14, 22 + (1 - ease_out(self.t)) * 26, self.width() - 28, self._h)

    def _rows(self):
        s = self.store

        def stp(label, key, lo, hi, last=False):
            st = Stepper(s.s(key), lo, hi, 1, "u.min" if key != "cycles" else "")
            st.changed.connect(lambda v, k=key: s.set_setting(k, v))
            return Row(label, None, st, last), st

        def tgl(label, sub, key, last=False):
            tg = Toggle(s.s(key))
            tg.toggled.connect(lambda v, k=key: s.set_setting(k, v))
            return Row(label, sub, tg, last)
        r1, self.st_focus = stp("ts.focus", "focus", 1, 480)
        r2 = tgl("ts.breaks", "ts.breaks_sub", "breaks")
        r3, self.st_short = stp("s.short", "short", 1, 120)
        r4, self.st_long = stp("s.long", "long", 1, 180)
        r5, self.st_cyc = stp("s.cycles", "cycles", 0, 12)
        r6 = tgl("ts.flow", "ts.flow_sub", "free_focus", True)
        return [r1, r2, r3, r4, r5, r6]

    def open_sheet(self):
        while self.lay.count():
            it = self.lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for r in self._rows():
            self.lay.addWidget(r)
        for w in self.box.findChildren(QWidget):
            if hasattr(w, "restyle"):
                w.restyle()
        self._dim()
        self._layout()
        self.refresh_save()
        self.show()
        self.raise_()
        A(self, "t", 1.0, 420, QEasingCurve.Type.OutQuint, start=0)

    def close_sheet(self):
        if self.isVisible():
            A(self, "t", 0.0, 220, IN, finished=self.hide)

    def _dim(self):
        on = bool(self.store.s("breaks"))
        free = bool(self.store.s("free_focus"))
        self.st_focus.setEnabled(not free)
        for st in (self.st_short, self.st_long, self.st_cyc):
            st.setEnabled(on and not free if st is not self.st_cyc else on)
        self.st_short.setEnabled(on and not free)
        self.st_long.setEnabled(on and not free)

    def on_store(self, topic):
        if topic in ("lang", "all"):
            self.hide()
        elif topic in ("settings", "presets") and self.isVisible():
            self._dim()
            self.refresh_save()

    def refresh_save(self):
        have = self.store.preset_index() >= 0
        full = len(self.store.d["presets"]) >= 6
        self.save.set_label("ts.remove" if have else "ts.save", "ghost" if have else "soft")
        self.save.setEnabled(have or not full)
        self.update()

    def on_save(self):
        self.store.toggle_preset()

    def _layout(self):
        c = self.card()
        self.box.setGeometry(int(c.left()), int(c.top()) + 62, int(c.width()), 352)
        self.close_btn.move(int(c.right()) - 20 - 34, int(c.top()) + 14)
        self.save.setGeometry(int(c.left()) + 22, int(c.top()) + 62 + 352 + 14, int(c.width()) - 44, 46)

    def resizeEvent(self, e):
        self._layout()

    def mousePressEvent(self, e):
        if not self.card().contains(e.position()):
            self.close_sheet()

    def paintEvent(self, e):
        self._layout()
        p = QPainter(self)
        p.setRenderHints(RH)
        t = ease_out(self.t)
        p.fillPath(rr_path(QRectF(self.rect()), 0, 0, RADIUS, RADIUS), QColor(0, 0, 0, int(110 * t)))
        c = self.card()
        for i in range(14):
            p.setPen(NOPEN)
            p.setBrush(QColor(0, 0, 0, int(255 * 0.03 * (1 - i / 14) ** 2 * t)))
            p.drawRoundedRect(c.adjusted(-i, -i + 6, i, i + 6), 28 + i, 28 + i)
        p.setPen(QPen(T.hair, 1))
        p.setBrush(T.card)
        p.drawRoundedRect(c, 28, 28)
        text(p, QRectF(c.left() + 24, c.top() + 14, c.width() - 90, 34), tr("ts.title"), F(20, W_SEMI), T.text)
        p.setPen(QPen(T.hair, 1))
        p.drawLine(QPointF(c.left() + 20, c.top() + 61), QPointF(c.right() - 20, c.top() + 61))


class FocusPage(QWidget):
    goto_tasks = Signal()
    goto_mini = Signal()
    BUILTIN = (("15", dict(focus=15, short=3, long=10, cycles=4)), ("25", dict(focus=25, short=5, long=15, cycles=4)),
               ("50", dict(focus=50, short=10, long=20, cycles=4)), ("90", dict(focus=90, short=20, long=30, cycles=3)))

    def __init__(self, store, engine):
        super().__init__()
        self.store, self.engine, self.toast = store, engine, lambda s: None
        self._view, self._ids = -1, []
        self.ring = TimerRing(self)
        self.ring.move(65, 0)
        self.sheet = Sheet(self)
        self.sheet.setGeometry(0, 270, 430, 334)
        self.chip = TaskChip(store, self.sheet)
        self.chip.move(24, 20)
        self.mini = RoundButton("mini", 34, "ghost", self)
        self.mini.move(386, 10)
        self.mini.clicked.connect(self.goto_mini)
        self.tune = RoundButton("sliders", 34, "ghost", self)
        self.tune.move(10, 10)
        self.tune.clicked.connect(self.open_time)
        self.main = RoundButton("playpause", 76, "primary", self.sheet)
        self.main.move(177, 88)
        self.reset = RoundButton("reset", 52, "ghost", self.sheet)
        self.reset.move(97, 100)
        self.fin = RoundButton("check", 52, "ghost", self.sheet)
        self.fin.move(281, 100)
        self.presets = ChipBar(self.sheet, bg="body", center=True)
        self.presets.setGeometry(0, 186, 430, 36)
        self.adj = QWidget(self.sheet)
        self.adj.setGeometry(0, 186, 430, 36)
        self.adj.hide()
        self.adj_btns = []
        for i, n in enumerate((-5, 5, 10)):
            b = PillButton("", "soft", None, 36, self.adj)
            b.setGeometry(49 + i * 114, 0, 104, 36)
            b.n = n
            b.clicked.connect(lambda n=n: self.engine.extend(n))
            self.adj_btns.append(b)
        self.info = Label("fo.free_hint", 13, W_NORMAL, "text3", "c", parent=self.sheet)
        self.info.setGeometry(24, 190, 382, 26)
        self.info.hide()
        self.fsheet = FinishSheet(self)
        self.tsheet = TimeSheet(store, self)
        self.fsheet.choose.connect(self.on_finish_choice)
        self.retr()
        self.presets.selected.connect(self.on_preset)
        self.main.clicked.connect(engine.toggle)
        self.ring.clicked.connect(engine.toggle)
        self.reset.clicked.connect(engine.reset)
        self.fin.clicked.connect(self.request_finish)
        self.chip.clicked.connect(self.goto_tasks)
        engine.tick.connect(self.on_tick)
        engine.state.connect(self.refresh)
        store.changed.connect(self.on_store)
        self.refresh()

    def resizeEvent(self, e):
        self.fsheet.setGeometry(self.rect())
        self.tsheet.setGeometry(self.rect())

    def retr(self):
        self.main.setToolTip(tr("tip.playpause"))
        self.reset.setToolTip(tr("tip.reset"))
        self.mini.setToolTip(tr("tip.mini"))
        self.tune.setToolTip(tr("tip.time"))
        for b in self.adj_btns:
            b.set_label(("−" if b.n < 0 else "+") + tr("p.min", n=abs(b.n)))
        self.build_presets()

    def build_presets(self):
        items = [(k, tr("p.min", n=v["focus"])) for k, v in self.BUILTIN]
        items.append(("free", "∞  " + tr("pr.flow")))
        for i, p in enumerate(self.store.d["presets"]):
            lab = f"{p['focus']}/{p['short']}" if p.get("breaks", True) else f"{p['focus']} · {tr('pr.nobreak')}"
            if p.get("free_focus"):
                lab = "∞ " + tr("pr.flow")
            items.append((f"u{i}", "★ " + lab))
        items.append(("custom", tr("pr.custom")))
        self._ids = [i[0] for i in items]
        self.presets.set_items(items, self.cur_preset_id())

    def cur_preset_id(self):
        s = self.store
        if s.s("free_focus"):
            return "free"
        cur = (s.s("focus"), s.s("short"), s.s("long"), s.s("cycles"))
        if s.s("breaks"):
            for k, v in self.BUILTIN:
                if (v["focus"], v["short"], v["long"], v["cycles"]) == cur:
                    return k
        i = s.preset_index()
        return f"u{i}" if i >= 0 else "custom"

    def open_time(self):
        self.tsheet.open_sheet()

    def on_store(self, topic):
        self.chip.update()
        if topic in ("lang", "all", "presets"):
            self.retr()
        if topic in ("lang", "all", "presets", "settings"):
            self.refresh()

    def on_tick(self):
        e = self.engine
        self.ring.set_view(e.remaining, e.prog, e.mode, e.running, e.started, e.cycle,
                           self.store.s("cycles"), e.free, e.total)

    def refresh(self):
        self.on_tick()
        e = self.engine
        self.main.set_morph(1.0 if e.running else 0.0)
        if e.mode == "focus":
            self.fin.icon = "check"
            self.fin.setEnabled(e.started)
            self.fin.setToolTip(tr("tip.finish"))
        else:
            self.fin.icon = "skip"
            self.fin.setEnabled(True)
            self.fin.setToolTip(tr("tip.skip"))
        self.fin.update()
        view = 2 if (e.started and e.free) else 1 if (e.started and e.mode != "focus" or e.started and not e.free) else 0
        if view != self._view:
            self._view = view
            fade(self.presets, view == 0)
            fade(self.adj, view == 1)
            fade(self.info, view == 2)
        if view == 0:
            cid = self.cur_preset_id()
            if cid not in self._ids:
                self.build_presets()
            else:
                self.presets.select(cid)
        if not e.started and self.fsheet.isVisible():
            self.fsheet.close_sheet()
        self.chip.update()

    def on_preset(self, cid):
        if cid == "custom":
            self.open_time()
            self.refresh()
            return
        if self.engine.started:
            self.toast(tr("tk.stop"))
            self.refresh()
            return
        s = self.store
        if cid == "free":
            s.update_settings({"free_focus": True})
        elif cid.startswith("u"):
            s.update_settings(dict(s.d["presets"][int(cid[1:])]))
        else:
            v = dict(next(v for k, v in self.BUILTIN if k == cid))
            v.update(breaks=True, free_focus=False)
            s.update_settings(v)

    # досрочное завершение
    def request_finish(self):
        e, s = self.engine, self.store
        if e.mode != "focus":
            e.skip()
            return
        if not e.started:
            return
        if not s.s("confirm_finish"):
            e.finish_early(False)
            return
        mins = e.elapsed / 60.0
        sub = tr("fin.worked", a=fmt_minutes(mins)) if e.free else tr("fin.of", a=fmt_minutes(mins), b=fmt_minutes(e.total / 60.0))
        t = s.task(s.d.get("current_task"))
        t = t if t and not t["done"] else None
        hint = tr("fin.short", n=s.s("min_session")) if mins < s.s("min_session") else tr("fin.counts")
        self.fsheet.open_sheet(sub, t["title"] if t else "", hint, bool(t))

    def on_finish_choice(self, c):
        self.fsheet.close_sheet()
        if c == "task":
            self.engine.finish_early(True)
        elif c == "only":
            self.engine.finish_early(False)

    def on_show(self):
        self.ring.play_intro()
        self.refresh()

    def restyle(self):
        pass


# ───────────────────────────── profile ─────────────────────────────
def fmt_hm(m):
    h, mm = divmod(int(round(m)), 60)
    return f"{h} {tr('u.hs')}" if h and not mm else fmt_minutes(m)


def wrap_text(p, rect, s, font, color, align=Qt.AlignmentFlag.AlignLeft):
    p.setFont(font)
    p.setPen(color)
    p.drawText(rect, int(align | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), s)


class Card(QWidget):
    t = fprop("t", 1.0)

    def __init__(self, store, h, parent=None):
        super().__init__(parent)
        self.store = store
        self.setFixedHeight(h)

    def play(self):
        A(self, "t", 1.0, 1300, OUT, start=0)

    def bg(self, p):
        p.setPen(QPen(T.hair, 1))
        p.setBrush(T.card)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 22, 22)

    def local(self, i, n=1, spread=.45):
        return ease_out((self.t - i * spread / max(n, 1)) / (1 - spread))


class ProfileHero(Card):
    hov = fprop("hov")

    def __init__(self, store, parent=None):
        super().__init__(store, 250, parent)
        self.setMouseTracking(True)
        self._hot = None
        self.edit = QLineEdit(self)
        self.edit.setMaxLength(24)
        self.edit.editingFinished.connect(lambda: store.set_name(self.edit.text()))
        self.edit.setText(store.d["profile"]["name"])
        self.restyle()

    def restyle(self):
        style_edit(self.edit, 24, W_SEMI, True)
        self.edit.setPlaceholderText(tr("pf.name"))

    def resizeEvent(self, e):
        self.edit.setGeometry(self.width() // 2 - 150, 138, 300, 38)

    def _where(self, pos):
        cx = self.width() / 2
        if self.store.avatar and math.dist((pos.x(), pos.y()), (cx + 37, 33)) < 12:
            return "x"
        return "avatar" if math.dist((pos.x(), pos.y()), (cx, 70)) < 41 else None

    def mouseMoveEvent(self, e):
        w = self._where(e.position())
        if w != self._hot:
            self._hot = w
            A(self, "hov", 1.0 if w == "avatar" else 0.0, 200)
            self.setCursor(Qt.CursorShape.PointingHandCursor if w else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._hot = None
        A(self, "hov", 0, 250)

    def mousePressEvent(self, e):
        w = self._where(e.position())
        if w == "x":
            self.store.clear_avatar()
        elif w == "avatar":
            p, _ = QFileDialog.getOpenFileName(self, tr("pf.pick"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
            if p:
                self.store.set_avatar(p)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        pr = self.store.d["profile"]
        xp = pr["xp"]
        lv = level_of(xp)
        lo, hi = level_bounds(lv)
        frac = clamp((xp - lo) / (hi - lo))
        t = ease_out(self.t)
        cx, cy, R = self.width() / 2, 70, 52
        p.setBrush(NOBRUSH)
        p.setPen(QPen(T.track, 4))
        p.drawEllipse(QPointF(cx, cy), R, R)
        if frac * t > .002:
            p.setPen(QPen(T.accent, 4, Qt.PenStyle.SolidLine, CAP_R))
            p.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R), 90 * 16, int(-frac * t * 360 * 16))
        circle = QPainterPath()
        circle.addEllipse(QPointF(cx, cy), 41, 41)
        av = self.store.avatar
        if av is not None:
            p.save()
            p.setClipPath(circle)
            p.drawPixmap(QRectF(cx - 41, cy - 41, 82, 82), av, QRectF(av.rect()))
            p.restore()
        else:
            if T.accent_key == "graphite":
                c1, c2 = (QColor("#5C5C66"), QColor("#2A2A2E")) if T.dark else (QColor("#4A4A52"), QColor("#111113"))
            else:
                c1, c2 = T.accent.lighter(118), T.accent.darker(140)
            g = QLinearGradient(cx - 40, cy - 40, cx + 40, cy + 40)
            g.setColorAt(0, c1)
            g.setColorAt(1, c2)
            p.setPen(NOPEN)
            p.setBrush(g)
            p.drawPath(circle)
            ini = (pr["name"].strip()[:1] or "G").upper()
            text(p, QRectF(cx - 40, cy - 40, 80, 80), ini, F(34, W_LIGHT), QColor("#FFFFFF"), "c")
        if self.hov > .01:
            p.setPen(NOPEN)
            p.setBrush(QColor(0, 0, 0, int(120 * self.hov)))
            p.drawPath(circle)
            draw_icon(p, "camera", cx, cy, 26, QColor(255, 255, 255, int(255 * self.hov)), w=1.7)
        if av is not None:
            p.setPen(QPen(T.card, 2.5))
            p.setBrush(T.track)
            p.drawEllipse(QPointF(cx + 37, 33), 10, 10)
            draw_icon(p, "close", cx + 37, 33, 10, T.text2, w=1.6)
        bx, by = cx + R * .74, cy + R * .74
        p.setPen(QPen(T.body, 3))
        p.setBrush(T.primary)
        p.drawEllipse(QPointF(bx, by), 15, 15)
        text(p, QRectF(bx - 15, by - 15, 30, 30), str(lv), F(13, W_SEMI), T.on_primary, "c")
        text(p, QRectF(0, 182, self.width(), 22), level_title(lv), F(14, W_MED), T.text2, "c")
        text(p, QRectF(0, 204, self.width(), 16), f"{int(xp - lo)} / {hi - lo} XP", F(11, W_MED, 1.4), T.text3, "c")
        bw = 180
        bx0 = (self.width() - bw) / 2
        p.setPen(NOPEN)
        p.setBrush(T.track)
        p.drawRoundedRect(QRectF(bx0, 228, bw, 4), 2, 2)
        p.setBrush(T.accent)
        p.drawRoundedRect(QRectF(bx0, 228, bw * frac * t, 4), 2, 2)


class WeeklyGoalCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 290, parent)
        self.edit = QLineEdit(self)
        self.edit.setMaxLength(60)
        self.edit.editingFinished.connect(lambda: store.set_weekly(title=self.edit.text().strip()))
        self.step = Stepper(int(store.d["weekly"].get("target", 0) // 60), 0, 80, 1, "u.hs", self)
        self.step.changed.connect(lambda v: store.set_weekly(target=v * 60))
        self.chips = ChipBar(self, bg="body", pad=24)
        self.chips.selected.connect(lambda c: store.set_weekly(cat=None if c == "all" else c))
        self.restyle()
        self.rebuild_chips()
        self.sync()

    def restyle(self):
        style_edit(self.edit, 17, W_MED)
        self.edit.setPlaceholderText(tr("wg.ph"))

    def rebuild_chips(self):
        items = [("all", "tk.all", None)] + [(c["id"], cat_name(c), c["color"]) for c in self.store.d["categories"]]
        cur = self.store.d["weekly"].get("cat") or "all"
        self.chips.set_items(items, cur if any(i[0] == cur for i in items) else "all")

    def sync(self):
        w = self.store.d["weekly"]
        if not self.edit.hasFocus():
            self.edit.setText(w.get("title", ""))
        tgt = int(w.get("target", 0))
        if self.step.value != tgt // 60:
            self.step.value = tgt // 60
            self.step.update()
        self.setFixedHeight(392 if tgt > 0 else 296)
        self.update()

    def resizeEvent(self, e):
        w = self.width()
        self.edit.setGeometry(24, 50, w - 48, 34)
        self.step.move(w - 24 - self.step.width(), 98)
        self.chips.setGeometry(0, 168, w, 36)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        w = self.width()
        done, target = self.store.goal_progress()
        t = ease_out(self.t)
        text(p, QRectF(24, 14, w - 120, 26), tr("wg.title"), F(16, W_SEMI), T.text)
        if target > 0:
            text(p, QRectF(w - 124, 14, 100, 26), f"{int(min(999, 100 * done / target))}%", F(14, W_MED), T.text2, "r")
        p.setPen(QPen(T.hair, 1))
        p.drawLine(QPointF(24, 88), QPointF(w - 24, 88))
        text(p, QRectF(24, 98, w - 190, 34), tr("wg.hours"), F(14, W_MED), T.text2)
        text(p, QRectF(24, 146, w - 48, 16), tr("wg.only"), F(10, W_MED, 1.4), T.text3)
        if target <= 0:
            wrap_text(p, QRectF(24, 224, w - 48, 60), tr("wg.none"), F(13, W_NORMAL), T.text3)
            return
        ref = max(target / 7.0 * 1.6, max(m for _, m in self.store.week_goal_days()), 1)
        text(p, QRectF(24, 222, w - 150, 36), fmt_minutes(done), F(26, W_LIGHT), T.text)
        text(p, QRectF(w - 150, 222, 126, 36), tr("wg.of", b=fmt_hm(target)), F(13, W_NORMAL), T.text2, "r")
        p.setPen(NOPEN)
        p.setBrush(T.track)
        p.drawRoundedRect(QRectF(24, 266, w - 48, 10), 5, 5)
        reached = done >= target
        p.setBrush(BREAK if reached else T.accent)
        p.drawRoundedRect(QRectF(24, 266, max(10.0, (w - 48) * clamp(done / target) * t), 10), 5, 5)
        days = self.store.week_goal_days()
        colw, base, top = (w - 48) / 7, 336, 292
        gy = base - (base - top) * (target / 7.0) / ref
        p.setPen(QPen(alpha(T.text3, .6), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(24, gy), QPointF(w - 24, gy))
        for i, (d, m) in enumerate(days):
            cx = 24 + colw * i + colw / 2
            hh = max(4.0, (base - top) * (m / ref) * self.local(i, 7, .5))
            is_today, future = d == date.today(), d > date.today()
            p.setPen(NOPEN)
            p.setBrush(T.accent if is_today else (T.track if m < 1 else alpha(T.accent, .45)))
            if future:
                p.setBrush(NOBRUSH)
                p.setPen(QPen(T.track, 1.2))
            p.drawRoundedRect(QRectF(cx - 10, base - hh, 20, hh), 6, 6)
            text(p, QRectF(cx - 20, base + 6, 40, 14), tr("d.%d" % d.weekday()), F(10, W_MED),
                 T.text if is_today else T.text3, "c")
        rem = target - done
        left = 7 - [d for d, _ in days].index(date.today()) if date.today() in [d for d, _ in days] else 1
        if rem <= 0:
            msg, col = tr("wg.reached"), BREAK
        elif left <= 1:
            msg, col = tr("wg.pace1", x=fmt_minutes(rem)), T.text2
        else:
            msg, col = tr("wg.pace", x=fmt_minutes(rem / left), n=left), T.text2
        text(p, QRectF(24, 360, w - 48, 20), msg, F(13, W_MED), col)


class IndexCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 188, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        val, f, a, d = self.store.index()
        t = ease_out(self.t)
        c, R = QPointF(78, 94), 50
        p.setBrush(NOBRUSH)
        p.setPen(QPen(T.track, 7))
        p.drawEllipse(c, R, R)
        if val * t > .3:
            p.setPen(QPen(T.accent, 7, Qt.PenStyle.SolidLine, CAP_R))
            p.drawArc(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), 90 * 16, int(-val / 100 * t * 360 * 16))
        text(p, QRectF(c.x() - 40, c.y() - 26, 80, 44), str(int(val * t)), F(36, W_LIGHT), T.text, "c")
        text(p, QRectF(c.x() - 44, c.y() + 14, 88, 14), tr("ix.of"), F(9, W_MED, 1.2), T.text3, "c")
        band = next(i for i, lim in enumerate((15, 35, 55, 75, 92, 101)) if val < lim)
        text(p, QRectF(150, 18, 232, 16), tr("ix.title"), F(10, W_MED, 1.6), T.text3)
        text(p, QRectF(150, 38, 232, 32), tr("ix.b%d" % band), F(24, W_SEMI), T.text)
        text(p, QRectF(150, 70, 232, 18), tr("ix.b%ds" % band), F(12, W_NORMAL), T.text2)
        for i, (lab, v) in enumerate((("tab.focus", f), ("ix.steady", a), ("tab.tasks", d))):
            y = 108 + i * 24
            text(p, QRectF(150, y, 90, 16), tr(lab), F(12, W_NORMAL), T.text2)
            p.setPen(NOPEN)
            p.setBrush(T.track)
            p.drawRoundedRect(QRectF(246, y + 5, 124, 5), 2.5, 2.5)
            p.setBrush(T.accent)
            p.drawRoundedRect(QRectF(246, y + 5, 124 * v * self.local(i, 3), 5), 2.5, 2.5)


class StatsCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 156, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        tf, ss, dn = self.store.totals()
        st = self.store.streak()
        cells = [("ps.streak", f"{int(st * self.local(0, 4))}", "ps.days"), ("tab.focus", None, "ps.total"),
                 ("tab.tasks", f"{int(dn * self.local(2, 4))}", "ps.done"),
                 ("ps.sessions", f"{int(ss * self.local(3, 4))}", "ps.sessions_u")]
        w2, h2 = self.width() / 2, self.height() / 2
        p.setPen(QPen(T.hair, 1))
        p.drawLine(QPointF(w2, 18), QPointF(w2, self.height() - 18))
        p.drawLine(QPointF(18, h2), QPointF(self.width() - 18, h2))
        for i, (lab, val, unit) in enumerate(cells):
            x, y = (i % 2) * w2 + 24, (i // 2) * h2
            if val is None:
                val = fmt_total(tf * self.local(1, 4))
            text(p, QRectF(x, y + 12, w2 - 40, 14), tr(lab).upper(), F(10, W_MED, 1.4), T.text3)
            text(p, QRectF(x, y + 28, w2 - 40, 30), val, F(26, W_LIGHT), T.text)
            text(p, QRectF(x, y + 56, w2 - 40, 16), tr(unit), F(12, W_NORMAL), T.text2)


class WeekCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 236, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        wk = self.store.week()
        goal = self.store.s("goal")
        total = sum(m for _, m in wk)
        text(p, QRectF(24, 16, 200, 24), tr("wk.title"), F(16, W_SEMI), T.text)
        text(p, QRectF(self.width() - 204, 16, 180, 24), fmt_minutes(total), F(14, W_MED), T.text2, "r")
        top, base = 76, 190
        mx = max(goal, max(m for _, m in wk)) * 1.1
        gy = base - (base - top) * goal / mx
        p.setPen(QPen(alpha(T.text3, .5), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(20, gy), QPointF(self.width() - 20, gy))
        colw = (self.width() - 48) / 7
        for i, (d, m) in enumerate(wk):
            cx = 24 + colw * i + colw / 2
            hh = (base - top) * (m / mx) * self.local(i, 7, .5)
            p.setPen(NOPEN)
            p.setBrush(T.accent if i == 6 else T.track)
            p.drawRoundedRect(QRectF(cx - 11, base - max(hh, 6), 22, max(hh, 6)), 8, 8)
            if m >= 1 and self.local(i, 7, .5) > .6:
                text(p, QRectF(cx - 25, base - hh - 18, 50, 14), str(int(m)), F(10, W_MED), T.text2, "c")
            text(p, QRectF(cx - 20, base + 12, 40, 16), tr("d.%d" % d.weekday()), F(10, W_MED, 1.0),
                 T.text if i == 6 else T.text3, "c")


class BadgesCard(Card):
    ROW = 92

    def __init__(self, store, parent=None):
        super().__init__(store, 60 + ((len(ACH) + 3) // 4) * self.ROW, parent)
        self.setMouseTracking(True)

    def _idx(self, pos):
        cw = (self.width() - 32) / 4
        col, row = int((pos.x() - 16) // cw), int((pos.y() - 46) // self.ROW)
        i = row * 4 + col
        return i if 0 <= col < 4 and 0 <= row and 0 <= i < len(ACH) else -1

    def mouseMoveEvent(self, e):
        i = self._idx(e.position())
        if i < 0:
            self.setToolTip("")
        else:
            k = ACH[i][0]
            self.setToolTip(f"{tr('ach.' + k)}\n{tr('ach.' + k + '.d')}")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        a = self.store.d["achievements"]
        text(p, QRectF(24, 16, 200, 24), tr("bd.title"), F(16, W_SEMI), T.text)
        text(p, QRectF(self.width() - 204, 16, 180, 24), f"{len(a)} / {len(ACH)}", F(14, W_MED), T.text2, "r")
        cw = (self.width() - 32) / 4
        for i, (k, glyph) in enumerate(ACH):
            cx, cy = 16 + cw * (i % 4) + cw / 2, 82 + (i // 4) * self.ROW
            s = ease_back(self.local(i, len(ACH), .6))
            on = k in a
            p.setOpacity(clamp(s))
            p.setPen(NOPEN)
            r = 26 * max(s, 0.01)
            if on:
                p.setBrush(alpha(T.accent, .12))
                p.drawEllipse(QPointF(cx, cy), r + 4, r + 4)
                p.setBrush(T.primary)
            else:
                p.setBrush(T.body)
            p.drawEllipse(QPointF(cx, cy), r, r)
            col = T.on_primary if on else T.text3
            if glyph.startswith("icon:"):
                draw_icon(p, glyph[5:], cx, cy, 24, col, w=1.9)
            else:
                text(p, QRectF(cx - 26, cy - 26, 52, 52), glyph, F(15 if len(glyph) < 4 else 12, W_SEMI), col, "c")
            text(p, QRectF(cx - cw / 2 + 2, cy + 33, cw - 4, 16), tr("ach." + k), F(11, W_MED), T.text if on else T.text3, "c")
            p.setOpacity(1)


class ProfilePage(SmoothScroll):
    def __init__(self, store, engine):
        super().__init__()
        self.store = store
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(20, 6, 20, 110)
        lay.setSpacing(14)
        self.hero, self.goal = ProfileHero(store), WeeklyGoalCard(store)
        self.cards = [self.hero, self.goal, IndexCard(store), StatsCard(store), WeekCard(store), BadgesCard(store), RulesCard(store)]
        for c in self.cards:
            lay.addWidget(c)
        lay.addStretch(1)
        self.setWidget(body)
        store.changed.connect(self.on_changed)

    def on_changed(self, topic):
        if topic in ("lang", "all", "categories"):
            self.hero.restyle()
            self.goal.restyle()
            self.goal.rebuild_chips()
        if topic in ("lang", "all", "categories", "goal", "stats", "settings"):
            self.goal.sync()
        for c in self.cards:
            c.update()

    def on_show(self):
        self.goal.sync()
        for c in self.cards:
            c.play()

    def restyle(self):
        pass


# ───────────────────────────── statistics ─────────────────────────────
def nice_max(v):
    for u in (15, 30, 60, 90, 120, 180, 240, 360, 480, 600, 720, 960, 1200, 1800, 2400, 3600, 4800, 6000, 9000, 12000,
              18000, 24000, 36000, 60000):
        if v <= u:
            return u
    return int(math.ceil(v / 60000.0)) * 60000


def axis_label(m):
    return f"{m / 60:g}{tr('u.h1')}" if m >= 60 else f"{int(m)}"


def smooth_path(pts, lo, hi):
    path = QPainterPath(QPointF(*pts[0]))
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, clamp(p1[1] + (p2[1] - p0[1]) / 6, lo, hi))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, clamp(p2[1] - (p3[1] - p1[1]) / 6, lo, hi))
        path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*p2))
    return path


def draw_tip(p, ax, ay, lines, W):
    f1, f2 = F(12, W_SEMI), F(11, W_NORMAL)
    wd = max(QFontMetricsF(f1).horizontalAdvance(lines[0]),
             max((QFontMetricsF(f2).horizontalAdvance(s) for s in lines[1:]), default=0)) + 26
    h = 14 + 17 * len(lines)
    r = QRectF(clamp(ax - wd / 2, 8, W - wd - 8), ay - h - 12, wd, h)
    if r.top() < 4:
        r.moveTop(ay + 14)
    p.setPen(QPen(QColor(255, 255, 255, 28), 1))
    p.setBrush(alpha(T.capsule, .96))
    p.drawRoundedRect(r, 11, 11)
    for i, s in enumerate(lines):
        text(p, QRectF(r.left(), r.top() + 8 + i * 17, r.width(), 17), s, f1 if i == 0 else f2,
             QColor("#F5F5F7") if i == 0 else QColor("#B4B4BA"), "c", False)


def fmt_day(d):
    return tr("date.fmt", wd=tr("wd.%d" % d.weekday()), mo=tr("mo.%d" % (d.month - 1)), d=d.day)


def chart_series(store, rng, key):
    """[(axis_label, tooltip_title, value, is_current)] для недели/месяца/года."""
    out = []
    if rng == "y":
        ms = store.months(12)
        for i, (d, foc, xp, ss) in enumerate(ms):
            v = foc if key == "focus" else xp
            out.append((tr("mo.%d" % (d.month - 1))[:3], f"{tr('mo.%d' % (d.month - 1))} {d.year}", v, i == len(ms) - 1))
        return out
    n = 7 if rng == "w" else 30
    for i, (d, v) in enumerate(store.span(n)):
        val = v["focus"] if key == "focus" else v.get("xp", 0.0)
        lab = tr("d.%d" % d.weekday()) if rng == "w" else (str(d.day) if (n - 1 - i) % 5 == 0 else "")
        out.append((lab, fmt_day(d), val, i == n - 1))
    return out


class RangeCard(Card):
    def __init__(self, store, h, parent=None):
        super().__init__(store, h, parent)
        self.rng, self.hot = "w", -1
        self.setMouseTracking(True)

    def set_range(self, r):
        self.rng, self.hot = r, -1
        self.play()

    def leaveEvent(self, e):
        self.hot = -1
        self.update()

    def title(self, p, key, right=""):
        text(p, QRectF(24, 16, self.width() - 150, 24), tr(key), F(16, W_SEMI), T.text)
        if right:
            text(p, QRectF(self.width() - 170, 16, 146, 24), right, F(14, W_MED), T.text2, "r")


class StatsHero(RangeCard):
    def __init__(self, store, parent=None):
        super().__init__(store, 212, parent)

    def n(self):
        return {"w": 7, "m": 30, "y": 365}[self.rng]

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        s, n, t = self.store, self.n(), ease_out(self.t)
        cur, prev = s.span(n), s.span(n, n)
        tot = sum(v["focus"] for _, v in cur)
        ptot = sum(v["focus"] for _, v in prev)
        ses = sum(v["sessions"] for _, v in cur)
        act = sum(1 for _, v in cur if v["focus"] >= 1)
        best = max((v["focus"] for _, v in cur), default=0)
        text(p, QRectF(24, 18, self.width() - 48, 16), tr("st.total_" + self.rng).upper(), F(10, W_MED, 1.6), T.text3)
        text(p, QRectF(24, 40, self.width() - 48, 48), fmt_minutes(tot * t), F(36, W_LIGHT), T.text, "l", False)
        if ptot > 0:
            dl = (tot - ptot) / ptot * 100
            up = dl >= 0
            col = BREAK if up else QColor("#FF6B57")
            label = f"{'▲' if up else '▼'} {abs(dl):.0f}%"
            f = F(12, W_SEMI)
            wd = QFontMetricsF(f).horizontalAdvance(label) + 22
            r = QRectF(24, 96, wd, 24)
            p.setPen(NOPEN)
            p.setBrush(alpha(col, .16))
            p.drawRoundedRect(r, 12, 12)
            text(p, r, label, f, col, "c", False)
            text(p, QRectF(r.right() + 10, 96, 220, 24), tr("st.vs_" + self.rng), F(12, W_NORMAL), T.text2)
        else:
            text(p, QRectF(24, 96, 300, 24), tr("st.nodata"), F(12, W_NORMAL), T.text3)
        p.setPen(QPen(T.hair, 1))
        p.drawLine(QPointF(24, 138), QPointF(self.width() - 24, 138))
        cw = (self.width() - 48) / 3
        cells = ((tr("ps.sessions"), f"{int(ses * t)}"), (tr("st.avg_active"), fmt_minutes(tot / max(act, 1) * t)),
                 (tr("st.best_day"), fmt_minutes(best * t)))
        for i, (lab, val) in enumerate(cells):
            x = 24 + cw * i
            text(p, QRectF(x, 148, cw - 6, 14), lab.upper(), F(9, W_MED, 1.2), T.text3)
            text(p, QRectF(x, 166, cw - 4, 30), val, F(16, W_MED), T.text, "l")


class BarsCard(RangeCard):
    def __init__(self, store, parent=None):
        super().__init__(store, 276, parent)
        self.L, self.R, self.top, self.base = 42, 20, 82, 226

    def geo(self, n):
        slot = (self.width() - self.L - self.R) / n
        return slot

    def mouseMoveEvent(self, e):
        data = chart_series(self.store, self.rng, "focus")
        slot = self.geo(len(data))
        i = int((e.position().x() - self.L) // slot)
        i = i if 0 <= i < len(data) and self.top - 30 <= e.position().y() <= self.base + 30 else -1
        if i != self.hot:
            self.hot = i
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        data = chart_series(self.store, self.rng, "focus")
        n, W = len(data), self.width()
        goal = self.store.s("goal") if self.rng != "y" else 0
        peak = max(v for _, _, v, _ in data)
        self.title(p, "st.bars", f"{tr('st.peak')} {fmt_minutes(peak)}" if peak > 0 else "")
        mx = nice_max(max(peak, goal * 1.05))
        slot = self.geo(n)
        for k in range(3):
            y = self.base - (self.base - self.top) * k / 2
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(self.L, y), QPointF(W - self.R, y))
            text(p, QRectF(8, y - 8, self.L - 14, 16), axis_label(mx * k / 2), F(10, W_NORMAL), T.text3, "r")
        if goal:
            gy = self.base - (self.base - self.top) * goal / mx
            p.setPen(QPen(alpha(T.text2, .7), 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(self.L, gy), QPointF(W - self.R, gy))
        bw = min(26.0, slot * 0.58)
        for i, (lab, tip, v, cur) in enumerate(data):
            cx = self.L + slot * i + slot / 2
            k = self.local(i, n, .55)
            hh = (self.base - self.top) * (v / mx) * k
            hh = max(hh, 3.0 if v > 0 else 0.0) if k > 0 else 0
            hot = i == self.hot
            if goal and v >= goal:
                c = T.accent
            else:
                c = alpha(T.accent, .42)
            if cur:
                c = T.accent
            if hot:
                c = mix(c, T.text, .25)
            if hh > 0:
                g = QLinearGradient(0, self.base - hh, 0, self.base)
                g.setColorAt(0, c)
                g.setColorAt(1, alpha(c, c.alphaF() * .75))
                p.setPen(NOPEN)
                p.setBrush(g)
                p.drawRoundedRect(QRectF(cx - bw / 2, self.base - hh, bw, hh), min(8, bw / 2), min(8, bw / 2))
            else:
                p.setPen(NOPEN)
                p.setBrush(T.track)
                p.drawRoundedRect(QRectF(cx - bw / 2, self.base - 3, bw, 3), 1.5, 1.5)
            if lab:
                text(p, QRectF(cx - slot, self.base + 12, slot * 2, 16), lab, F(10, W_MED, 0.6 if self.rng == "w" else 0),
                     T.text if cur else T.text3, "c")
        if self.hot >= 0:
            lab, tip, v, cur = data[self.hot]
            cx = self.L + slot * self.hot + slot / 2
            hh = (self.base - self.top) * (v / mx)
            draw_tip(p, cx, self.base - hh, [tip, fmt_minutes(v)], W)


class DonutCard(RangeCard):
    def __init__(self, store, parent=None):
        super().__init__(store, 262, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        s = self.store
        n = {"w": 7, "m": 30, "y": 365}[self.rng]
        ct = sorted(s.cat_totals(s.span(n)).items(), key=lambda kv: -kv[1])
        tot = sum(v for _, v in ct)
        self.title(p, "st.cats")
        c, R = QPointF(100, 150), 62.0
        t = ease_out(self.t)
        p.setBrush(NOBRUSH)
        p.setPen(QPen(T.track, 18))
        p.drawEllipse(c, R, R)
        if tot <= 0:
            text(p, QRectF(c.x() - 50, c.y() - 10, 100, 20), "—", F(20, W_LIGHT), T.text3, "c")
            text(p, QRectF(190, 120, self.width() - 214, 40), tr("st.nodata"), F(13, W_NORMAL), T.text3, "l")
            return
        gap = 2.0 if len(ct) > 1 else 0.0
        rect = QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R)
        ang = 90.0
        for cid, v in ct:
            sw = v / tot * 360.0 * t
            col = QColor(s.cat(cid)["color"])
            if sw > gap + .3:
                p.setPen(QPen(col, 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                p.drawArc(rect, int(ang * 16), int(-(sw - gap) * 16))
            ang -= sw
        text(p, QRectF(c.x() - 46, c.y() - 20, 92, 28), fmt_total(tot * t), F(20, W_LIGHT), T.text, "c")
        text(p, QRectF(c.x() - 46, c.y() + 8, 92, 14), tr("tab.focus").upper(), F(9, W_MED, 1.2), T.text3, "c")
        x0 = 190
        rows = ct[:5]
        for i, (cid, v) in enumerate(rows):
            y = 70 + i * 36
            k = self.local(i, len(rows), .6)
            p.setOpacity(k)
            cat = s.cat(cid)
            p.setPen(NOPEN)
            p.setBrush(QColor(cat["color"]))
            p.drawEllipse(QPointF(x0 + 5, y + 14), 5, 5)
            text(p, QRectF(x0 + 18, y + 2, self.width() - x0 - 90, 18), cat_name(cat), F(13, W_MED), T.text)
            text(p, QRectF(x0 + 18, y + 19, self.width() - x0 - 90, 14), fmt_hm(v), F(11, W_NORMAL), T.text2)
            text(p, QRectF(self.width() - 76, y + 2, 52, 18), f"{v / tot * 100:.0f}%", F(13, W_MED), T.text2, "r")
            p.setOpacity(1)


class PointsCard(RangeCard):
    def __init__(self, store, parent=None):
        super().__init__(store, 262, parent)
        self.L, self.R, self.top, self.base = 42, 24, 84, 214

    def pts(self, data):
        n = len(data)
        mx = max((v for _, _, v, _ in data), default=0)
        mx = max(mx * 1.15, 10.0)
        xs = [self.L + (self.width() - self.L - self.R) * i / max(n - 1, 1) for i in range(n)]
        ys = [self.base - (self.base - self.top) * (v / mx) for _, _, v, _ in data]
        return mx, xs, ys

    def mouseMoveEvent(self, e):
        data = chart_series(self.store, self.rng, "xp")
        mx, xs, ys = self.pts(data)
        i = min(range(len(xs)), key=lambda k: abs(xs[k] - e.position().x()))
        i = i if abs(xs[i] - e.position().x()) < 24 + (self.width() / len(xs)) / 2 else -1
        if i != self.hot:
            self.hot = i
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        data = chart_series(self.store, self.rng, "xp")
        W = self.width()
        total = sum(v for _, _, v, _ in data)
        self.title(p, "st.points", f"+{total:.0f}")
        lv = level_of(self.store.d["profile"]["xp"])
        text(p, QRectF(24, 40, W - 48, 18), tr("st.level_now", l=lv, t=level_title(lv)), F(12, W_NORMAL), T.text2)
        mx, xs, ys = self.pts(data)
        for k in range(3):
            y = self.base - (self.base - self.top) * k / 2
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(self.L, y), QPointF(W - self.R, y))
            text(p, QRectF(8, y - 8, self.L - 14, 16), f"{mx * k / 2:.0f}", F(10, W_NORMAL), T.text3, "r")
        pts = list(zip(xs, ys))
        t = ease_out(self.t)
        p.save()
        p.setClipRect(QRectF(0, 0, self.L + (W - self.L - self.R + 6) * t, self.height()))
        line = smooth_path(pts, self.top - 6, self.base)
        area = QPainterPath(line)
        area.lineTo(pts[-1][0], self.base)
        area.lineTo(pts[0][0], self.base)
        area.closeSubpath()
        g = QLinearGradient(0, self.top, 0, self.base)
        g.setColorAt(0, alpha(T.accent, .30))
        g.setColorAt(1, alpha(T.accent, 0))
        p.setPen(NOPEN)
        p.setBrush(g)
        p.drawPath(area)
        p.setBrush(NOBRUSH)
        p.setPen(QPen(T.accent, 2.4, Qt.PenStyle.SolidLine, CAP_R, JOIN_R))
        p.drawPath(line)
        if len(data) <= 12:
            for (x, y) in pts:
                p.setPen(QPen(T.accent, 2))
                p.setBrush(T.card)
                p.drawEllipse(QPointF(x, y), 3.6, 3.6)
        p.restore()
        step = max(1, len(data) // 7) if self.rng != "w" else 1
        for i, (lab, tip, v, cur) in enumerate(data):
            if self.rng == "m":
                lab = data[i][0]
            if lab:
                text(p, QRectF(xs[i] - 24, self.base + 12, 48, 16), lab, F(10, W_MED, 0.6 if self.rng == "w" else 0),
                     T.text if cur else T.text3, "c")
        if self.hot >= 0:
            x, y = pts[self.hot]
            p.setPen(QPen(alpha(T.text3, .6), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, self.top - 6), QPointF(x, self.base))
            p.setPen(QPen(T.accent, 2.4))
            p.setBrush(T.card)
            p.drawEllipse(QPointF(x, y), 5.5, 5.5)
            draw_tip(p, x, y - 4, [data[self.hot][1], f"+{data[self.hot][2]:.0f} " + tr("st.pts_u")], W)


class HeatCard(Card):
    WEEKS = 16

    def __init__(self, store, parent=None):
        super().__init__(store, 262, parent)
        self.hot = None
        self.setMouseTracking(True)

    def geo(self):
        gap, left = 4.0, 30.0
        cell = (self.width() - 24 - left - gap * (self.WEEKS - 1)) / self.WEEKS
        return cell, gap, left

    def start(self):
        return week_start_of(date.today(), self.store.s("week_start")) - timedelta(weeks=self.WEEKS - 1)

    def cell_at(self, pos):
        cell, gap, left = self.geo()
        c, r = int((pos.x() - left) // (cell + gap)), int((pos.y() - 66) // (cell + gap))
        if 0 <= c < self.WEEKS and 0 <= r < 7:
            d = self.start() + timedelta(days=c * 7 + r)
            if d <= date.today():
                return (c, r, d)
        return None

    def mouseMoveEvent(self, e):
        h = self.cell_at(e.position())
        if (h and h[2]) != (self.hot and self.hot[2]):
            self.hot = h
            self.update()

    def leaveEvent(self, e):
        self.hot = None
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        s = self.store
        goal = max(1, s.s("goal"))
        cell, gap, left = self.geo()
        st = self.start()
        act = sum(1 for i in range(self.WEEKS * 7) if st + timedelta(days=i) <= date.today()
                  and s.day((st + timedelta(days=i)).isoformat())["focus"] >= 1)
        text(p, QRectF(24, 16, self.width() - 150, 24), tr("st.heat"), F(16, W_SEMI), T.text)
        text(p, QRectF(self.width() - 170, 16, 146, 24), tr("st.active_days", n=act), F(14, W_MED), T.text2, "r")
        wk0 = 0 if s.s("week_start") == "mon" else 6
        for r in (0, 2, 4):
            text(p, QRectF(18, 66 + r * (cell + gap), 22, cell), tr("d.%d" % ((wk0 + r) % 7))[:2], F(9, W_MED), T.text3, "l")
        for c in range(self.WEEKS):
            k = self.local(c, self.WEEKS, .6)
            for r in range(7):
                d = st + timedelta(days=c * 7 + r)
                if d > date.today():
                    continue
                m = s.day(d.isoformat())["focus"]
                f = m / goal
                a = 0.0 if m < 1 else .28 if f < .34 else .5 if f < .67 else .75 if f < 1 else 1.0
                x, y = left + c * (cell + gap), 66 + r * (cell + gap)
                p.setOpacity(clamp(k))
                p.setPen(NOPEN)
                p.setBrush(T.track if a == 0 else alpha(T.accent, a))
                sz = cell * (0.6 + 0.4 * k)
                rect = QRectF(x + (cell - sz) / 2, y + (cell - sz) / 2, sz, sz)
                p.drawRoundedRect(rect, 5, 5)
                if d == date.today():
                    p.setBrush(NOBRUSH)
                    p.setPen(QPen(T.text, 1.4))
                    p.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), 6, 6)
                p.setOpacity(1)
        y = 66 + 7 * (cell + gap) + 8
        text(p, QRectF(24, y, 50, 16), tr("st.less"), F(10, W_NORMAL), T.text3, "l")
        for i, a in enumerate((0, .28, .5, .75, 1.0)):
            p.setPen(NOPEN)
            p.setBrush(T.track if a == 0 else alpha(T.accent, a))
            p.drawRoundedRect(QRectF(66 + i * 20, y + 1, 14, 14), 4, 4)
        text(p, QRectF(172, y, 60, 16), tr("st.more"), F(10, W_NORMAL), T.text3, "l")
        if self.hot:
            c, r, d = self.hot
            x, yy = left + c * (cell + gap) + cell / 2, 66 + r * (cell + gap)
            draw_tip(p, x, yy, [fmt_day(d), fmt_minutes(s.day(d.isoformat())["focus"])], self.width())


class HoursCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 232, parent)
        self.hot = -1
        self.setMouseTracking(True)

    def mouseMoveEvent(self, e):
        w = (self.width() - 48) / 24
        i = int((e.position().x() - 24) // w)
        i = i if 0 <= i < 24 else -1
        if i != self.hot:
            self.hot = i
            self.update()

    def leaveEvent(self, e):
        self.hot = -1
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        hrs = self.store.hour_totals()
        tot = sum(hrs)
        text(p, QRectF(24, 16, self.width() - 48, 24), tr("st.hours"), F(16, W_SEMI), T.text)
        best = max(range(24), key=lambda h: hrs[h] + hrs[(h + 1) % 24]) if tot > 0 else -1
        if tot > 0:
            text(p, QRectF(24, 40, self.width() - 48, 18), tr("st.best_time", a=f"{best:02d}:00", b=f"{(best + 2) % 24:02d}:00"),
                 F(12, W_NORMAL), T.text2)
        else:
            text(p, QRectF(24, 40, self.width() - 48, 18), tr("st.nodata"), F(12, W_NORMAL), T.text3)
        top, base = 84, 180
        mx = max(max(hrs), 1.0)
        w = (self.width() - 48) / 24
        for h in range(24):
            k = self.local(h, 24, .6)
            hh = max((base - top) * hrs[h] / mx * k, 4.0 if k > 0 else 0)
            inb = best >= 0 and h in (best, (best + 1) % 24)
            c = T.accent if inb else alpha(T.accent, .35) if hrs[h] > 0 else T.track
            if h == self.hot:
                c = mix(c, T.text, .25)
            p.setPen(NOPEN)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(24 + h * w + 2, base - hh, w - 4, hh), 3.5, 3.5)
        for h in (0, 6, 12, 18):
            text(p, QRectF(24 + h * w - 10, base + 10, 40, 14), f"{h:02d}", F(10, W_MED), T.text3, "l")
        if self.hot >= 0:
            hh = (base - top) * hrs[self.hot] / mx
            draw_tip(p, 24 + self.hot * w + w / 2, base - hh, [f"{self.hot:02d}:00", fmt_minutes(hrs[self.hot])], self.width())


class RecordsCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 168, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        s = self.store
        tf, ss, dn = s.totals()
        bk, bm = s.best_day()
        cells = [("st.rec_streak", f"{int(s.longest_streak() * self.local(0, 4))}", tr("ps.days")),
                 ("st.best_day", fmt_minutes(bm * self.local(1, 4)), fmt_day(date.fromisoformat(bk)) if bk else "—"),
                 ("st.avg_sess", fmt_minutes((tf / ss if ss else 0) * self.local(2, 4)), tr("ps.sessions_u")),
                 ("st.rec_early", f"{int(s.early_total() * self.local(3, 4))}", tr("st.rec_early_u"))]
        w2, h2 = self.width() / 2, self.height() / 2
        p.setPen(QPen(T.hair, 1))
        p.drawLine(QPointF(w2, 18), QPointF(w2, self.height() - 18))
        p.drawLine(QPointF(18, h2), QPointF(self.width() - 18, h2))
        for i, (lab, val, unit) in enumerate(cells):
            x, y = (i % 2) * w2 + 24, (i // 2) * h2
            text(p, QRectF(x, y + 12, w2 - 40, 14), tr(lab).upper(), F(10, W_MED, 1.2), T.text3)
            text(p, QRectF(x, y + 28, w2 - 40, 30), val, F(22, W_LIGHT), T.text)
            text(p, QRectF(x, y + 56, w2 - 40, 16), unit, F(12, W_NORMAL), T.text2)


class StatsPage(SmoothScroll):
    def __init__(self, store, engine=None):
        super().__init__()
        self.store = store
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(20, 6, 20, 110)
        lay.setSpacing(14)
        self.chips = ChipBar(None, bg="card", center=True, pad=0)
        self.chips.set_items([("w", "st.r_w"), ("m", "st.r_m"), ("y", "st.r_y")], "w")
        self.chips.selected.connect(self.on_range)
        lay.addWidget(self.chips)
        self.rcards = [StatsHero(store), BarsCard(store), DonutCard(store), PointsCard(store)]
        self.cards = self.rcards + [HeatCard(store), HoursCard(store), RecordsCard(store)]
        for c in self.cards:
            lay.addWidget(c)
        lay.addStretch(1)
        self.setWidget(body)
        store.changed.connect(self.on_changed)

    def on_range(self, r):
        for c in self.rcards:
            c.set_range(r)

    def on_changed(self, topic):
        if topic == "lang":
            self.chips.relayout()
        if topic in ("lang", "all", "stats", "settings", "categories", "goals", "tasks"):
            for c in self.cards:
                c.update()

    def on_show(self):
        self.chips.relayout()
        for c in self.cards:
            c.play()

    def restyle(self):
        pass


class RulesCard(Card):
    RULES = (("rule.focus", "+1 / " + "min"), ("rule.streak", "×1.4"), ("rule.session", "+5"), ("rule.deep", "+5"),
             ("rule.task", "+6…20"), ("rule.early", "+8"), ("rule.goal", "+8 / +12"), ("rule.day", "+20"),
             ("rule.week", "+100"))

    def __init__(self, store, parent=None):
        super().__init__(store, 74 + len(self.RULES) * 30 + 56, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        text(p, QRectF(24, 16, self.width() - 48, 24), tr("rule.title"), F(16, W_SEMI), T.text)
        text(p, QRectF(24, 40, self.width() - 48, 18), tr("rule.sub"), F(12, W_NORMAL), T.text2)
        for i, (k, v) in enumerate(self.RULES):
            y = 74 + i * 30
            k_ = self.local(i, len(self.RULES), .6)
            p.setOpacity(k_)
            text(p, QRectF(24, y, self.width() - 140, 26), tr(k), F(13, W_NORMAL), T.text)
            v = v.replace("min", tr("u.min")) if i == 0 else v
            text(p, QRectF(self.width() - 130, y, 106, 26), v, F(13, W_SEMI), T.text2, "r")
            p.setOpacity(1)
            if i < len(self.RULES) - 1:
                p.setPen(QPen(T.hair, 1))
                p.drawLine(QPointF(24, y + 28), QPointF(self.width() - 24, y + 28))
        wrap_text(p, QRectF(24, 74 + len(self.RULES) * 30 + 8, self.width() - 48, 44), tr("rule.note"),
                  F(12, W_NORMAL), T.text3)



# ───────────────────────────── settings controls ─────────────────────────────
class Toggle(QWidget):
    toggled = Signal(bool)
    t = fprop("t")
    press = fprop("press")

    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.value = bool(value)
        self._p_t = 1.0 if value else 0.0
        self.setFixedSize(54, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        self.value = not self.value
        A(self, "t", 1.0 if self.value else 0.0, 380, BACK)
        A(self, "press", 1, 90)
        self.toggled.emit(self.value)

    def mouseReleaseEvent(self, e):
        A(self, "press", 0, 260)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        t = clamp(self.t)
        p.setPen(NOPEN)
        p.setBrush(mix(T.track, T.primary, t))
        p.drawRoundedRect(QRectF(self.rect()), 16, 16)
        kw = 26 + 6 * self.press
        x = lerp(3, 51 - kw, self.t)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawRoundedRect(QRectF(x, 5, kw, 26), 13, 13)
        p.setBrush(mix(QColor("#FFFFFF"), T.on_primary, t))
        p.drawRoundedRect(QRectF(x, 3, kw, 26), 13, 13)


class Stepper(QWidget):
    changed = Signal(int)
    bump = fprop("bump", 1.0)

    def __init__(self, value, lo, hi, step, unit="", parent=None):
        super().__init__(parent)
        self.value, self.lo, self.hi, self.step, self.unit = value, lo, hi, step, unit
        self.setFixedSize(138, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rep = QTimer(self)
        self._rep.setInterval(85)
        self._rep.timeout.connect(self._repeat)
        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.setInterval(380)
        self._hold.timeout.connect(self._rep.start)
        self._dir, self._n = 0, 0
        self.edit = QLineEdit(self)
        self.edit.setValidator(QIntValidator(lo, hi, self))
        self.edit.setGeometry(40, 3, self.width() - 80, 28)
        self.edit.returnPressed.connect(self._commit)
        self.edit.installEventFilter(self)
        self.edit.hide()
        self.restyle()

    def restyle(self):
        style_edit(self.edit, 14, W_MED, center=True)

    def eventFilter(self, o, e):
        if o is self.edit and self.edit.isVisible():
            if e.type() == QEvent.Type.FocusOut:
                self._commit()
            elif e.type() == QEvent.Type.KeyPress and e.key() == Qt.Key.Key_Escape:
                self.edit.hide()
                self.update()
                return True
        return False

    def _begin_edit(self):
        self.edit.setText(str(self.value))
        self.edit.show()
        self.edit.setFocus()
        self.edit.selectAll()
        self.update()

    def _commit(self):
        if not self.edit.isVisible():
            return
        t = self.edit.text().strip()
        self.edit.hide()
        if t.lstrip("-").isdigit():
            self.set_value(int(clamp(int(t), self.lo, self.hi)))
        self.update()

    def set_value(self, v):
        v = int(clamp(v, self.lo, self.hi))
        if v != self.value:
            self.value = v
            A(self, "bump", 1, 300, OUT, start=0)
            self.changed.emit(v)

    def _apply(self, d, mult=1):
        self.set_value(self.value + d * self.step * mult)

    def _repeat(self):
        self._n += 1
        self._apply(self._dir, 1 if self._n < 10 else 5 if self._n < 25 else 10)

    def mousePressEvent(self, e):
        x = e.position().x()
        self._dir = -1 if x < 40 else 1 if x > self.width() - 40 else 0
        self._n = 0
        if self._dir:
            self._apply(self._dir)
            self._hold.start()
        elif not self.edit.isVisible():
            self._begin_edit()

    def mouseReleaseEvent(self, e):
        self._hold.stop()
        self._rep.stop()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        if not self.isEnabled():
            p.setOpacity(.35)
        p.setPen(NOPEN)
        p.setBrush(T.body)
        p.drawRoundedRect(QRectF(self.rect()), 17, 17)
        for ic, x, ok in (("minus", 19, self.value > self.lo), ("plus", self.width() - 19, self.value < self.hi)):
            draw_icon(p, ic, x, 17, 14, alpha(T.text, 1.0 if ok else .25), w=1.8)
        if self.edit.isVisible():
            return
        b = ease_out(self.bump)
        s = 1.0 + 0.14 * (1 - b)
        p.translate(self.width() / 2, 17)
        p.scale(s, s)
        p.translate(-self.width() / 2, -17)
        label = tr('off') if self.value == 0 and self.lo == 0 else f"{self.value}{(' ' + tr(self.unit)) if self.unit else ''}"
        text(p, QRectF(30, 0, self.width() - 60, 34), label, F(14, W_MED), T.text, "c", False)


class Segmented(QWidget):
    changed = Signal(str)
    sel = fprop("sel")

    def __init__(self, options, current, width=196, parent=None):
        super().__init__(parent)
        self.options = options
        self.cur = next((i for i, o in enumerate(options) if o[0] == current), 0)
        self._p_sel = float(self.cur)
        self.setFixedSize(width, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        i = int(e.position().x() // (self.width() / len(self.options)))
        if i != self.cur:
            self.cur = i
            A(self, "sel", i, 420, QEasingCurve.Type.OutQuint)
            self.changed.emit(self.options[i][0])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        n = len(self.options)
        w = self.width() / n
        p.setPen(NOPEN)
        p.setBrush(T.body)
        p.drawRoundedRect(QRectF(self.rect()), 17, 17)
        p.setBrush(T.thumb)
        p.drawRoundedRect(QRectF(3 + self.sel * w, 3, w - 6, 28), 14, 14)
        for i, (k, lab) in enumerate(self.options):
            text(p, QRectF(i * w, 0, w, 34), tr(lab), F(13, W_MED), mix(T.text2, T.text, 1 - abs(self.sel - i)), "c")


class Swatches(QWidget):
    changed = Signal(str)
    sel = fprop("sel")

    def __init__(self, current, parent=None):
        super().__init__(parent)
        self.keys = list(Theme.ACCENTS)
        self.cur = self.keys.index(current) if current in self.keys else 0
        self._p_sel = float(self.cur)
        self.setFixedSize(len(self.keys) * 34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        i = int(e.position().x() // 34)
        if 0 <= i < len(self.keys) and i != self.cur:
            self.cur = i
            A(self, "sel", i, 420, QEasingCurve.Type.OutQuint)
            self.changed.emit(self.keys[i])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        for i, k in enumerate(self.keys):
            hx = Theme.ACCENTS[k][1]
            c = QPointF(17 + i * 34, 17)
            if hx is None:
                g = QLinearGradient(c.x() - 10, c.y() - 10, c.x() + 10, c.y() + 10)
                g.setColorAt(0, QColor("#1C1C1E"))
                g.setColorAt(1, QColor("#9A9AA0"))
                p.setBrush(g)
            else:
                p.setBrush(QColor(hx))
            p.setPen(NOPEN)
            p.drawEllipse(c, 10, 10)
        p.setBrush(NOBRUSH)
        p.setPen(QPen(T.text, 1.8))
        p.drawEllipse(QPointF(17 + self.sel * 34, 17), 14, 14)


class Row(QWidget):
    def __init__(self, label, sub=None, control=None, last=False, parent=None):
        super().__init__(parent)
        self.label, self.sub, self.last, self.control = label, sub, last, control
        self.setFixedHeight(64 if sub else 56)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.addStretch(1)
        if control:
            lay.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        mw = self.width() - 44 - (self.control.width() if self.control else 0)
        if self.sub:
            text(p, QRectF(20, 11, mw, 22), tr(self.label), F(15, W_MED), T.text)
            text(p, QRectF(20, 33, mw, 18), tr(self.sub), F(12, W_NORMAL), T.text2)
        else:
            text(p, QRectF(20, 0, mw, self.height()), tr(self.label), F(15, W_MED), T.text)
        if not self.last:
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(20, self.height() - 1), QPointF(self.width(), self.height() - 1))


class DangerRow(Hoverable):
    def __init__(self, label, action, last=False, parent=None):
        super().__init__(parent)
        self.label, self.action, self.last, self.armed = label, action, last, False
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        if self.armed:
            self.armed = False
            self.action()
        else:
            self.armed = True
            QTimer.singleShot(3000, self._disarm)
        self.update()

    def _disarm(self):
        self.armed = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        s = tr("s.confirm") if self.armed else tr(self.label)
        text(p, QRectF(20, 0, self.width() - 40, 54), s, F(15, W_MED), alpha(DANGER, .75 + .25 * self.hover))
        if not self.last:
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(20, 53), QPointF(self.width(), 53))


class CatRow(Hoverable):
    removed = Signal(str)

    def __init__(self, cat, last=False, parent=None):
        super().__init__(parent)
        self.cat, self.last = cat, last
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor if cat["id"] != "other" else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, e):
        if self.cat["id"] != "other" and e.position().x() > self.width() - 56:
            self.removed.emit(self.cat["id"])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.setPen(NOPEN)
        p.setBrush(QColor(self.cat["color"]))
        p.drawEllipse(QPointF(30, 25), 6, 6)
        text(p, QRectF(48, 0, self.width() - 110, 50), cat_name(self.cat), F(15, W_MED), T.text)
        if self.cat["id"] != "other":
            draw_icon(p, "close", self.width() - 30, 25, 13, alpha(T.text3, .5 + .5 * self.hover), w=1.6)
        if not self.last:
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(20, 49), QPointF(self.width(), 49))


class AddCatRow(QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setFixedHeight(54)
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(tr("s.newcat"))
        self.edit.setMaxLength(20)
        self.edit.returnPressed.connect(self.add)
        self.btn = RoundButton("plus", 34, "ghost", self)
        self.btn.clicked.connect(self.add)
        self.restyle()

    def restyle(self):
        style_edit(self.edit, 15, W_MED)

    def resizeEvent(self, e):
        self.edit.setGeometry(48, 0, self.width() - 110, 54)
        self.btn.move(self.width() - 50, 10)

    def add(self):
        s = self.edit.text().strip()
        if s:
            self.store.add_category(s, CAT_COLORS[len(self.store.d["categories"]) % len(CAT_COLORS)])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.setPen(QPen(T.text3, 1.6, Qt.PenStyle.DashLine))
        p.setBrush(NOBRUSH)
        p.drawEllipse(QPointF(30, 27), 6, 6)


class GroupCard(QWidget):
    def __init__(self, rows=(), parent=None):
        super().__init__(parent)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.set_rows(rows)

    def set_rows(self, rows):
        while self.lay.count():
            it = self.lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for r in rows:
            self.lay.addWidget(r)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.setPen(QPen(T.hair, 1))
        p.setBrush(T.card)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 22, 22)


class ActionRow(Hoverable):
    def __init__(self, label, action, icon=None, last=False, parent=None):
        super().__init__(parent)
        self.label, self.action, self.icon, self.last = label, action, icon, last
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        self.action()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        text(p, QRectF(20, 0, self.width() - 70, 54), tr(self.label), F(15, W_MED), mix(T.text, T.accent, .0 + .5 * self.hover))
        if self.icon:
            draw_icon(p, self.icon, self.width() - 32, 27, 16, T.text2, w=1.7)
        if not self.last:
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(20, 53), QPointF(self.width(), 53))


class SupportRow(Hoverable):
    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.setFixedHeight(78)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        self.action()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.setPen(NOPEN)
        p.setBrush(alpha(QColor("#FF6B57"), .14 + .08 * self.hover))
        p.drawEllipse(QPointF(46, 39), 22, 22)
        draw_icon(p, "heart", 46, 40, 24, QColor("#FF6B57"))
        text(p, QRectF(84, 16, self.width() - 140, 24), tr("s.support_open"), F(15, W_MED), T.text)
        text(p, QRectF(84, 40, self.width() - 140, 20), tr("s.support_sub"), F(12, W_NORMAL), T.text2)
        draw_icon(p, "chevron", self.width() - 30 + 3 * self.hover, 39, 14, T.text3, w=1.8)


class ChoiceRow(QWidget):
    """Подпись + прокручиваемые чипы (звуки, язык)."""
    def __init__(self, label, items, current, on_pick, last=False):
        super().__init__()
        self.label, self.last = label, last
        self.setFixedHeight(104)
        self.chips = ChipBar(self, bg="body", pad=20)
        self.chips.set_items(items, current)
        self.chips.selected.connect(on_pick)

    def resizeEvent(self, e):
        self.chips.setGeometry(0, 52, self.width(), 36)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        text(p, QRectF(20, 8, self.width() - 40, 36), tr(self.label), F(15, W_MED), T.text)
        if not self.last:
            p.setPen(QPen(T.hair, 1))
            p.drawLine(QPointF(20, self.height() - 1), QPointF(self.width(), self.height() - 1))


class SettingsPage(SmoothScroll):
    def __init__(self, store, engine):
        super().__init__()
        self.store = store
        self.toast = lambda s: None
        self.open_support = lambda: None
        self.build()
        store.changed.connect(self.on_changed)

    def on_changed(self, topic):
        if topic in ("all", "lang"):
            QTimer.singleShot(0, self.rebuild)
        elif topic == "categories":
            self.fill_cats()

    def rebuild(self):
        v = self.verticalScrollBar().value()
        self.build()
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(v))

    def sec(self, key):
        return Label("  " + tr(key), 11, W_MED, "text3", spacing=1.5)

    def stepper(self, label, key, lo, hi, step, unit, last=False):
        st = Stepper(self.store.s(key), lo, hi, step, unit)
        st.changed.connect(lambda v: self.store.set_setting(key, v))
        return Row(label, None, st, last)

    def toggle(self, label, key, sub=None, last=False):
        tg = Toggle(self.store.s(key))
        tg.toggled.connect(lambda v: self.store.set_setting(key, v))
        return Row(label, sub, tg, last)

    def segmented(self, label, key, options, width, last=False):
        sg = Segmented(options, self.store.s(key), width)
        sg.changed.connect(lambda v: self.store.set_setting(key, v))
        return Row(label, None, sg, last)

    def sound_row(self, label, key, last=False):
        def pick(sid):
            self.store.set_setting(key, sid)
            play_sound(sid, self.store.s("volume"))
        return ChoiceRow(label, [(s, "snd." + s) for s in SOUND_IDS], self.store.s(key), pick, last)

    def export(self):
        p, _ = QFileDialog.getSaveFileName(self, tr("s.export"), "graphite_time_backup.json", "JSON (*.json)")
        if p:
            self.store.export(p)
            self.toast(tr("s.exported", p=Path(p).name))

    def build(self):
        s = self.store
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(20, 8, 20, 110)
        lay.setSpacing(8)
        lay.addWidget(self.sec("st.timer"))
        lay.addWidget(GroupCard([
            self.stepper("s.focus", "focus", 1, 480, 1, "u.min"), self.toggle("ts.breaks", "breaks", "ts.breaks_sub"),
            self.stepper("s.short", "short", 1, 120, 1, "u.min"), self.stepper("s.long", "long", 1, 180, 1, "u.min"),
            self.stepper("s.cycles", "cycles", 0, 12, 1, ""), self.toggle("ts.flow", "free_focus", "ts.flow_sub"),
            self.stepper("s.flow_ratio", "flow_ratio", 2, 10, 1, ""),
            self.stepper("s.min_session", "min_session", 1, 30, 1, "u.min"),
            self.toggle("s.confirm_finish", "confirm_finish"),
            self.stepper("s.goal", "goal", 15, 1440, 15, "u.min"),
            self.segmented("s.week_start", "week_start", [("mon", "s.mon"), ("sun", "s.sun")], 150, True)]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.behavior"))
        rows = [self.toggle("s.auto_break", "auto_break"), self.toggle("s.auto_focus", "auto_focus"),
                self.toggle("s.end_warn", "end_warn"), self.toggle("s.notify", "notify"),
                self.toggle("s.title_time", "title_time"), self.toggle("s.on_top", "on_top"),
                self.toggle("s.popup_end", "popup_end", None, sys.platform != "win32")]
        if sys.platform == "win32":
            rows.append(self.toggle("s.autostart", "autostart", None, True))
        lay.addWidget(GroupCard(rows))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.mini"))
        lay.addWidget(GroupCard([self.toggle("s.mini_min", "mini_min"), self.toggle("s.mini_snap", "mini_snap"),
                                 self.stepper("s.mini_opacity", "mini_opacity", 30, 100, 5, "%", True)]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.sounds"))
        lay.addWidget(GroupCard([self.toggle("s.sound", "sound"), self.stepper("s.volume", "volume", 10, 100, 10, "%"),
                                 self.sound_row("snd.focus_end", "sound_focus"),
                                 self.sound_row("snd.break_end", "sound_break", True)]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.appearance"))
        sw = Swatches(s.s("accent"))
        sw.changed.connect(lambda v: s.set_setting("accent", v))
        lay.addWidget(GroupCard([
            self.segmented("s.theme", "theme", [("light", "s.light"), ("dark", "s.dark"), ("auto", "s.auto")], 236),
            Row("s.accent", None, sw), self.toggle("s.ticks", "ticks"),
            self.stepper("s.opacity", "opacity", 60, 100, 5, "%"),
            self.toggle("s.animations", "animations", "s.sub_anim", True)]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.language"))
        lay.addWidget(GroupCard([ChoiceRow("s.language", [(c, LANG_NAMES[c]) for c in LANGS], s.s("lang"),
                                           lambda c: s.set_setting("lang", c), True)]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.categories"))
        self.cats = GroupCard()
        lay.addWidget(self.cats)
        self.fill_cats()
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.support"))
        lay.addWidget(GroupCard([SupportRow(lambda: self.open_support())]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.data"))
        lay.addWidget(GroupCard([ActionRow("s.export", self.export, "download"),
                                 DangerRow("s.reset_stats", s.reset_stats), DangerRow("s.reset_all", s.reset_all, True)]))
        lay.addSpacing(10)
        lay.addWidget(self.sec("st.about"))
        lay.addWidget(CreatorCard())
        lay.addSpacing(4)
        lay.addWidget(Label(f"{APP_NAME}  ·  v{APP_VERSION}", 12, W_NORMAL, "text3", "c"))
        lay.addStretch(1)
        self.setWidget(body)
        for w in self.findChildren(QWidget):
            if hasattr(w, "restyle"):
                w.restyle()

    def fill_cats(self):
        rows = []
        for c in self.store.d["categories"]:
            r = CatRow(c)
            r.removed.connect(self.store.remove_category)
            rows.append(r)
        rows.append(AddCatRow(self.store))
        self.cats.set_rows(rows)
        for w in self.cats.findChildren(QWidget):
            if hasattr(w, "restyle"):
                w.restyle()

    def restyle(self):
        pass


# ───────────────────────────── support (crypto) & creator ─────────────────────────────
def draw_qr(p, rect, rows, color):
    """Классический QR: квадратные «глазки» (надёжно сканируются), модули чуть скруглены."""
    n = len(rows)
    m = rect.width() / n
    p.save()
    p.translate(rect.topLeft())
    p.setPen(NOPEN)
    p.setBrush(color)

    def in_finder(r, c):
        return (r < 7 and c < 7) or (r < 7 and c >= n - 7) or (r >= n - 7 and c < 7)
    for r in range(n):
        for c in range(n):
            if rows[r][c] == "1" and not in_finder(r, c):
                p.drawRoundedRect(QRectF(c * m, r * m, m, m), m * RQ, m * RQ)
    for (r, c) in ((0, 0), (0, n - 7), (n - 7, 0)):
        x, y = c * m, r * m
        p.drawRect(QRectF(x, y, 7 * m, 7 * m))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRect(QRectF(x + m, y + m, 5 * m, 5 * m))
        p.setBrush(color)
        p.drawRect(QRectF(x + 2 * m, y + 2 * m, 3 * m, 3 * m))
    p.restore()


RQ = 0.22


class CopyButton(Hoverable):
    clicked = Signal()
    done = fprop("done")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def flash(self):
        A(self, "done", 1.0, 260, OUT)
        QTimer.singleShot(1900, lambda: A(self, "done", 0.0, 350, OUT))

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        p.setPen(NOPEN)
        p.setBrush(mix(mix(T.primary, T.text, .12 * self.hover), BREAK, self.done))
        p.drawRoundedRect(r, 24, 24)
        d = self.done
        fnt = F(14, W_MED)
        label_a, label_b = tr("sp.copy"), tr("sp.copied")
        col = T.on_primary if T.accent_key != "graphite" or not T.dark else T.on_primary
        col = QColor("#FFFFFF") if d > .5 else col
        s = label_b if d > .5 else label_a
        wd = QFontMetricsF(fnt).horizontalAdvance(s)
        cx = r.center().x() + 14
        icon = "check" if d > .5 else "copy"
        draw_icon(p, icon, cx - wd / 2 - 14, r.center().y(), 17, col, w=1.8)
        text(p, QRectF(cx - wd / 2, r.top(), wd + 4, r.height()), s, fnt, col, "l", False)


class CryptoCard(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 506, parent)
        self.btn = CopyButton(self)
        self.btn.clicked.connect(self.copy)
        self.setMouseTracking(True)

    def copy(self):
        QApplication.clipboard().setText(DONATE_ADDRESS)
        self.btn.flash()

    def resizeEvent(self, e):
        self.btn.setGeometry(24, 372, self.width() - 48, 48)

    def mousePressEvent(self, e):
        if QRectF(24, 296, self.width() - 48, 56).contains(e.position()):
            self.copy()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        w, t = self.width(), ease_out(self.t)
        # network chip
        label = "USDT  ·  TRC20"
        f = F(12, W_SEMI, 0.6)
        cw = QFontMetricsF(f).horizontalAdvance(label) + 40
        chip = QRectF((w - cw) / 2, 18, cw, 28)
        p.setPen(NOPEN)
        p.setBrush(alpha(BREAK, .16))
        p.drawRoundedRect(chip, 14, 14)
        p.setBrush(BREAK)
        p.drawEllipse(QPointF(chip.left() + 15, chip.center().y()), 3.5, 3.5)
        text(p, QRectF(chip.left() + 26, chip.top(), cw - 30, 28), label, f, mix(T.text, BREAK, .55), "l", False)
        # QR on white plate
        plate = QRectF((w - 224) / 2, 60 + (1 - t) * 10, 224, 224)
        p.setOpacity(t)
        p.setPen(QPen(T.hair, 1))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(plate, 24, 24)
        draw_qr(p, plate.adjusted(24, 24, -24, -24), QR_ROWS, QColor("#16161A"))
        p.setOpacity(1)
        text(p, QRectF(0, 292, w, 18), tr("sp.scan"), F(12, W_NORMAL), T.text3, "c")
        # address (two lines, monospace)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPixelSize(14)
        mono.setWeight(W_MED)
        a1, a2 = DONATE_ADDRESS[:17], DONATE_ADDRESS[17:]
        text(p, QRectF(0, 316, w, 22), a1, mono, T.text, "c", False)
        text(p, QRectF(0, 338, w, 22), a2, mono, T.text, "c", False)
        wrap_text(p, QRectF(30, 436, w - 60, 60), tr("sp.warn"), F(12, W_NORMAL), T.text3, Qt.AlignmentFlag.AlignHCenter)


class CreatorCard(Hoverable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(88)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            QDesktopServices.openUrl(QUrl(GITHUB_URL))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        h = self.hover
        r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        p.setPen(QPen(mix(T.hair, alpha(T.accent, .55), h), 1.2))
        p.setBrush(mix(T.card, T.body, .5 * h))
        p.drawRoundedRect(r, 24, 24)
        c = QPointF(48, r.center().y())
        if T.accent_key == "graphite":
            c1, c2 = (QColor("#5C5C66"), QColor("#2A2A2E")) if T.dark else (QColor("#4A4A52"), QColor("#111113"))
        else:
            c1, c2 = T.accent.lighter(118), T.accent.darker(140)
        g = QLinearGradient(c.x() - 26, c.y() - 26, c.x() + 26, c.y() + 26)
        g.setColorAt(0, c1)
        g.setColorAt(1, c2)
        p.setPen(NOPEN)
        p.setBrush(alpha(T.accent, .10 * h))
        p.drawEllipse(c, 31, 31)
        p.setBrush(g)
        p.drawEllipse(c, 26, 26)
        text(p, QRectF(c.x() - 26, c.y() - 26, 52, 52), AUTHOR[:1].upper(), F(26, W_LIGHT), QColor("#FFFFFF"), "c")
        x = 90
        text(p, QRectF(x, 15, self.width() - x - 56, 16), tr("cr.role").upper(), F(10, W_MED, 1.6), T.text3)
        text(p, QRectF(x, 31, self.width() - x - 56, 28), AUTHOR, F(20, W_SEMI), T.text)
        text(p, QRectF(x, 58, self.width() - x - 56, 18), GITHUB_URL.replace("https://", ""), F(12, W_NORMAL), T.text2)
        draw_icon(p, "ext", self.width() - 32 + 2 * h, r.center().y() - 2 * h, 17, mix(T.text3, T.text, h), w=1.8)


class SupportHero(Card):
    def __init__(self, store, parent=None):
        super().__init__(store, 204, parent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        self.bg(p)
        w, t = self.width(), ease_out(self.t)
        coral = QColor("#FF6B57")
        p.setPen(NOPEN)
        p.setBrush(alpha(coral, .13))
        p.drawEllipse(QPointF(w / 2, 52), 31 * (0.85 + 0.15 * t), 31 * (0.85 + 0.15 * t))
        draw_icon(p, "heart", w / 2, 53, 30 * (0.7 + 0.3 * ease_back(self.t)), coral)
        text(p, QRectF(0, 96, w, 30), tr("sp.title"), F(21, W_SEMI), T.text, "c")
        wrap_text(p, QRectF(28, 134, w - 56, 66), tr("sp.text"), F(13, W_NORMAL), T.text2, Qt.AlignmentFlag.AlignHCenter)


class SupportPage(QWidget):
    def __init__(self, store, parent):
        super().__init__(parent)
        self.store, self._eff, self._y0, self._slide = store, None, 116, 0.0
        self.hide()
        self.back = RoundButton("back", 38, "ghost", self)
        self.back.move(16, 8)
        self.back.clicked.connect(self.close_page)
        self.scroll = SmoothScroll(self)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(20, 6, 20, 120)
        lay.setSpacing(14)
        self.hero, self.crypto = SupportHero(store), CryptoCard(store)
        lay.addWidget(self.hero)
        lay.addWidget(self.crypto)
        lay.addWidget(CreatorCard())
        lay.addStretch(1)
        self.scroll.setWidget(body)

    def resizeEvent(self, e):
        self.scroll.setGeometry(0, 54, self.width(), self.height() - 54)

    def _gs(self):
        return self._slide

    def _ss(self, v):
        self._slide = v
        self.move(0, self._y0 + int((1 - v) * 44))
        if self._eff is not None:
            self._eff.setOpacity(clamp(v))
    slide = Property(float, _gs, _ss)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        p.fillPath(rr_path(QRectF(self.rect()), 0, 0, RADIUS, RADIUS), T.body)
        text(p, QRectF(0, 8, self.width(), 38), tr("st.support"), F(15, W_SEMI), T.text, "c")

    def open_page(self):
        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._ss(0.0)
        self.show()
        self.raise_()
        self.scroll.verticalScrollBar().setValue(0)
        A(self, "slide", 1.0, 420, QEasingCurve.Type.OutQuint, start=0, finished=self._open_done)
        self.hero.play()
        self.crypto.play()

    def _open_done(self):
        self.setGraphicsEffect(None)
        self._eff = None

    def close_page(self):
        if not self.isVisible():
            return
        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        A(self, "slide", 0.0, 260, IN, finished=self._close_done)

    def _close_done(self):
        self.hide()
        self.setGraphicsEffect(None)
        self._eff = None


# ───────────────────────────── mini mode ─────────────────────────────
class MiniWindow(QWidget):
    """Плавающая мини-панель. Магнитится к верху/низу рабочей области (не заходит под панель задач),
    в прилипшем виде перестраивается в компактную «вкладку», где всё видно целиком."""
    expand = Signal()
    CW, M, PHF, PHD = 330, 16, 72, 46

    def _gcf(self):
        return getattr(self, "_p_cf", 0.0)

    def _scf(self, v):
        self._p_cf = v
        self._sync_vis()
        self.update()
    cf = Property(float, _gcf, _scf)

    def __init__(self, store, engine):
        super().__init__()
        self.store, self.engine = store, engine
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._edge = self._draw_edge = ""
        self._press = self._drag_on = None
        self._flash, self._show_fin = "", False
        self._ga = QPropertyAnimation(self, b"geometry", self)
        self._ga.finished.connect(self._anim_done)
        self.exp = RoundButton("expand", 34, "ghost", self)
        self.play = RoundButton("playpause", 44, "primary", self)
        self.fin = RoundButton("check", 34, "ghost", self)
        self.play.clicked.connect(engine.toggle)
        self.exp.clicked.connect(self.expand)
        self.fin.clicked.connect(self.on_fin)
        self.resize(self.CW + 2 * self.M, self.PHF + 2 * self.M)
        engine.tick.connect(self.update)
        engine.state.connect(self.on_state)
        engine.finished_early.connect(self.on_early)
        store.changed.connect(self.on_store)
        for sc in QApplication.screens():
            sc.availableGeometryChanged.connect(lambda *_: self.reposition())
        self.on_state()

    # --- геометрия ---
    def _s(self):
        return clamp((self.PHF + 2 * self.M - self.height()) / float(self.PHF - self.PHD + self.M))

    def _panel(self):
        s, M, h = self._s(), self.M, self.height()
        ph = lerp(self.PHF, self.PHD, s)
        if self._draw_edge == "bottom":
            top = h - ph - (1 - s) * M
        elif self._draw_edge == "top":
            top = (1 - s) * M
        else:
            top = M
        return QRectF(M, top, self.CW, ph)

    def _target(self, px, py, edge, wa):
        M = self.M
        if edge == "top":
            return QRect(int(px) - M, wa.top(), self.CW + 2 * M, self.PHD + M)
        if edge == "bottom":
            h = self.PHD + M
            return QRect(int(px) - M, wa.bottom() + 1 - h, self.CW + 2 * M, h)
        return QRect(int(px) - M, int(py) - M, self.CW + 2 * M, self.PHF + 2 * M)

    def _go(self, target, edge):
        if edge != self._edge:
            self._edge = edge
            if edge:
                self._draw_edge = edge
            self._layout()
            if not _ANIM:
                self._draw_edge = edge
                self.setGeometry(target)
                self._layout()
                return
            self._ga.stop()
            self._ga.setDuration(dur(320))
            self._ga.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._ga.setStartValue(self.geometry())
            self._ga.setEndValue(target)
            self._ga.start()
        elif self._ga.state() == QAbstractAnimation.State.Running:
            self._ga.setEndValue(target)
        else:
            self.setGeometry(target)

    def _anim_done(self):
        if not self._edge:
            self._draw_edge = ""
        self._layout()
        self.update()

    def _screen_wa(self, pt=None):
        scr = (QApplication.screenAt(pt) if pt is not None else None) or self.screen() or QApplication.primaryScreen()
        return scr.availableGeometry()

    def _saved(self):
        s = self.store
        return s.s("mini_dock"), s.s("mini_x"), s.s("mini_y")

    def _apply_saved(self):
        dock, x, y = self._saved()
        scr = QApplication.screenAt(QPoint(x + self.CW // 2, y + 20)) if x >= 0 else None
        if scr is None:
            wa = QApplication.primaryScreen().availableGeometry()
            x, y, dock = wa.right() + 1 - self.CW - 14, wa.bottom() + 1 - self.PHF - 14, ""
        else:
            wa = scr.availableGeometry()
        x = int(clamp(x, wa.left(), max(wa.left(), wa.right() + 1 - self.CW)))
        y = int(clamp(y, wa.top(), max(wa.top(), wa.bottom() + 1 - self.PHF)))
        edge = dock if (dock in ("top", "bottom") and self.store.s("mini_snap")) else ""
        self._ga.stop()
        self._edge = self._draw_edge = edge
        self.setGeometry(self._target(x, y, edge, wa))

    def reposition(self):
        if self.isVisible() and self._drag_on is None:
            self._apply_saved()

    def popup(self):
        self._apply_saved()
        self.on_state()
        self.show()
        self.raise_()
        self.setWindowOpacity(0.0)
        A(self, "windowOpacity", self._idle(), 260, OUT, start=0)

    def _idle(self):
        return clamp(self.store.s("mini_opacity") / 100.0, .3, 1.0)

    # --- состояние ---
    def on_store(self, topic):
        if topic in ("settings", "lang", "all"):
            self.on_state()
            if self.isVisible() and not self.underMouse():
                self.setWindowOpacity(self._idle())

    def on_state(self):
        e = self.engine
        self.play.set_morph(1.0 if e.running else 0.0)
        self._show_fin = (e.mode == "focus" and e.started) or e.mode != "focus"
        self.fin.icon = "check" if e.mode == "focus" else "skip"
        self.fin.setToolTip(tr("tip.finish") if e.mode == "focus" else tr("tip.skip"))
        self.exp.setToolTip(tr("tip.expand"))
        if self.cf > 0 and not (e.mode == "focus" and e.started):
            self.set_confirm(False)
        self._sync_vis()
        self._layout()
        self.update()

    def _sync_vis(self):
        on = self.cf < 0.5
        self.exp.setVisible(on)
        self.play.setVisible(on)
        self.fin.setVisible(on and self._show_fin)

    def _layout(self):
        s, r = self._s(), self._panel()
        cy = r.center().y()
        bs, ps = int(lerp(34, 26, s)), int(lerp(44, 30, s))
        gap, padr = lerp(8, 6, s), lerp(14, 10, s)
        xe = r.right() - padr - bs
        xp = xe - gap - ps
        xf = xp - gap - bs
        for w, x, sz in ((self.exp, xe, bs), (self.play, xp, ps), (self.fin, xf, bs)):
            w.setFixedSize(sz, sz)
            w.move(int(x), int(cy - sz / 2))

    def resizeEvent(self, e):
        self._layout()

    def enterEvent(self, e):
        A(self, "windowOpacity", 1.0, 160, OUT)

    def leaveEvent(self, e):
        if self._drag_on is None:
            A(self, "windowOpacity", self._idle(), 380, OUT)

    # --- завершение ---
    def on_fin(self):
        e, s = self.engine, self.store
        if e.mode != "focus":
            e.skip()
            return
        t = s.task(s.d.get("current_task"))
        if t and not t["done"] and s.s("confirm_finish"):
            self.set_confirm(True)
        else:
            e.finish_early(False)

    def set_confirm(self, on):
        A(self, "cf", 1.0 if on else 0.0, 260, OUT)

    def on_early(self, mins, gain, closed):
        self.set_confirm(False)
        if mins < 1 and not closed:
            self._flash = tr("fin.too_short")
        else:
            self._flash = tr("mini.saved", m=fmt_minutes(mins), p=int(round(gain)))
        QTimer.singleShot(2800, self._clear_flash)
        self.update()

    def _clear_flash(self):
        self._flash = ""
        self.update()

    def _crects(self):
        r = self._panel()
        h = min(34.0, r.height() - 14)
        for px in (13, 12, 11):
            f = F(px, W_MED)
            fm = QFontMetricsF(f)
            w1 = fm.horizontalAdvance(tr("mini.task_done")) + 44
            w2 = fm.horizontalAdvance(tr("mini.only")) + 28
            if w1 + w2 + 30 + 16 <= r.width() - 28:
                break
        y = r.center().y() - h / 2
        x = r.left() + 14
        a = QRectF(x, y, w1, h)
        b = QRectF(a.right() + 8, y, w2, h)
        c = QRectF(b.right() + 8, y, 30, h)
        return f, h, a, b, c

    # --- мышь / перетаскивание ---
    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.cf > 0.5:
            f, h, a, b, c = self._crects()
            pos = e.position()
            if a.contains(pos):
                self.engine.finish_early(True)
            elif b.contains(pos):
                self.engine.finish_early(False)
            elif c.contains(pos) or not self._panel().contains(pos):
                self.set_confirm(False)
            return
        gp = e.globalPosition().toPoint()
        r = self._panel()
        self._press = gp
        self._gx, self._gy = gp.x() - (self.x() + r.left()), gp.y() - (self.y() + r.top())
        self._drag_on = None

    def mouseMoveEvent(self, e):
        if self._press is None:
            return
        gp = e.globalPosition().toPoint()
        if self._drag_on is None:
            if (gp - self._press).manhattanLength() < 5:
                return
            self._drag_on = True
        self._drag(gp)

    def _drag(self, gp):
        s, M, CW = self.store, self.M, self.CW
        wa = self._screen_wa(gp)
        px = gp.x() - self._gx
        py = gp.y() - self._gy
        px = clamp(px, wa.left(), max(wa.left(), wa.right() + 1 - CW))
        py = clamp(py, wa.top(), max(wa.top(), wa.bottom() + 1 - self.PHF))
        edge = self._edge
        if s.s("mini_snap"):
            cx = wa.center().x() + 0.5 - CW / 2
            if abs(px - cx) < 26:
                px = cx
            elif abs(px - (wa.left() + 10)) < 16:
                px = wa.left() + 10
            elif abs(px - (wa.right() + 1 - CW - 10)) < 16:
                px = wa.right() + 1 - CW - 10
            tg, bg = py - wa.top(), wa.bottom() + 1 - (py + self.PHF)
            if not ((edge == "top" and tg <= 64) or (edge == "bottom" and bg <= 64)):
                edge = "top" if tg <= 34 else "bottom" if bg <= 34 else ""
        else:
            edge = ""
        self._go(self._target(px, py, edge, wa), edge)

    def mouseReleaseEvent(self, e):
        if self._drag_on:
            r = self._panel_target()
            s = self.store.d["settings"]
            s["mini_dock"], s["mini_x"], s["mini_y"] = self._edge, r[0], r[1]
            self.store.touch("mini")
        self._press = self._drag_on = None

    def _panel_target(self):
        g = self._ga.endValue() if self._ga.state() == QAbstractAnimation.State.Running else self.geometry()
        x = g.x() + self.M
        if self._edge:
            return x, g.y() if self._edge == "top" else g.y() + g.height() - self.PHF
        return x, g.y() + self.M

    def mouseDoubleClickEvent(self, e):
        if self.cf < 0.5:
            self.expand.emit()

    # --- рисование ---
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        M, e_ = self.M, self.engine
        s, r, edge = self._s(), self._panel(), self._draw_edge
        ro, rf = lerp(36, r.height() / 2, s), lerp(36, 0, s)
        tl, tr_, br, bl = ((rf, rf, ro, ro) if edge == "top" else (ro, ro, rf, rf) if edge == "bottom" else (ro,) * 4)
        off = 5 if not edge else (3 if edge == "top" else -3)
        p.setPen(NOPEN)
        for i in range(M):
            p.setBrush(QColor(0, 0, 0, int(255 * 0.04 * (1 - i / M) ** 2.2)))
            p.drawPath(rr_path(r.adjusted(-i, -i + off, i, i + off), *(0 if v == 0 else v + i for v in (tl, tr_, br, bl))))
        path = rr_path(r.adjusted(.5, .5, -.5, -.5), tl, tr_, br, bl)
        p.setPen(QPen(T.border, 1))
        p.setBrush(T.card)
        p.drawPath(path)
        cf = self.cf
        col = BREAK if e_.mode != "focus" else T.accent
        cy = r.center().y()
        if cf < 0.99:
            p.setOpacity(1 - cf)
            c, R = QPointF(r.left() + lerp(36, 27, s), cy), lerp(17, 11.5, s)
            p.setBrush(NOBRUSH)
            lw = lerp(4, 3, s)
            p.setPen(QPen(T.track, lw))
            p.drawEllipse(c, R, R)
            prog = e_.prog
            if prog > .003:
                p.setPen(QPen(col, lw, Qt.PenStyle.SolidLine, CAP_R))
                p.drawArc(QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), 90 * 16, int(-prog * 360 * 16))
            tx = r.left() + lerp(68, 48, s)
            size = lerp(27, 19, s)
            txt = fmt_clock(e_.remaining, up=e_.free)
            xl = (self.fin.x() if self._show_fin else self.play.x()) - 8
            text(p, QRectF(tx, cy - lerp(26, 17, s), xl - tx, size * 1.3), txt, F(size, W_LIGHT), T.text, "l", False)
            cap = tr("mode.paused") if (e_.started and not e_.running) else \
                tr("mode.free") if (e_.free and e_.mode == "focus") else tr("mode." + e_.mode)
            task = self.store.task(self.store.d.get("current_task"))
            ccol = col if e_.running else T.text3
            if task and e_.mode == "focus" and not task["done"]:
                cap += "  ·  " + task["title"]
            if self._flash:
                cap, ccol = self._flash.upper(), T.accent if T.accent_key != "graphite" else T.text
            text(p, QRectF(tx, cy + lerp(10, 7, s), xl - tx, 16), cap, F(lerp(10, 9, s), W_MED, 1.0), ccol)
        if cf > 0.01:
            p.setOpacity(cf)
            f, h, a, b, c = self._crects()
            p.setPen(NOPEN)
            p.setBrush(T.primary)
            p.drawRoundedRect(a, h / 2, h / 2)
            draw_icon(p, "check", a.left() + 17, a.center().y(), 15, T.on_primary, w=2.0)
            text(p, QRectF(a.left() + 30, a.top(), a.width() - 34, h), tr("mini.task_done"), f, T.on_primary, "l", False)
            p.setPen(QPen(T.hair, 1))
            p.setBrush(T.body)
            p.drawRoundedRect(b, h / 2, h / 2)
            text(p, b, tr("mini.only"), f, T.text, "c", False)
            p.setPen(NOPEN)
            p.setBrush(T.body)
            p.drawEllipse(c)
            draw_icon(p, "close", c.center().x(), c.center().y(), 12, T.text2, w=1.7)


# ───────────────────────────── main window ─────────────────────────────
class MainWindow(QWidget):
    M, W, H = 26, 430, 720

    def __init__(self, store, engine):
        super().__init__()
        self.store, self.engine = store, engine
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(logo_pixmap(256)))
        self.setFixedSize(self.W + 2 * self.M, self.H + 2 * self.M)
        self._ontop, self._last_sec, self._intro_done, self._autostart = False, None, False, None
        self.frame = QWidget(self)
        self.frame.setGeometry(self.M, self.M, self.W, self.H)
        self.titlebar = TitleBar(self, self.frame)
        self.titlebar.setGeometry(0, 0, self.W, 36)
        self.header = Header(self.frame)
        self.header.setGeometry(0, 36, self.W, 80)
        self.host = PageHost(self.frame)
        self.host.setGeometry(0, 116, self.W, self.H - 116)
        self.toast = Toast(self.frame)
        self.focus = FocusPage(store, engine)
        self.tasks = TasksPage(store, engine)
        self.stats = StatsPage(store, engine)
        self.profile = ProfilePage(store, engine)
        self.settings = SettingsPage(store, engine)
        for pg in (self.focus, self.tasks, self.stats, self.profile, self.settings):
            self.host.add(pg)
        self.focus.toast = self.tasks.toast = self.settings.toast = self.tasks.goals.toast = self.toast.queue
        self.settings.open_support = self.open_support
        self.focus.goto_tasks.connect(lambda: self.go(1))
        self.focus.goto_mini.connect(self.enter_mini)
        self.splash = Splash(self.host)
        self.splash.setGeometry(self.host.rect())
        self.host.overlay = self.splash
        self.support = SupportPage(store, self.frame)
        self.support.setGeometry(0, 116, self.W, self.H - 116)
        self.tabs = TabBar(self.frame)
        self.tabs.move((self.W - 390) // 2, self.H - 92)
        self.tabs.changed.connect(self.go)
        self.outline = Outline(self.frame)
        self.outline.setGeometry(0, 0, self.W, self.H)
        self.mini = MiniWindow(store, engine)
        self.mini.expand.connect(self.leave_mini)
        for i in range(5):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.go(i))
        QShortcut(QKeySequence("Space"), self, activated=engine.toggle)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self.enter_mini)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.focus.request_finish)
        QShortcut(QKeySequence("Esc"), self, activated=self.support.close_page)
        engine.tick.connect(self.on_tick)
        engine.completed.connect(self.on_completed)
        engine.warning.connect(lambda: self.toast.queue(tr("warn.1min")))
        engine.finished_early.connect(self.on_early)
        store.goal_done.connect(lambda t: self.toast.queue(tr("gl.auto", t=t)))
        store.changed.connect(self.on_store)
        store.levelup.connect(lambda l: self.toast.queue(tr("lvup", l=l, t=level_title(l))))
        store.unlocked.connect(lambda k: self.toast.queue(tr("ach.unlocked", n=tr("ach." + k))))
        store.goal_hit.connect(self.on_goal_hit)
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                lambda *_: self.change_theme() if store.s("theme") == "auto" else None)
        except Exception:
            pass
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(QIcon(logo_pixmap(64)), self)
            m = QMenu()
            self.a_toggle, self.a_reset = m.addAction(""), m.addAction("")
            self.a_skip = m.addAction("")
            m.addSeparator()
            self.a_mini, self.a_open, self.a_quit = m.addAction(""), m.addAction(""), m.addAction("")
            self.a_toggle.triggered.connect(engine.toggle)
            self.a_reset.triggered.connect(engine.reset)
            self.a_skip.triggered.connect(engine.skip)
            self.a_mini.triggered.connect(self.enter_mini)
            self.a_open.triggered.connect(self.leave_mini)
            self.a_quit.triggered.connect(self.quit)
            m.aboutToShow.connect(self.update_tray_menu)
            self.tray.setContextMenu(m)
            self.tray.activated.connect(self.on_tray)
            self.tray.show()
            self._menu = m
        self.tabs.vis = 0.0
        self.apply_settings()
        self.refresh_header(True)

    # lifecycle
    def start(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - self.width() // 2, scr.center().y() - self.height() // 2)
        self.show()
        self.host.show_page(0, False)
        self.splash.raise_()
        if not _ANIM:
            self.splash.hide()
            self.tabs.vis = 1.0
            self.finish_intro(False)
            return
        A(self, "windowOpacity", self.store.s("opacity") / 100.0, 350, OUT, start=0)
        A(self.splash, "t", 1.0, 900, OUT, start=0)
        self.header.set_state(tr("hd.start"), tr("hd.prep"), 0, True, True)
        self.header.set_state(tr("hd.start"), tr("hd.prep"), 100, True, True, 1500)
        QTimer.singleShot(1750, self.finish_intro)

    def finish_intro(self, animate=True):
        self._intro_done = True
        self.setWindowOpacity(self.store.s("opacity") / 100.0)
        self.refresh_header()
        if animate:
            A(self.splash, "out", 1.0, 550, OUT, finished=self.splash.hide)
            A(self.tabs, "vis", 1.0, 700, OUT)
        self.focus.on_show()
        self.header.update()

    def restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit(self):
        self.store.save()
        QApplication.quit()

    def closeEvent(self, e):
        if self.engine.running and self.tray:
            e.ignore()
            self.hide()
            self.mini.popup()
            self.tray.showMessage(APP_NAME, tr("tray.bg"), QSystemTrayIcon.MessageIcon.Information, 2500)
        else:
            self.quit()

    def minimize(self):
        self.enter_mini() if self.store.s("mini_min") else self.showMinimized()

    def enter_mini(self):
        self.hide()
        self.mini.popup()

    def leave_mini(self):
        self.mini.hide()
        self.restore()

    def on_tray(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.leave_mini()

    def update_tray_menu(self):
        e = self.engine
        self.a_toggle.setText(tr("tray.pause") if e.running else tr("tray.start"))
        self.a_reset.setText(tr("tip.reset"))
        self.a_skip.setText(tr("tray.finish") if e.mode == "focus" else tr("tip.skip"))
        self.a_mini.setText(tr("tip.mini"))
        self.a_open.setText(tr("tray.open"))
        self.a_quit.setText(tr("tray.quit"))

    def go(self, i):
        self.support.close_page()
        self.tabs.set_index(i)
        self.host.show_page(i)

    def open_support(self):
        self.support.open_page()
        self.tabs.raise_()
        self.outline.raise_()
        self.toast.raise_()

    # state
    def refresh_header(self, instant=False):
        done, total = self.store.today_progress()
        foc = self.store.day(today())["focus"]
        gd, gt = self.store.goal_progress()
        ft = tr("hd.focus", x=fmt_minutes(foc))
        wk = [tr("hd.week", p=min(999, int(100 * gd / gt)))] if gt > 0 else []
        if total == 0:
            head, parts, pct, show = tr("hd.today"), [tr("hd.add_first")] + ([ft] if foc else []) + wk, 0, False
        elif done == total:
            head, parts, pct, show = tr("hd.closed"), [tr("hd.all_done"), ft] + wk, 100, False
        else:
            head, parts, pct, show = tr("hd.today"), [tr("hd.done_of", d=done, t=total), ft] + wk, 100 * done / total, True
        self.header.set_state(head, "  ·  ".join(parts), pct, show, instant)

    def on_store(self, topic):
        if topic in ("tasks", "stats", "goal", "settings", "lang", "all"):
            self.refresh_header()
        if topic in ("appearance", "all"):
            self.change_theme()
        if topic in ("settings", "lang", "all"):
            self.apply_settings()
        if topic in ("lang", "all"):
            self._last_sec = None
            self.on_tick()
            self.update_tray_menu() if self.tray else None
            self.mini.on_state()

    def apply_settings(self):
        s = self.store
        set_lang(s.s("lang"))
        set_animations(s.s("animations"))
        set_ticks(s.s("ticks"))
        T.apply(s.s("theme"), s.s("accent"))
        want = bool(s.s("on_top"))
        if want != self._ontop:
            self._ontop = want
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, want)
            if self.isVisible():
                self.show()
        if self._intro_done:
            self.setWindowOpacity(s.s("opacity") / 100.0)
        if self._autostart is None or self._autostart != s.s("autostart"):
            if self._autostart is not None:
                set_autostart(s.s("autostart"))
            self._autostart = s.s("autostart")
        self.engine.apply_settings()
        self.on_tick()
        self.update()

    def change_theme(self):
        T.apply(self.store.s("theme"), self.store.s("accent"))
        ov = None
        if _ANIM and self.isVisible():
            ov = QLabel(self.frame)
            ov.setPixmap(self.frame.grab())
            ov.setGeometry(0, 0, self.W, self.H)
            ov.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            ov.show()
        for w in self.findChildren(QWidget):
            if hasattr(w, "restyle"):
                w.restyle()
            w.update()
        self.mini.update()
        if ov:
            eff = QGraphicsOpacityEffect(ov)
            ov.setGraphicsEffect(eff)
            an = QPropertyAnimation(eff, b"opacity", ov)
            an.setDuration(520)
            an.setStartValue(1.0)
            an.setEndValue(0.0)
            an.setEasingCurve(OUT)
            an.finished.connect(ov.deleteLater)
            an.start()

    def on_tick(self):
        e = self.engine
        sec = int(e.remaining) if e.free else int(math.ceil(e.remaining))
        key = (sec, e.running, e.mode, LANG)
        if key == self._last_sec:
            return
        self._last_sec = key
        if self.store.s("title_time") and e.running:
            t = f"{fmt_clock(e.remaining, up=e.free)}  ·  {tr('mode.free' if e.free else 'mode.' + e.mode).capitalize()}  —  {APP_NAME}"
        else:
            t = APP_NAME
        self.setWindowTitle(t)
        self.titlebar.update()
        if self.tray:
            self.tray.setToolTip(t)

    def on_completed(self, mode):
        s = self.store
        if mode == "focus":
            msg, sub = tr("done.focus"), tr("done.focus_sub")
            self.focus.ring.celebrate()
        else:
            msg, sub = tr("done.break"), tr("done.break_sub")
        self.toast.queue(msg + (f"  ·  +{int(round(self.engine.last_gain))}" if mode == "focus" and self.engine.last_gain >= 1 else ""))
        if s.s("sound"):
            play_sound(s.s("sound_focus" if mode == "focus" else "sound_break"), s.s("volume"))
        if s.s("notify") and self.tray:
            self.tray.showMessage(msg, sub, QSystemTrayIcon.MessageIcon.Information, 4000)
        if s.s("popup_end") and not self.isVisible():
            self.leave_mini()

    def on_early(self, mins, gain, closed):
        s = self.store
        if mins < 1 and not closed:
            self.toast.queue(tr("fin.too_short"))
            return
        self.toast.queue(tr("fin.saved", m=fmt_minutes(mins), p=int(round(gain))))
        self.focus.ring.celebrate()
        if s.s("sound"):
            play_sound(s.s("sound_focus"), s.s("volume"))

    def on_goal_hit(self):
        self.toast.queue(tr("wg.hit"))
        if self.store.s("notify") and self.tray:
            self.tray.showMessage(APP_NAME, tr("wg.hit"), QSystemTrayIcon.MessageIcon.Information, 4000)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(RH)
        r = QRectF(self.M, self.M, self.W, self.H)
        p.setPen(NOPEN)
        for i in range(self.M):
            a = 0.03 * (1 - i / self.M) ** 2.2
            p.setBrush(QColor(0, 0, 0, int(255 * a)))
            p.drawRoundedRect(r.adjusted(-i, -i + 6, i, i + 6), RADIUS + i, RADIUS + i)


def make_icon_files():
    pm = logo_pixmap(256)
    pm.save("app.png")
    ok = pm.save("app.ico")
    print("Saved: app.png" + (", app.ico" if ok else " (ico failed — convert app.png to .ico with any converter)"))


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("heartcache.graphite.time")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    global FAMILY
    FAMILY = pick_family()
    if "--make-icon" in sys.argv:
        make_icon_files()
        return
    store = Store()
    if not store.s("lang"):
        store.d["settings"]["lang"] = detect_lang()
    set_lang(store.s("lang"))
    set_animations(store.s("animations"))
    set_ticks(store.s("ticks"))
    T.apply(store.s("theme"), store.s("accent"))
    engine = Engine(store)
    win = MainWindow(store, engine)
    win.start()
    app.aboutToQuit.connect(store.save)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
