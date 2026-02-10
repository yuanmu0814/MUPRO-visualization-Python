from __future__ import annotations

from PyQt5 import QtCore, QtWidgets, uic


class DomainCriteria(QtWidgets.QDialog):
    def __init__(self, simple_view, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        ui_path = QtCore.QDir.toNativeSeparators(
            QtCore.QDir.current().absoluteFilePath("ui/domainCriteria.ui")
        )
        self.ui = uic.loadUi(ui_path, self)
        self.main3d = simple_view
        self.domain_std_angle = 180.0
        self.domain_std_value = 0.5

        self.ui.domainStdAngle_LE.editingFinished.connect(
            self.on_domainStdAngle_LE_editingFinished
        )
        self.ui.domainStdValue_LE.editingFinished.connect(
            self.on_domainStdValue_LE_editingFinished
        )

    def getDomainStdAngle(self) -> float:
        return self.domain_std_angle

    def getDomainStdValue(self) -> float:
        return self.domain_std_value

    def on_domainStdValue_LE_editingFinished(self) -> None:
        try:
            self.domain_std_value = float(self.ui.domainStdValue_LE.text())
        except ValueError:
            return

    def on_domainStdAngle_LE_editingFinished(self) -> None:
        try:
            self.domain_std_angle = float(self.ui.domainStdAngle_LE.text())
        except ValueError:
            return
