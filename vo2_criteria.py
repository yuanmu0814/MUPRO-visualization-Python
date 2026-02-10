from __future__ import annotations

from PyQt5 import QtCore, QtWidgets, uic


class VO2Criteria(QtWidgets.QDialog):
    def __init__(self, simple_view, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        ui_path = QtCore.QDir.toNativeSeparators(
            QtCore.QDir.current().absoluteFilePath("ui/VO2Criteria.ui")
        )
        self.ui = uic.loadUi(ui_path, self)
        self.main3d = simple_view
        self.m1_mod = 0.1
        self.m1_ang = 10.0
        self.m2_mod = 0.1
        self.m2_ang = 10.0

        self.ui.vo2_M1_mod_LE.editingFinished.connect(
            self.on_vo2_M1_mod_LE_editingFinished
        )
        self.ui.vo2_M1_ang_LE.editingFinished.connect(
            self.on_vo2_M1_ang_LE_editingFinished
        )
        self.ui.vo2_M2_mod_LE.editingFinished.connect(
            self.on_vo2_M2_mod_LE_editingFinished
        )
        self.ui.vo2_M2_ang_LE.editingFinished.connect(
            self.on_vo2_M2_ang_LE_editingFinished
        )

    def getM1_mod(self) -> float:
        return self.m1_mod

    def getM1_ang(self) -> float:
        return self.m1_ang

    def getM2_mod(self) -> float:
        return self.m2_mod

    def getM2_ang(self) -> float:
        return self.m2_ang

    def on_vo2_M1_mod_LE_editingFinished(self) -> None:
        try:
            self.m1_mod = float(self.ui.vo2_M1_mod_LE.text())
        except ValueError:
            return

    def on_vo2_M1_ang_LE_editingFinished(self) -> None:
        try:
            self.m1_ang = float(self.ui.vo2_M1_ang_LE.text())
        except ValueError:
            return

    def on_vo2_M2_mod_LE_editingFinished(self) -> None:
        try:
            self.m2_mod = float(self.ui.vo2_M2_mod_LE.text())
        except ValueError:
            return

    def on_vo2_M2_ang_LE_editingFinished(self) -> None:
        try:
            self.m2_ang = float(self.ui.vo2_M2_ang_LE.text())
        except ValueError:
            return
