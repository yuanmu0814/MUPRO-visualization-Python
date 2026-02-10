from __future__ import annotations

from PyQt5 import QtCore, QtWidgets, uic


class Batch3D(QtWidgets.QDialog):
    def __init__(self, simple_view, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        ui_path = QtCore.QDir.toNativeSeparators(
            QtCore.QDir.current().absoluteFilePath("ui/batch3D.ui")
        )
        self.ui = uic.loadUi(ui_path, self)
        self.main3d = simple_view

        self.export_dir = ""
        self.scalar_dir = ""
        self.vector_dir = ""
        self.domain_dir = ""
        self.status_file = ""

        self.scalar_flag = False
        self.vector_flag = False
        self.domain_flag = False
        self.output_flag = False

        self.ui.loadStatusFile_PB.clicked.connect(self.on_loadStatusFile_PB_released)
        self.ui.loadScalar_PB.clicked.connect(self.on_loadScalar_PB_released)
        self.ui.loadVector_PB.clicked.connect(self.on_loadVector_PB_released)
        self.ui.loadDomain_PB.clicked.connect(self.on_loadDomain_PB_released)
        self.ui.exportDir_PB.clicked.connect(self.on_exportDir_PB_released)

    def formName(self, file_name: str, time_step: int) -> str:
        return f"{file_name}.{time_step:08d}"

    def formDataName(self, file_name: str, time_step: int) -> str:
        return f"{file_name}.{time_step:08d}.dat"

    def on_loadStatusFile_PB_released(self) -> None:
        self.status_file = self.main3d.slotLoadStatus()
        self.ui.loadScalar_PB.setEnabled(self.main3d.scalar)
        self.ui.loadVector_PB.setEnabled(self.main3d.vector)
        self.ui.loadDomain_PB.setEnabled(self.main3d.domain)

    def on_loadScalar_PB_released(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Scalar data", "", "Scalar data (*.*)"
        )
        if file_path:
            self.scalar_dir = QtCore.QFileInfo(file_path).absolutePath()
            self.ui.scalarName_LB.setText(QtCore.QFileInfo(file_path).baseName())
            self.scalar_flag = True
        else:
            self.scalar_flag = False

    def on_loadVector_PB_released(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Vector data", "", "Vector data (*.*)"
        )
        if file_path:
            self.vector_dir = QtCore.QFileInfo(file_path).absolutePath()
            self.ui.vectorName_LB.setText(QtCore.QFileInfo(file_path).baseName())
            self.vector_flag = True
        else:
            self.vector_flag = False

    def on_loadDomain_PB_released(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Domain data", "", "Domain data (*.*)"
        )
        if file_path:
            self.domain_dir = QtCore.QFileInfo(file_path).absolutePath()
            self.ui.domainName_LB.setText(QtCore.QFileInfo(file_path).baseName())
            self.domain_flag = True
        else:
            self.domain_flag = False

    def on_exportDir_PB_released(self) -> None:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Export directory"
        )
        if dir_path:
            self.export_dir = QtCore.QFileInfo(dir_path).absoluteFilePath()
            self.ui.exportDir_LB.setText(QtCore.QFileInfo(dir_path).baseName())
            self.output_flag = True
        else:
            self.output_flag = False

    def accept(self) -> None:
        if self.loopThroughKt():
            self.close()
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Alert",
                "All field must be filled before running batch processing.",
            )

    def loopThroughKt(self) -> bool:
        if not (
            (self.scalar_flag or self.vector_flag or self.domain_flag)
            and self.output_flag
            and self.ui.timeBegin_LE.text()
            and self.ui.timeInterval_LE.text()
            and self.ui.timeEnd_LE.text()
        ):
            return False

        start = int(self.ui.timeBegin_LE.text())
        interval = int(self.ui.timeInterval_LE.text())
        end = int(self.ui.timeEnd_LE.text())

        if self.ui.loadScalar_PB.isEnabled():
            QtCore.QDir().mkpath(f"{self.export_dir}/scalar/")
        if self.ui.loadVector_PB.isEnabled():
            QtCore.QDir().mkpath(f"{self.export_dir}/vector/")
        if self.ui.loadDomain_PB.isEnabled():
            QtCore.QDir().mkpath(f"{self.export_dir}/domain/")
        QtCore.QDir().mkpath(f"{self.export_dir}/images/")

        for i in range(start, end + 1, interval):
            scalar_name = ""
            vector_name = ""

            if self.ui.loadScalar_PB.isEnabled():
                file_base = f"{self.scalar_dir}/{self.ui.scalarName_LB.text()}"
                scalar_data = self.formDataName(file_base, i)
                self.main3d.loadData(scalar_data)
                scalar_name = f"{self.export_dir}/scalar/{self.ui.scalarName_LB.text()}"
                scalar_out = self.formName(scalar_name, i)
                self.main3d.outputScalar(
                    QtCore.QFileInfo(scalar_out).absoluteFilePath(),
                    self.main3d.scalarColumn,
                    self.main3d.tempX - 1,
                    self.main3d.tempY - 1,
                    self.main3d.tempZ - 1,
                )
                scalar_name = f"{scalar_out}.{self.main3d.scalarColumn + 1}.vtk"

            if self.ui.loadVector_PB.isEnabled():
                file_base = f"{self.vector_dir}/{self.ui.vectorName_LB.text()}"
                vector_data = self.formDataName(file_base, i)
                self.main3d.loadData(vector_data)
                vector_name = f"{self.export_dir}/vector/{self.ui.vectorName_LB.text()}"
                vector_out = self.formName(vector_name, i)
                hold = self.main3d.vectorColumn
                self.main3d.outputVector(
                    vector_out,
                    hold,
                    hold + 1,
                    hold + 2,
                    self.main3d.tempX - 1,
                    self.main3d.tempY - 1,
                    self.main3d.tempZ - 1,
                )
                hold = hold + 1
                vector_name = f"{vector_out}.{hold}{hold+1}{hold+2}.vtk"

            if self.ui.loadDomain_PB.isEnabled():
                file_base = f"{self.domain_dir}/{self.ui.domainName_LB.text()}"
                domain_data = self.formDataName(file_base, i)
                self.main3d.loadData(domain_data)
                domain_name = f"{self.export_dir}/domain/{self.ui.domainName_LB.text()}"
                domain_out = self.formName(domain_name, i)
                self.main3d.outputDomain(
                    domain_out,
                    self.main3d.tempX - 1,
                    self.main3d.tempY - 1,
                    self.main3d.tempZ - 1,
                )
                domain_vtk = f"{domain_out}.domain.vtk"
                self.main3d.drawDomain(domain_vtk)

            self.main3d.updateVTK(scalar_name, vector_name)
            if self.status_file:
                self.main3d.loadStatus(QtCore.QFileInfo(self.status_file))
            self.main3d.slotUpdate()
            self.main3d.on_cameraSet_PB_released()
            image_path = (
                self.formName(f"{self.export_dir}/images/{self.ui.outputName_LE.text()}", i)
                + ".png"
            )
            self.main3d.outputImage(QtCore.QFileInfo(image_path).absoluteFilePath())

        return True
