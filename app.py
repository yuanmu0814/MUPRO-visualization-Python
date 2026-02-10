import os
import sys

from PyQt5 import QtWidgets

from simple_view import SimpleView


def main() -> int:
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SimpleView()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
