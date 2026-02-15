from PyQt5 import QtCore, QtWidgets


def output_status(view, file_info: QtCore.QFileInfo) -> None:
    with open(file_info.absoluteFilePath(), "w", encoding="utf-8") as f:
        f.write(f"{int(view.outline_CB.checkState())} {view.outlineWidth_LE.text()}\n")
        f.write(f"{int(view.axis_CB.checkState())}\n")
        f.write(f"{int(view.extract_CB.checkState())}\n")
        f.write(f"{view.xmin_LE.text()} {view.xmax_LE.text()} {view.xDelta_LE.text()}\n")
        f.write(f"{view.ymin_LE.text()} {view.ymax_LE.text()} {view.yDelta_LE.text()}\n")
        f.write(f"{view.zmin_LE.text()} {view.zmax_LE.text()} {view.zDelta_LE.text()}\n")
        f.write(f"{view.rescaleX_LE.text()} {view.rescaleY_LE.text()} {view.rescaleZ_LE.text()}\n")
        f.write(
            f"{view.cameraPositionX_LE.text()} {view.cameraPositionY_LE.text()} {view.cameraPositionZ_LE.text()}\n"
        )
        f.write(
            f"{view.cameraFocalX_LE.text()} {view.cameraFocalY_LE.text()} {view.cameraFocalZ_LE.text()}\n"
        )
        f.write(
            f"{view.cameraViewUpX_LE.text()} {view.cameraViewUpY_LE.text()} {view.cameraViewUpZ_LE.text()}\n"
        )
        f.write(f"{view.viewportSizeX.text()} {view.viewportSizeY.text()} {view.exportRatio.text()}\n")

        f.write(f"{view.RGB_Combo.currentIndex()}\n")
        f.write(f"{view.RGBScalar_Table.rowCount()}\n")
        for i in range(view.RGBScalar_Table.rowCount()):
            f.write(
                f"{view.RGBScalar_Table.item(i,0).text()} {view.RGBScalar_Table.item(i,1).text()} "
                f"{view.RGBScalar_Table.item(i,2).text()} {view.RGBScalar_Table.item(i,3).text()}\n"
            )
        f.write(f"{view.RGBVector_Table.rowCount()}\n")
        for i in range(view.RGBVector_Table.rowCount()):
            f.write(
                f"{view.RGBVector_Table.item(i,0).text()} {view.RGBVector_Table.item(i,1).text()} "
                f"{view.RGBVector_Table.item(i,2).text()} {view.RGBVector_Table.item(i,3).text()}\n"
            )
        f.write(f"{view.RGBIso_Table.rowCount()}\n")
        for i in range(view.RGBIso_Table.rowCount()):
            f.write(
                f"{view.RGBIso_Table.item(i,0).text()} {view.RGBIso_Table.item(i,1).text()} "
                f"{view.RGBIso_Table.item(i,2).text()} {view.RGBIso_Table.item(i,3).text()}\n"
            )
        f.write(f"{view.RGBDomain_Table.rowCount()}\n")
        for i in range(view.RGBDomain_Table.rowCount()):
            index = view.RGBDomain_Combo.findText(view.RGBDomain_Table.item(i, 0).text())
            f.write(
                f"{index} {view.RGBDomain_Table.item(i,1).text()} "
                f"{view.RGBDomain_Table.item(i,2).text()} {view.RGBDomain_Table.item(i,3).text()}\n"
            )

        f.write(f"{view.alpha_Combo.currentIndex()}\n")
        f.write(f"{view.alphaScalar_Table.rowCount()}\n")
        for i in range(view.alphaScalar_Table.rowCount()):
            f.write(
                f"{view.alphaScalar_Table.item(i,0).text()} {view.alphaScalar_Table.item(i,1).text()}\n"
            )
        f.write(f"{view.alphaDomain_Table.rowCount()}\n")
        for i in range(view.alphaDomain_Table.rowCount()):
            index = view.domainAlpha_Combo.findText(view.alphaDomain_Table.item(i, 0).text())
            f.write(f"{index} {view.alphaDomain_Table.item(i,1).text()}\n")

        f.write(f"{int(view.scalar_CB.checkState())}\n")
        f.write(f"{view.scalarChoice.count()} {view.scalarChoice.currentIndex()}\n")
        f.write(f"{int(view.scalarLegendBar_CB.checkState())} {view.scalarLegend_LE.text()}\n")
        f.write(f"{int(view.volume_CB.checkState())}\n")
        f.write(f"{int(view.scalarRange_CB.checkState())}\n")
        f.write(f"{view.scalarValueMin_LE.text()} {view.scalarValueMax_LE.text()}\n")
        f.write(f"{int(view.slice_CB.checkState())}\n")
        f.write(f"{view.sliceOriginX.text()} {view.sliceOriginY.text()} {view.sliceOriginZ.text()}\n")
        f.write(f"{view.sliceNormalX.text()} {view.sliceNormalY.text()} {view.sliceNormalZ.text()}\n")
        f.write(f"{int(view.isosurface_CB.checkState())}\n")
        f.write(f"{view.isosurface_LW.count()}\n")
        for i in range(view.isosurface_LW.count()):
            item = view.isosurface_LW.item(i)
            f.write(f"{item.text()} {int(item.checkState())}\n")

        f.write(f"{int(view.vector_CB.checkState())}\n")
        f.write(f"{view.vectorChoice.count()} {view.vectorChoice.currentIndex()}\n")
        f.write(f"{view.vectorColorMode_Combo.currentIndex()}\n")
        f.write(f"{int(view.vectorLegendBar_CB.checkState())} {view.vectorLegend_LE.text()}\n")
        f.write(f"{int(view.vectorGlyph_CB.checkState())}\n")
        f.write(f"{view.vectorMaskNum_LE.text()}\n")
        f.write(f"{view.vectorScale_LE.text()}\n")
        f.write(f"{int(view.vectorRange_CB.checkState())}\n")
        f.write(f"{view.vectorValueMin_LE.text()} {view.vectorValueMax_LE.text()}\n")
        f.write(f"{int(view.streamline_CB.checkState())}\n")
        f.write(f"{view.seedNumber_LE.text()}\n")
        f.write(f"{view.seedRadius_LE.text()}\n")
        f.write(f"{view.seedCenterX_LE.text()} {view.seedCenterY_LE.text()} {view.seedCenterZ_LE.text()}\n")
        f.write(f"{view.streamStepLength_LE.text()}\n")

        f.write(f"{int(view.domain_CB.checkState())}\n")
        for i in range(view.domain_TW.rowCount()):
            f.write(f"{int(view.domain_TW.item(i,0).checkState())}\n")
        f.write(f"{view.domainStdAngle_LE.text()} {view.domainStdValue_LE.text()}\n")
        f.write(f"{view.domain_Combo.currentIndex()}\n")
        for i in range(view.vo2Domain_LW.count()):
            f.write(f"{int(view.vo2Domain_LW.item(i).checkState())}\n")
        f.write(f"{view.vo2_M1_mod_LE.text()} {view.vo2_M1_ang_LE.text()}\n")
        f.write(f"{view.vo2_M2_mod_LE.text()} {view.vo2_M2_ang_LE.text()}\n")
        if view.coordRuler_CB is not None:
            f.write(f"{int(view.coordRuler_CB.checkState())}\n")
        if view.pointProbe_CB is not None:
            f.write(f"{int(view.pointProbe_CB.checkState())}\n")


def slot_output_status(view) -> None:
    file_path, _ = QtWidgets.QFileDialog.getSaveFileName(view, "Save file", "", "Status (*.txt)")
    if file_path:
        view.outputStatus(QtCore.QFileInfo(file_path))


def load_status(view, file_info: QtCore.QFileInfo) -> None:
    with open(file_info.absoluteFilePath(), "r", encoding="utf-8") as f:
        data = f.read().split()
    if not data:
        return
    it = iter(data)

    view.outline_CB.setCheckState(int(next(it)))
    view.outlineWidth_LE.setText(next(it))
    view.axis_CB.setCheckState(int(next(it)))
    view.extract_CB.setCheckState(int(next(it)))
    view.xmin_LE.setText(next(it))
    view.xmax_LE.setText(next(it))
    view.xDelta_LE.setText(next(it))
    view.ymin_LE.setText(next(it))
    view.ymax_LE.setText(next(it))
    view.yDelta_LE.setText(next(it))
    view.zmin_LE.setText(next(it))
    view.zmax_LE.setText(next(it))
    view.zDelta_LE.setText(next(it))
    view.rescaleX_LE.setText(next(it))
    view.rescaleY_LE.setText(next(it))
    view.rescaleZ_LE.setText(next(it))
    view.cameraPositionX_LE.setText(next(it))
    view.cameraPositionY_LE.setText(next(it))
    view.cameraPositionZ_LE.setText(next(it))
    view.cameraFocalX_LE.setText(next(it))
    view.cameraFocalY_LE.setText(next(it))
    view.cameraFocalZ_LE.setText(next(it))
    view.cameraViewUpX_LE.setText(next(it))
    view.cameraViewUpY_LE.setText(next(it))
    view.cameraViewUpZ_LE.setText(next(it))
    view.viewportSizeX.setText(next(it))
    view.viewportSizeY.setText(next(it))
    view.exportRatio.setText(next(it))

    view.RGB_Combo.setCurrentIndex(int(next(it)))
    count = int(next(it))
    view.RGBScalar_Table.setRowCount(0)
    for i in range(count):
        value = next(it)
        r = next(it)
        g = next(it)
        b = next(it)
        view.RGBScalar_Table.insertRow(i)
        view.RGBScalar_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
        view.RGBScalar_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
        view.RGBScalar_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
        view.RGBScalar_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

    count = int(next(it))
    view.RGBVector_Table.setRowCount(0)
    for i in range(count):
        value = next(it)
        r = next(it)
        g = next(it)
        b = next(it)
        view.RGBVector_Table.insertRow(i)
        view.RGBVector_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
        view.RGBVector_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
        view.RGBVector_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
        view.RGBVector_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

    count = int(next(it))
    view.RGBIso_Table.setRowCount(0)
    for i in range(count):
        value = next(it)
        r = next(it)
        g = next(it)
        b = next(it)
        view.RGBIso_Table.insertRow(i)
        view.RGBIso_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
        view.RGBIso_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
        view.RGBIso_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
        view.RGBIso_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

    count = int(next(it))
    view.RGBDomain_Table.setRowCount(0)
    for i in range(count):
        value = next(it)
        r = next(it)
        g = next(it)
        b = next(it)
        view.RGBDomain_Table.insertRow(i)
        view.RGBDomain_Table.setItem(
            i, 0, QtWidgets.QTableWidgetItem(view.RGBDomain_Combo.itemText(int(value)))
        )
        view.RGBDomain_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
        view.RGBDomain_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
        view.RGBDomain_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

    view.alpha_Combo.setCurrentIndex(int(next(it)))
    count = int(next(it))
    view.alphaScalar_Table.setRowCount(0)
    for i in range(count):
        value = next(it)
        a = next(it)
        view.alphaScalar_Table.insertRow(i)
        view.alphaScalar_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
        view.alphaScalar_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(a))

    count = int(next(it))
    view.alphaDomain_Table.setRowCount(0)
    for i in range(count):
        value = next(it)
        a = next(it)
        view.alphaDomain_Table.insertRow(i)
        view.alphaDomain_Table.setItem(
            i, 0, QtWidgets.QTableWidgetItem(view.domainAlpha_Combo.itemText(int(value)))
        )
        view.alphaDomain_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(a))

    view.scalar_CB.setCheckState(int(next(it)))
    _count = int(next(it))
    index = int(next(it))
    view.scalarChoice.setCurrentIndex(index)
    view.scalarColumn = index
    view.scalarLegendBar_CB.setCheckState(int(next(it)))
    view.scalarLegend_LE.setText(next(it))
    view.volume_CB.setCheckState(int(next(it)))
    view.scalarRange_CB.setCheckState(int(next(it)))
    view.scalarValueMin_LE.setText(next(it))
    view.scalarValueMax_LE.setText(next(it))
    view.slice_CB.setCheckState(int(next(it)))
    view.sliceOriginX.setText(next(it))
    view.sliceOriginY.setText(next(it))
    view.sliceOriginZ.setText(next(it))
    view.sliceNormalX.setText(next(it))
    view.sliceNormalY.setText(next(it))
    view.sliceNormalZ.setText(next(it))
    view.isosurface_CB.setCheckState(int(next(it)))
    iso_count = int(next(it))
    while view.isosurface_LW.count() > 0:
        view.isosurface_LW.setCurrentRow(0)
        view.on_isoDelete_PB_released()
    for _ in range(iso_count):
        value = next(it)
        checkstate = int(next(it))
        view.isoValue_LE.setText(value)
        view.on_isoAdd_PB_released()
        item = view.isosurface_LW.item(view.isosurface_LW.count() - 1)
        item.setCheckState(checkstate)

    view.vector_CB.setCheckState(int(next(it)))
    _count = int(next(it))
    index = int(next(it))
    view.vectorChoice.setCurrentIndex(index)
    view.vectorColumn = index
    view.vectorColorMode_Combo.setCurrentIndex(int(next(it)))
    view.vectorLegendBar_CB.setCheckState(int(next(it)))
    view.vectorLegend_LE.setText(next(it))
    view.vectorGlyph_CB.setCheckState(int(next(it)))
    view.vectorMaskNum_LE.setText(next(it))
    view.vectorScale_LE.setText(next(it))
    view.vectorRange_CB.setCheckState(int(next(it)))
    view.vectorValueMin_LE.setText(next(it))
    view.vectorValueMax_LE.setText(next(it))
    view.streamline_CB.setCheckState(int(next(it)))
    view.seedNumber_LE.setText(next(it))
    view.seedRadius_LE.setText(next(it))
    view.seedCenterX_LE.setText(next(it))
    view.seedCenterY_LE.setText(next(it))
    view.seedCenterZ_LE.setText(next(it))
    view.streamStepLength_LE.setText(next(it))

    view.domain_CB.setCheckState(int(next(it)))
    for i in range(view.domain_TW.rowCount()):
        view.domain_TW.item(i, 0).setCheckState(int(next(it)))
    view.domainStdAngle_LE.setText(next(it))
    view.domainStdValue_LE.setText(next(it))
    view.domain_Combo.setCurrentIndex(int(next(it)))
    for i in range(view.vo2Domain_LW.count()):
        view.vo2Domain_LW.item(i).setCheckState(int(next(it)))
    view.vo2_M1_mod_LE.setText(next(it))
    view.vo2_M1_ang_LE.setText(next(it))
    view.vo2_M2_mod_LE.setText(next(it))
    view.vo2_M2_ang_LE.setText(next(it))
    try:
        coord_ruler_state = int(next(it))
    except StopIteration:
        coord_ruler_state = 0
    if view.coordRuler_CB is not None:
        view.coordRuler_CB.setCheckState(coord_ruler_state)
    try:
        point_probe_state = int(next(it))
    except StopIteration:
        point_probe_state = 0
    if view.pointProbe_CB is not None:
        view.pointProbe_CB.setCheckState(point_probe_state)


def slot_load_status(view) -> str:
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(view, "Status input", "", "Status input (*.*)")
    if file_path:
        view.loadStatus(QtCore.QFileInfo(file_path))
    return file_path
