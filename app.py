import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from simple_view import SimpleView


def _build_fallback_icon() -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(256, 256)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(QtGui.QColor(35, 125, 220))
    painter.drawRoundedRect(12, 12, 232, 232, 42, 42)
    painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
    font = QtGui.QFont("Segoe UI", 96, QtGui.QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, "M")
    painter.end()
    return QtGui.QIcon(pixmap)


def _resolve_app_icon(base: str) -> QtGui.QIcon:
    icon_candidates = [
        os.path.join(base, "Icons", "mupro-logo-new.ico"),
        os.path.join(base, "Icons", "mupro-logo-new.png"),
    ]
    for icon_file in icon_candidates:
        if os.path.isfile(icon_file):
            icon = QtGui.QIcon(icon_file)
            if not icon.isNull():
                return icon
    return _build_fallback_icon()


def _get_base_path() -> str:
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        try:
            main_mod = sys.modules.get("__main__")
            if main_mod and hasattr(main_mod, "__compiled__"):
                comp = main_mod.__compiled__
                if hasattr(comp, "containing_dir_path"):
                    return comp.containing_dir_path
        except Exception:
            pass
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    base = _get_base_path()

    os.chdir(base)
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app_icon = _resolve_app_icon(base)
    app.setWindowIcon(app_icon)
    window = SimpleView()
    window.setWindowIcon(app_icon)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
