from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

BG = "#0c0e14"
SIDEBAR = "#10131b"
SURFACE = "#141823"
CARD = "#181c28"
CARD_HOVER = "#1d2230"
BORDER = "#252b3b"
BORDER_STRONG = "#343b52"
TEXT = "#e8eaf2"
MUTED = "#8a92a8"
FAINT = "#5b6278"
ACCENT = "#7c6cff"
ACCENT_2 = "#4f8cff"
SUCCESS = "#3ecf8e"
WARN = "#f2b84b"
DANGER = "#f0627a"

QSS = f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif; font-size: 13px; color: {TEXT}; outline: 0; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#page {{ background: {BG}; }}
QWidget#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
QLabel {{ background: transparent; }}
QLabel#appName {{ font-size: 17px; font-weight: 700; letter-spacing: 0.3px; }}
QLabel#appTag {{ color: {MUTED}; font-size: 12px; }}
QLabel#pageTitle {{ font-size: 24px; font-weight: 700; }}
QLabel#pageSub {{ color: {MUTED}; font-size: 13px; }}
QLabel#sectionTitle {{ font-size: 11px; font-weight: 600; color: {MUTED}; letter-spacing: 1.2px; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#faint {{ color: {FAINT}; font-size: 12px; }}
QLabel#cardTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#bigNumber {{ font-size: 22px; font-weight: 700; }}

QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}
QFrame#cardFlat {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}

QFrame#dropCard {{ background: {CARD}; border: 1.5px dashed {BORDER_STRONG}; border-radius: 16px; }}
QFrame#dropCard:hover {{ background: {CARD_HOVER}; border-color: {ACCENT}; }}
QFrame#dropCard[state="ok"] {{ border: 1.5px solid rgba(62,207,142,0.55); background: {CARD}; }}
QFrame#dropCard[state="warn"] {{ border: 1.5px solid rgba(242,184,75,0.6); background: {CARD}; }}
QFrame#dropCard[state="error"] {{ border: 1.5px solid rgba(240,98,122,0.6); background: {CARD}; }}
QFrame#dropCard[drag="true"] {{ border: 1.5px solid {ACCENT}; background: #1b1f33; }}

QPushButton {{ background: {CARD_HOVER}; border: 1px solid {BORDER_STRONG}; border-radius: 9px; padding: 8px 16px; font-weight: 500; }}
QPushButton:hover {{ background: #252b3d; border-color: #46506b; }}
QPushButton:pressed {{ background: #1a1f2e; }}
QPushButton:disabled {{ color: {FAINT}; background: {SURFACE}; border-color: {BORDER}; }}
QPushButton#primary {{ border: none; color: white; font-weight: 600; padding: 11px 24px; border-radius: 10px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2}); }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8e80ff, stop:1 #639aff); }}
QPushButton#primary:pressed {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6a5be6, stop:1 #4379e6); }}
QPushButton#primary:disabled {{ background: #232839; color: {FAINT}; }}
QPushButton#ghost {{ background: transparent; border: 1px solid transparent; color: {MUTED}; }}
QPushButton#ghost:hover {{ background: {CARD_HOVER}; color: {TEXT}; }}
QPushButton#chip {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 15px; padding: 6px 14px; color: {MUTED}; }}
QPushButton#chip:hover {{ color: {TEXT}; border-color: {BORDER_STRONG}; }}
QPushButton#chip:checked {{ background: rgba(124,108,255,0.16); border-color: {ACCENT}; color: {TEXT}; }}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 9px;
    padding: 8px 11px; selection-background-color: {ACCENT}; min-height: 18px; }}
QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: {BORDER_STRONG}; }}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {BORDER_STRONG}; border-radius: 8px; padding: 4px;
    selection-background-color: rgba(124,108,255,0.28); outline: 0; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}

QCheckBox {{ spacing: 9px; background: transparent; }}
QCheckBox::indicator {{ width: 17px; height: 17px; border-radius: 5px; border: 1px solid {BORDER_STRONG}; background: {SURFACE}; }}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url(:/none); }}

QProgressBar {{ background: {SURFACE}; border: none; border-radius: 4px; height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ border-radius: 4px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2}); }}

QTableView {{ background: transparent; border: none; gridline-color: transparent; selection-background-color: transparent; }}
QTableView::item {{ padding: 0 10px; border-bottom: 1px solid {BORDER}; }}
QTableView::item:selected {{ background: rgba(124,108,255,0.16); }}
QTableView::item:hover {{ background: rgba(255,255,255,0.03); }}
QHeaderView::section {{ background: {CARD}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER};
    padding: 10px; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2c3347; border-radius: 4px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: #3b4562; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #2c3347; border-radius: 4px; min-width: 36px; }}
QPlainTextEdit {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; padding: 8px;
    font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px; color: {MUTED}; }}
QToolTip {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER_STRONG}; padding: 5px 8px; border-radius: 6px; }}
QMessageBox {{ background: {CARD}; }}
QSplitter::handle {{ background: transparent; }}
"""


def apply(app: QApplication) -> None:
    for fam in ("Segoe UI Variable Text", "Segoe UI", "Inter"):
        if fam in QFontDatabase.families():
            f = QFont(fam)
            f.setPixelSize(13)
            app.setFont(f)
            break
    app.setStyle("Fusion")
    app.setStyleSheet(QSS.replace("url(:/none)", f"url({_check_icon()})"))


def _check_icon() -> str:
    import tempfile
    from pathlib import Path
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QPainter, QPen, QPixmap
    path = Path(tempfile.gettempdir()) / "TimelineBuilder" / "check.png"
    path.parent.mkdir(exist_ok=True)
    pm = QPixmap(34, 34)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("white"), 3.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline([QPointF(9, 18), QPointF(15, 24), QPointF(25, 11)])
    p.end()
    pm.save(str(path))
    return path.as_posix()


def qcolor(hexstr: str, alpha: int = 255) -> QColor:
    c = QColor(hexstr)
    c.setAlpha(alpha)
    return c
