import math

from PyQt5 import QtCore, QtWidgets

from constants import PI_VALUE
from domain_criteria import DomainCriteria
from stats_utils import get_avg, get_max, get_min
from vo2_criteria import VO2Criteria


def slot_open_file_scalar(view) -> None:
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(view, "Input", "", "Input (*.*)")
    if not file_path:
        return
    suffix = QtCore.QFileInfo(file_path).suffix().lower()
    if suffix != "vtk":
        view.columns = view.loadData(file_path)
        view.inputTab.setCurrentIndex(0)
        view.data2Dx = view.tempX == 1
        view.data2Dy = view.tempY == 1
        view.data2Dz = view.tempZ == 1

        view.scalar_CB.setCheckState(QtCore.Qt.Checked)
        view.volume_CB.setCheckState(QtCore.Qt.Checked)
        view.vector_CB.setCheckState(QtCore.Qt.Unchecked)
        view.domain_CB.setCheckState(QtCore.Qt.Unchecked)

        file_info = QtCore.QFileInfo(file_path)
        view.scalarDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

        view.scalarChoice.clear()
        for i in range(view.columns):
            view.outputScalar(view.scalarDir.absoluteFilePath(), i, view.xmax, view.ymax, view.zmax)
            view.scalarChoice.addItem(str(i + 1))

        view.inputFileScalar.setText(file_info.fileName())
        view.rowcolScalar.setText(str(view.columns))
        view.xMinMaxScalar.setText(f"1 - {view.xmax + 1}")
        view.yMinMaxScalar.setText(f"1 - {view.ymax + 1}")
        view.zMinMaxScalar.setText(f"1 - {view.zmax + 1}")

        view.scalar_Table.clearContents()
        while view.scalar_Table.rowCount() > 0:
            view.scalar_Table.removeRow(0)
        for i in range(view.columns):
            col_values = [row[i] for row in view.vtk_data]
            view.scalar_Table.insertRow(view.scalar_Table.rowCount())
            view.scalar_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(get_min(col_values))))
            view.scalar_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(get_max(col_values))))
            view.scalar_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(get_avg(col_values))))

        view.scalarName = f"{view.scalarDir.absoluteFilePath()}.{view.scalarChoice.currentIndex()+1}.vtk"
        view.updateVTK(view.scalarName, view.vectorName)
        view.vtk_data = []
    else:
        view.columns = 1
        view.scalarChoice.clear()
        view.scalarChoice.addItem("1")
        view.scalar_Table.clearContents()
        while view.scalar_Table.rowCount() > 0:
            view.scalar_Table.removeRow(0)
        view.scalar_CB.setCheckState(QtCore.Qt.Checked)
        view.volume_CB.setCheckState(QtCore.Qt.Checked)
        view.vector_CB.setCheckState(QtCore.Qt.Unchecked)
        view.domain_CB.setCheckState(QtCore.Qt.Unchecked)
        view.xmax = 10
        view.ymax = 10
        view.zmax = 10
        view.scalarName = file_path
        view.updateVTK(view.scalarName, view.vectorName)


def on_scalar_choice_current_index_changed(view, _index: int) -> None:
    if view.scalarChoice.count() <= 0:
        return
    base = view.scalarDir.absoluteFilePath()
    if base:
        view.scalarName = f"{base}.{view.scalarChoice.currentIndex()+1}.vtk"
    view.updateFlag = False
    if view.stackedWidget.currentIndex() == 0 and view.scalar_CB.isChecked():
        view.slotUpdate()


def slot_open_file_vector(view) -> None:
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(view, "Input", "", "Input (*.*)")
    if not file_path:
        return
    suffix = QtCore.QFileInfo(file_path).suffix().lower()
    if suffix != "vtk":
        view.columns = view.loadData(file_path)
        view.inputTab.setCurrentIndex(1)
        file_info = QtCore.QFileInfo(file_path)
        view.vectorDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

        view.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
        view.volume_CB.setCheckState(QtCore.Qt.Unchecked)
        view.vector_CB.setCheckState(QtCore.Qt.Checked)
        view.vectorGlyph_CB.setCheckState(QtCore.Qt.Checked)
        view.domain_CB.setCheckState(QtCore.Qt.Unchecked)

        view.vectorChoice.clear()
        for i in range(view.columns // 3):
            view.outputVector(
                view.vectorDir.absoluteFilePath(), 3 * i, 3 * i + 1, 3 * i + 2, view.xmax, view.ymax, view.zmax
            )
            view.vectorChoice.addItem(f"{3*i+1}{3*i+2}{3*i+3}")

        view.inputFileVector.setText(file_info.fileName())
        view.rowcolVector.setText(str(view.columns))
        view.xMinMaxVector.setText(f"1 - {view.xmax + 1}")
        view.yMinMaxVector.setText(f"1 - {view.ymax + 1}")
        view.zMinMaxVector.setText(f"1 - {view.zmax + 1}")

        view.vector_Table.clearContents()
        while view.vector_Table.rowCount() > 0:
            view.vector_Table.removeRow(0)
        for i in range(view.columns):
            col_values = [row[i] for row in view.vtk_data]
            view.vector_Table.insertRow(view.vector_Table.rowCount())
            view.vector_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(get_min(col_values))))
            view.vector_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(get_max(col_values))))
            view.vector_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(get_avg(col_values))))

        magnitudes = [
            math.sqrt(row[0] * row[0] + row[1] * row[1] + row[2] * row[2])
            for row in view.vtk_data
        ]
        if magnitudes:
            view.vectorValueMin_LE.setText(str(min(magnitudes)))
            view.vectorValueMax_LE.setText(str(max(magnitudes)))
            if max(magnitudes) != 0:
                view.vectorScale_LE.setText(str(5 / max(magnitudes)))

        index = view.vectorChoice.currentIndex()
        view.vectorName = (
            f"{view.vectorDir.absoluteFilePath()}.{3*index+1}{3*index+2}{3*index+3}.vtk"
        )
        view.updateVTK(view.scalarName, view.vectorName)
        view.vtk_data = []
    else:
        view.columns = 3
        view.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
        view.volume_CB.setCheckState(QtCore.Qt.Unchecked)
        view.vector_CB.setCheckState(QtCore.Qt.Checked)
        view.vectorGlyph_CB.setCheckState(QtCore.Qt.Checked)
        view.domain_CB.setCheckState(QtCore.Qt.Unchecked)
        view.vectorScale_LE.setText("1")
        view.vectorChoice.clear()
        view.vectorChoice.addItem("123")
        view.xmax = 10
        view.ymax = 10
        view.zmax = 10
        view.vectorName = file_path
        view.updateVTK(view.scalarName, view.vectorName)


def on_vector_choice_current_index_changed(view, index) -> None:
    if view.vectorChoice.count() <= 0:
        return
    try:
        index_value = int(index)
    except (TypeError, ValueError):
        index_value = view.vectorChoice.currentIndex()
    base = view.vectorDir.absoluteFilePath()
    if base:
        view.vectorName = (
            f"{base}.{3*index_value+1}{3*index_value+2}{3*index_value+3}.vtk"
        )
    view.updateFlag = False
    if view.stackedWidget.currentIndex() == 0 and view.vector_CB.isChecked():
        view.slotUpdate()


def slot_open_file_domain(view) -> None:
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(view, "Input", "", "Input (*.*)")
    if not file_path:
        return
    switch_control = view.domain_Combo.currentIndex()
    if switch_control == 0:
        domain_dialog = DomainCriteria(view)
        if domain_dialog.exec() == QtWidgets.QDialog.Accepted:
            view.domainStandardAngle = domain_dialog.getDomainStdAngle()
            view.domainStandardAngleRad = view.domainStandardAngle * PI_VALUE / 180.0
            view.domainStandardValue = domain_dialog.getDomainStdValue()
            view.domainStdAngle_LE.setText(str(view.domainStandardAngle))
            view.domainStdValue_LE.setText(str(view.domainStandardValue))

            view.columns = view.loadData(file_path)
            view.inputTab.setCurrentIndex(2)
            view.existDomain = [False] * 27
            file_info = QtCore.QFileInfo(file_path)
            view.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
            view.volume_CB.setCheckState(QtCore.Qt.Unchecked)
            view.vector_CB.setCheckState(QtCore.Qt.Unchecked)
            view.domain_CB.setCheckState(QtCore.Qt.Checked)
            view.domainDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

            view.outputDomain(view.domainDir.absoluteFilePath(), view.xmax, view.ymax, view.zmax)
            view.inputFileDomain.setText(file_info.fileName())
            view.rowcolDomain.setText(str(view.columns))
            view.xMinMaxDomain.setText(f"1 - {view.xmax + 1}")
            view.yMinMaxDomain.setText(f"1 - {view.ymax + 1}")
            view.zMinMaxDomain.setText(f"1 - {view.zmax + 1}")

            view.domain_Table.clearContents()
            while view.domain_Table.rowCount() > 0:
                view.domain_Table.removeRow(0)
            for i in range(view.columns):
                col_values = [row[i] for row in view.vtk_data]
                view.domain_Table.insertRow(view.domain_Table.rowCount())
                view.domain_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(get_min(col_values))))
                view.domain_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(get_max(col_values))))
                view.domain_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(get_avg(col_values))))

            view.domainName = f"{view.domainDir.absoluteFilePath()}.domain.vtk"
            view.drawDomain(view.domainName)
    elif switch_control == 1:
        vo2_dialog = VO2Criteria(view)
        if vo2_dialog.exec() == QtWidgets.QDialog.Accepted:
            view.M1mod = vo2_dialog.getM1_mod()
            view.M1ang = vo2_dialog.getM1_ang() * PI_VALUE / 180.0
            view.M2mod = vo2_dialog.getM2_mod()
            view.M2ang = vo2_dialog.getM2_ang() * PI_VALUE / 180.0
            view.vo2_M1_mod_LE.setText(str(view.M1mod))
            view.vo2_M1_ang_LE.setText(str(view.M1ang * 180.0 / PI_VALUE))
            view.vo2_M2_mod_LE.setText(str(view.M2mod))
            view.vo2_M2_ang_LE.setText(str(view.M2ang * 180.0 / PI_VALUE))
            view.columns = view.loadData(file_path)
            view.inputTab.setCurrentIndex(2)
            view.existDomain = [False] * 27
            file_info = QtCore.QFileInfo(file_path)
            view.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
            view.volume_CB.setCheckState(QtCore.Qt.Unchecked)
            view.vector_CB.setCheckState(QtCore.Qt.Unchecked)
            view.domain_CB.setCheckState(QtCore.Qt.Checked)
            view.domainDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

            view.outputVO2Domain(view.domainDir.absoluteFilePath(), view.xmax, view.ymax, view.zmax)
            view.domainName = f"{view.domainDir.absoluteFilePath()}.domain.vtk"
            view.drawVO2Domain(view.domainName)
