import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui import theme
from app.ui.main_window import MainWindow


def resource(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Timeline Builder")
    icon = resource("assets/icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    theme.apply(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
