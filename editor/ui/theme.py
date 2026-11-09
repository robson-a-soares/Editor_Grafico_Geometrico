"""Tema escuro da interface (estilo Fusion + paleta + folha de estilos)."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

ACCENT = "#5B8FFF"
BG = "#1E2026"
PANEL = "#262930"
PANEL_2 = "#2E323A"
BORDER = "#3A3F4A"
TEXT = "#E6E8EE"
MUTED = "#9AA1AF"

STYLESHEET = f"""
QMainWindow, QWidget {{ font-size: 10pt; }}
QToolBar {{ background: {PANEL}; border: none; spacing: 2px; padding: 3px; }}
QToolBar::separator {{ background: {BORDER}; width: 1px; height: 1px; margin: 4px; }}
QToolButton {{ border: 1px solid transparent; border-radius: 6px; padding: 4px; color: {TEXT}; }}
QToolButton:hover {{ background: {PANEL_2}; border-color: {BORDER}; }}
QToolButton:checked {{ background: #34405E; border-color: {ACCENT}; }}
QToolButton:pressed {{ background: #2B3550; }}
QDockWidget {{ color: {TEXT}; titlebar-close-icon: none; }}
QDockWidget::title {{ background: {PANEL}; padding: 6px 8px; font-weight: 600; }}
QGroupBox {{ border: 1px solid {BORDER}; border-radius: 8px; margin-top: 14px; padding: 8px 6px 6px 6px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {MUTED}; font-weight: 600; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {BG}; border: 1px solid {BORDER};
    border-radius: 5px; padding: 3px 5px; color: {TEXT}; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 5px 10px; color: {TEXT}; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: #2B3550; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #7AA6FF; }}
QTreeWidget {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 6px; }}
QTreeWidget::item {{ padding: 3px 0; }}
QTreeWidget::item:selected {{ background: #34405E; color: white; }}
QScrollArea {{ border: none; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; }}
QStatusBar QLabel {{ color: {MUTED}; padding: 0 6px; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px 5px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: #34405E; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QMenuBar {{ background: {PANEL}; }}
QMenuBar::item:selected {{ background: #34405E; border-radius: 4px; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#matrix {{ font-family: Consolas, 'DejaVu Sans Mono', monospace; background: {BG};
    border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 6px; }}
QTextBrowser {{ background: {BG}; border: none; color: {TEXT}; }}
QCheckBox {{ spacing: 6px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle(QStyleFactory.create("Fusion"))
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(PANEL))
    p.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Base, QColor(BG))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL_2))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(PANEL_2))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Button, QColor(PANEL_2))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED))
    p.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor("#6B7280"))
    app.setPalette(p)
    app.setStyleSheet(STYLESHEET)
