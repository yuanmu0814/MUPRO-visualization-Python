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


def main() -> int:
    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))

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
