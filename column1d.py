from typing import List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from plot_widget import QCPScatterStyle


class Column1D(QtWidgets.QWidget):
    figureReplot = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        ui_path = QtCore.QDir.current().absoluteFilePath("ui/column1D.ui")
        uic.loadUi(ui_path, self)
        QtCore.QMetaObject.connectSlotsByName(self)
        self.ui = self

        self.loaded = False
        self.vtkData: List[List[float]] = []
        self.dataFiltered: List[List[float]] = []
        self.columns = 0
        self.rows = 0
        self.xmin1D = 1.0
        self.xmax1D = 0.0
        self.ymin1D = 1.0
        self.ymax1D = 0.0

        self.scatterStyleList = [
            QCPScatterStyle.ssNone,
            QCPScatterStyle.ssDot,
            QCPScatterStyle.ssCross,
            QCPScatterStyle.ssPlus,
            QCPScatterStyle.ssCircle,
            QCPScatterStyle.ssDisc,
            QCPScatterStyle.ssSquare,
            QCPScatterStyle.ssDiamond,
            QCPScatterStyle.ssStar,
            QCPScatterStyle.ssTriangle,
            QCPScatterStyle.ssTriangleInverted,
            QCPScatterStyle.ssCrossSquare,
            QCPScatterStyle.ssPlusSquare,
            QCPScatterStyle.ssCrossCircle,
            QCPScatterStyle.ssPlusCircle,
        ]
        self.lineStyleList = [
            QtCore.Qt.SolidLine,
            QtCore.Qt.DashLine,
            QtCore.Qt.DotLine,
            QtCore.Qt.DashDotLine,
            QtCore.Qt.DashDotDotLine,
        ]
        self.lineStyle: List[QtGui.QPen] = []
        self.scatterStyle: List[int] = []
        self.lineName: List[str] = []

        self.plot1DFileX_Combo.setView(QtWidgets.QListView())
        self.plot1DFile_Table.setColumnWidth(0, 60)
        self.plot1DFile_Table.setColumnWidth(1, 60)
        self.plot1DFile_Table.setColumnWidth(2, 60)
        self.plot1DRelationFile_Table.setColumnWidth(0, 60)
        self.plot1DRelationFile_Table.setColumnWidth(1, 60)
        self.plot1DRelationFile_Table.setColumnWidth(2, 60)

    def getColumns(self) -> int:
        return self.columns

    def returnX(self) -> List[float]:
        data_rows = len(self.dataFiltered)
        col_x = self.plot1DFileX_Combo.currentIndex()
        if data_rows > 0:
            self.xmin1D = self.dataFiltered[0][col_x]
            self.xmax1D = self.dataFiltered[0][col_x]
        x_vals: List[float] = []
        for row in self.dataFiltered:
            value = row[col_x]
            x_vals.append(value)
            if value <= self.xmin1D:
                self.xmin1D = value
            if value >= self.xmax1D:
                self.xmax1D = value
        return x_vals

    def returnXMin(self) -> float:
        return self.xmin1D

    def returnXMax(self) -> float:
        return self.xmax1D

    def returnY(self, col_y: int) -> List[float]:
        data_rows = len(self.dataFiltered)
        if data_rows > 0:
            self.ymin1D = self.dataFiltered[0][col_y]
            self.ymax1D = self.dataFiltered[0][col_y]
        y_vals: List[float] = []
        for row in self.dataFiltered:
            value = row[col_y]
            y_vals.append(value)
            if value <= self.ymin1D:
                self.ymin1D = value
            if value >= self.ymax1D:
                self.ymax1D = value
        return y_vals

    def returnYMin(self) -> float:
        return self.ymin1D

    def returnYMax(self) -> float:
        return self.ymax1D

    def filter(self) -> int:
        self.dataFiltered = [row for row in self.vtkData if self.filter1DData(row)]
        return len(self.dataFiltered)

    def getFilteredCount(self) -> int:
        if self.loaded:
            self.filter()
            return len(self.dataFiltered)
        return 0

    def on_load1DFile_PB_clicked(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Input", "", "Input (*.*)")
        if not file_path:
            return
        self.columns = self.loadData1D(file_path)
        self.loaded = True

        while self.plot1DFileX_Combo.count() > 0:
            self.plot1DFileX_Combo.removeItem(0)
        for i in range(self.columns):
            self.plot1DFileX_Combo.addItem(str(i + 1))

        self.plot1DFileY_LW.clear()
        for i in range(self.columns):
            item = QtWidgets.QListWidgetItem(str(i + 1))
            item.setFlags(
                QtCore.Qt.ItemIsUserCheckable
                | QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
            )
            item.setCheckState(QtCore.Qt.Unchecked)
            self.plot1DFileY_LW.addItem(item)
        self.plot1DFileY_LW.sortItems()

        self.plot1DRelationFile_Combo.setEnabled(True)
        self.plot1DRelationValueFile_LE.setEnabled(True)

        while self.plot1DColFile_Combo.count() > 0:
            self.plot1DColFile_Combo.removeItem(0)
        for i in range(self.columns):
            self.plot1DColFile_Combo.addItem(str(i + 1))

        self.plot1DLines_LW.clear()
        while self.plot1DRelationFile_Table.rowCount() > 0:
            self.plot1DRelationFile_Table.removeRow(0)

        file_info = QtCore.QFileInfo(file_path)
        self.plot1DFileName_LE.setText(file_info.fileName())
        self.plot1DFileColNum_LE.setText(str(self.columns))

        self.plot1DFile_Table.clearContents()
        while self.plot1DFile_Table.rowCount() > 0:
            self.plot1DFile_Table.removeRow(0)
        for i in range(self.columns):
            column_values = [row[i] for row in self.vtkData]
            row = self.plot1DFile_Table.rowCount()
            self.plot1DFile_Table.insertRow(row)
            self.plot1DFile_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(self.getMin(column_values))))
            self.plot1DFile_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(self.getMax(column_values))))
            self.plot1DFile_Table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(self.getAvg(column_values))))

        self.figureReplot.emit()

    def loadData1D(self, filedir: str) -> int:
        with open(filedir, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if len(lines) < 2:
            self.vtkData = []
            self.rows = 0
            return 0

        line1 = lines[0].split()
        line2 = lines[1].split()
        count1 = len(line1)
        count2 = len(line2)
        column_number = count2
        skip_first = False
        if count1 != count2:
            skip_first = True
        else:
            try:
                first_value = float(line1[0])
                if first_value == 0:
                    skip_first = True
            except ValueError:
                skip_first = True

        data_lines = lines[1:] if skip_first else lines
        self.rows = len(data_lines)
        self.vtkData = []
        for line in data_lines:
            tokens = line.split()
            row: List[float] = []
            for i in range(column_number):
                value = 0.0
                if i < len(tokens):
                    try:
                        value = float(tokens[i])
                    except ValueError:
                        value = 0.0
                row.append(value)
            self.vtkData.append(row)
        self.columns = column_number
        return column_number

    def filter1DData(self, data: List[float]) -> bool:
        for i in range(self.plot1DRelationFile_Table.rowCount()):
            col_item = self.plot1DRelationFile_Table.item(i, 0)
            rel_item = self.plot1DRelationFile_Table.item(i, 1)
            value_item = self.plot1DRelationFile_Table.item(i, 2)
            if not col_item or not rel_item or not value_item:
                continue
            relation_col = int(col_item.text()) - 1
            relation = rel_item.text()
            value = float(value_item.text())
            if relation == "=" and data[relation_col] != value:
                return False
            if relation == ">" and data[relation_col] <= value:
                return False
            if relation == ">=" and data[relation_col] < value:
                return False
            if relation == "<" and data[relation_col] >= value:
                return False
            if relation == "<=" and data[relation_col] > value:
                return False
        return True

    def on_plot1DAddRelationFile_PB_released(self) -> None:
        if self.plot1DColFile_Combo.count() == 0 or not self.plot1DRelationValueFile_LE.text():
            return
        row = self.plot1DRelationFile_Table.rowCount()
        self.plot1DRelationFile_Table.insertRow(row)
        self.plot1DRelationFile_Table.setItem(
            row, 0, QtWidgets.QTableWidgetItem(self.plot1DColFile_Combo.currentText())
        )
        self.plot1DRelationFile_Table.setItem(
            row, 1, QtWidgets.QTableWidgetItem(self.plot1DRelationFile_Combo.currentText())
        )
        self.plot1DRelationFile_Table.setItem(
            row, 2, QtWidgets.QTableWidgetItem(self.plot1DRelationValueFile_LE.text())
        )
        self.plot1DRelationFile_Table.sortItems(0, QtCore.Qt.AscendingOrder)
        self.figureReplot.emit()

    def on_plot1DFileY_LW_itemClicked(self, item: QtWidgets.QListWidgetItem) -> None:
        if item.checkState():
            self.plot1DLines_LW.addItem(item.text())
            self.lineStyle.append(QtGui.QPen())
            self.scatterStyle.append(0)
            self.lineName.append("")
            self.plot1DLines_LW.setCurrentItem(
                self.plot1DLines_LW.findItems(item.text(), QtCore.Qt.MatchExactly)[0]
            )
            self.plot1DLineRGBR_LE.setText("0")
            self.plot1DLineRGBG_LE.setText("0")
            self.plot1DLineRGBB_LE.setText("0")
            self.plot1DLineWeight_LE.setText("2")
            self.plot1DScatterStyle_Combo.setCurrentIndex(0)
            self.plot1DLineStyle_Combo.setCurrentIndex(0)
            self.plot1DLineName_LE.setText(f"line{len(self.lineStyle)}")
            self.on_plot1DSetLine_PB_released()
        else:
            items = self.plot1DLines_LW.findItems(item.text(), QtCore.Qt.MatchExactly)
            if items:
                rownum = self.plot1DLines_LW.row(items[0])
                self.plot1DLines_LW.takeItem(rownum)
                if rownum < len(self.lineName):
                    self.lineName.pop(rownum)
                    self.lineStyle.pop(rownum)
                    self.scatterStyle.pop(rownum)
        self.plot1DSetLine_PB.setEnabled(self.plot1DLines_LW.count() > 0)
        self.figureReplot.emit()

    def on_plot1DSetLine_PB_released(self) -> None:
        if not self.plot1DLines_LW.currentItem():
            return
        index = self.plot1DLines_LW.currentRow()
        if index < 0 or index >= len(self.lineStyle):
            return
        r = int(float(self.plot1DLineRGBR_LE.text() or 0))
        g = int(float(self.plot1DLineRGBG_LE.text() or 0))
        b = int(float(self.plot1DLineRGBB_LE.text() or 0))
        weight = int(float(self.plot1DLineWeight_LE.text() or 1))
        pen = QtGui.QPen(QtGui.QColor(r, g, b))
        pen.setWidth(weight)
        pen.setStyle(self.lineStyleList[self.plot1DLineStyle_Combo.currentIndex()])
        self.lineStyle[index] = pen
        self.scatterStyle[index] = self.plot1DScatterStyle_Combo.currentIndex()
        self.lineName[index] = self.plot1DLineName_LE.text()
        self.figureReplot.emit()

    def on_plot1DLines_LW_currentRowChanged(self, row_num: int) -> None:
        if row_num == -1 or row_num >= len(self.lineStyle):
            return
        pen = self.lineStyle[row_num]
        color = pen.color()
        self.plot1DLineRGBR_LE.setText(str(color.red()))
        self.plot1DLineRGBG_LE.setText(str(color.green()))
        self.plot1DLineRGBB_LE.setText(str(color.blue()))
        self.plot1DLineWeight_LE.setText(str(pen.width()))
        self.plot1DScatterStyle_Combo.setCurrentIndex(self.scatterStyle[row_num])
        style_index = 0
        if pen.style() in self.lineStyleList:
            style_index = self.lineStyleList.index(pen.style())
        self.plot1DLineStyle_Combo.setCurrentIndex(style_index)
        self.plot1DLineName_LE.setText(self.lineName[row_num])

    def on_plot1DRemoveRelationFile_PB_released(self) -> None:
        if self.plot1DRelationFile_Table.rowCount() > 0:
            self.plot1DRelationFile_Table.removeRow(self.plot1DRelationFile_Table.currentRow())
            self.figureReplot.emit()

    def getLineStyle(self, row_number: int) -> QtGui.QPen:
        if 0 <= row_number < len(self.lineStyle):
            return self.lineStyle[row_number]
        return QtGui.QPen()

    def getScatterStyle(self, row_number: int) -> str:
        if 0 <= row_number < len(self.scatterStyle):
            return self.scatterStyleList[self.scatterStyle[row_number]]
        return QCPScatterStyle.ssNone

    def getLineName(self, row_number: int) -> str:
        if 0 <= row_number < len(self.lineName):
            return self.lineName[row_number]
        return ""

    def getMin(self, values: List[float]) -> float:
        return min(values) if values else 0.0

    def getMax(self, values: List[float]) -> float:
        return max(values) if values else 0.0

    def getAvg(self, values: List[float]) -> float:
        return sum(values) / float(len(values)) if values else 0.0

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        painter = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, painter, self)


class column1D(Column1D):
    pass


import sys

sys.modules.setdefault("column1D", sys.modules[__name__])
