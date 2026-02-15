import os


def on_axis_cb_state_changed(view, state: int) -> None:
    if state:
        view.widget.On()
    else:
        view.widget.Off()
    view.qvtkWidget.GetRenderWindow().Render()


def on_coord_ruler_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    if (
        enabled
        and view.stackedWidget.currentIndex() == 0
        and (
            (view.scalarName and os.path.isfile(view.scalarName))
            or (view.vectorName and os.path.isfile(view.vectorName))
            or (view.domainName and os.path.isfile(view.domainName))
        )
    ):
        view.slotUpdate()
        return
    view.coordRulerActor.SetVisibility(enabled and view.stackedWidget.currentIndex() == 0)
    view.qvtkWidget.GetRenderWindow().Render()


def on_point_probe_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    if not enabled:
        view._reset_point_probe_display()
        return
    view._refresh_point_probe_source()
    view._set_point_probe_hint()


def on_outline_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    if view.scalar_CB.checkState():
        view.outlineScalarActor.SetVisibility(enabled)
    else:
        view.outlineScalarActor.SetVisibility(False)
    if view.vector_CB.checkState():
        view.outlineVectorActor.SetVisibility(enabled)
    else:
        view.outlineVectorActor.SetVisibility(False)
    if view.domain_CB.checkState():
        view.outlineDomainActor.SetVisibility(enabled)
    view.outlineWidth_LB.setEnabled(enabled)
    view.outlineWidth_LE.setEnabled(enabled)
    view.outlinePx_LB.setEnabled(enabled)
    view.qvtkWidget.GetRenderWindow().Render()


def on_scalar_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.scalarChoice.setEnabled(enabled)
    view.volume_CB.setEnabled(enabled)
    view.scalarColumn_LB.setEnabled(enabled)
    view.slice_CB.setEnabled(enabled)
    view.isosurface_CB.setEnabled(enabled)
    view.scalarLegendBar_CB.setEnabled(enabled)
    view.scalarLegend_LE.setEnabled(enabled)
    view.scalarRange_CB.setEnabled(False)
    view.scalarValueMin_LE.setEnabled(False)
    view.scalarValueMax_LE.setEnabled(False)
    view.scalarTo_LB.setEnabled(False)
    view.slicePoint_LB.setEnabled(False)
    view.sliceNormal_LB.setEnabled(False)
    view.sliceNormalX.setEnabled(False)
    view.sliceNormalY.setEnabled(False)
    view.sliceNormalZ.setEnabled(False)
    view.sliceOriginX.setEnabled(False)
    view.sliceOriginY.setEnabled(False)
    view.sliceOriginZ.setEnabled(False)
    view.isoValue_LB.setEnabled(False)
    view.isoValue_LE.setEnabled(False)
    view.isoAdd_PB.setEnabled(False)
    view.isoDelete_PB.setEnabled(False)
    view.isosurfaces_LB.setEnabled(False)
    view.isosurface_LW.setEnabled(False)

    if enabled:
        if view.volume_CB.isChecked():
            view.scalarRange_CB.setEnabled(True)
            if view.scalarRange_CB.isChecked():
                view.scalarValueMin_LE.setEnabled(True)
                view.scalarValueMax_LE.setEnabled(True)
                view.scalarTo_LB.setEnabled(True)
        if view.slice_CB.isChecked():
            view.slicePoint_LB.setEnabled(True)
            view.sliceNormal_LB.setEnabled(True)
            view.sliceNormalX.setEnabled(True)
            view.sliceNormalY.setEnabled(True)
            view.sliceNormalZ.setEnabled(True)
            view.sliceOriginX.setEnabled(True)
            view.sliceOriginY.setEnabled(True)
            view.sliceOriginZ.setEnabled(True)
        if view.isosurface_CB.isChecked():
            view.isoValue_LB.setEnabled(True)
            view.isoValue_LE.setEnabled(True)
            view.isoAdd_PB.setEnabled(True)
            view.isoDelete_PB.setEnabled(True)
            view.isosurfaces_LB.setEnabled(True)
            view.isosurface_LW.setEnabled(True)

    if state == 0 or view.volume_CB.checkState() == 0:
        view.actorScalar.SetVisibility(False)
    else:
        view.actorScalar.SetVisibility(True)
    view.qvtkWidget.GetRenderWindow().Render()


def on_volume_cb_state_changed(view, state: int) -> None:
    if state == 0:
        view.scalarRange_CB.setEnabled(False)
        view.scalarValueMin_LE.setEnabled(False)
        view.scalarValueMax_LE.setEnabled(False)
        view.scalarTo_LB.setEnabled(False)
    else:
        view.scalarRange_CB.setEnabled(True)
        if view.scalarRange_CB.isChecked():
            view.scalarValueMin_LE.setEnabled(True)
            view.scalarValueMax_LE.setEnabled(True)
            view.scalarTo_LB.setEnabled(True)
        else:
            view.scalarValueMin_LE.setEnabled(False)
            view.scalarValueMax_LE.setEnabled(False)
            view.scalarTo_LB.setEnabled(False)
    if state == 0 or view.scalar_CB.checkState() == 0:
        view.actorScalar.SetVisibility(False)
    else:
        view.actorScalar.SetVisibility(True)
    view.qvtkWidget.GetRenderWindow().Render()


def on_vector_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.vectorChoice.setEnabled(enabled)
    view.vector_LB.setEnabled(enabled)
    view.vectorGlyph_CB.setEnabled(enabled)
    view.streamline_CB.setEnabled(enabled)
    view.vectorLegend_LE.setEnabled(enabled)
    view.vectorLegendBar_CB.setEnabled(enabled)
    view.vectorColorMode_Combo.setEnabled(enabled)
    view.vectorColorMode_LB.setEnabled(enabled)

    if not enabled:
        view.vectorValueMin_LE.setEnabled(False)
        view.vectorValueMax_LE.setEnabled(False)
        view.vectorTo_LB.setEnabled(False)
        view.vectorMaskNum_LE.setEnabled(False)
        view.vectorMaxPoints_LB.setEnabled(False)
        view.vectorScale_LB.setEnabled(False)
        view.vectorScale_LE.setEnabled(False)
        view.vectorRange_CB.setEnabled(False)
        view.streamStepLength_LE.setEnabled(False)
        view.seedNumber_LE.setEnabled(False)
        view.seedRadius_LE.setEnabled(False)
        view.seedCenterX_LE.setEnabled(False)
        view.seedCenterY_LE.setEnabled(False)
        view.seedCenterZ_LE.setEnabled(False)
        view.streamSeedNum_LB.setEnabled(False)
        view.streamSeedCenter_LB.setEnabled(False)
        view.streamMaxLength_LB.setEnabled(False)
        view.streamSampleRadius_LB.setEnabled(False)
        view.xDelta_LE.setEnabled(False)
        view.yDelta_LE.setEnabled(False)
        view.zDelta_LE.setEnabled(False)
        view.xDelta_LB.setEnabled(False)
        view.yDelta_LB.setEnabled(False)
        view.zDelta_LB.setEnabled(False)
        view.sampleRate_LB.setEnabled(False)
    else:
        if view.vectorGlyph_CB.isChecked():
            view.vectorMaskNum_LE.setEnabled(True)
            view.vectorMaxPoints_LB.setEnabled(True)
            view.vectorScale_LB.setEnabled(True)
            view.vectorScale_LE.setEnabled(True)
            view.vectorRange_CB.setEnabled(True)
            view.xDelta_LE.setEnabled(True)
            view.yDelta_LE.setEnabled(True)
            view.zDelta_LE.setEnabled(True)
            view.xDelta_LB.setEnabled(True)
            view.yDelta_LB.setEnabled(True)
            view.zDelta_LB.setEnabled(True)
            view.sampleRate_LB.setEnabled(True)
            if view.vectorRange_CB.isChecked():
                view.vectorValueMin_LE.setEnabled(True)
                view.vectorValueMax_LE.setEnabled(True)
                view.vectorTo_LB.setEnabled(True)
            else:
                view.vectorValueMin_LE.setEnabled(False)
                view.vectorValueMax_LE.setEnabled(False)
                view.vectorTo_LB.setEnabled(False)
        else:
            view.vectorMaskNum_LE.setEnabled(False)
            view.vectorMaxPoints_LB.setEnabled(False)
            view.vectorScale_LB.setEnabled(False)
            view.vectorScale_LE.setEnabled(False)
            view.vectorRange_CB.setEnabled(False)
            view.vectorValueMin_LE.setEnabled(False)
            view.vectorValueMax_LE.setEnabled(False)
            view.vectorTo_LB.setEnabled(False)

        if view.streamline_CB.isChecked():
            view.streamStepLength_LE.setEnabled(True)
            view.seedNumber_LE.setEnabled(True)
            view.seedRadius_LE.setEnabled(True)
            view.seedCenterX_LE.setEnabled(True)
            view.seedCenterY_LE.setEnabled(True)
            view.seedCenterZ_LE.setEnabled(True)
            view.streamSeedNum_LB.setEnabled(True)
            view.streamSeedCenter_LB.setEnabled(True)
            view.streamMaxLength_LB.setEnabled(True)
            view.streamSampleRadius_LB.setEnabled(True)
        else:
            view.streamStepLength_LE.setEnabled(False)
            view.seedNumber_LE.setEnabled(False)
            view.seedRadius_LE.setEnabled(False)
            view.seedCenterX_LE.setEnabled(False)
            view.seedCenterY_LE.setEnabled(False)
            view.seedCenterZ_LE.setEnabled(False)
            view.streamSeedNum_LB.setEnabled(False)
            view.streamSeedCenter_LB.setEnabled(False)
            view.streamMaxLength_LB.setEnabled(False)
            view.streamSampleRadius_LB.setEnabled(False)

    if state == 0:
        view.actorVector.SetVisibility(False)
    else:
        view.actorVector.SetVisibility(True)
    view.qvtkWidget.GetRenderWindow().Render()


def on_vector_glyph_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.vectorMaskNum_LE.setEnabled(enabled)
    view.vectorMaxPoints_LB.setEnabled(enabled)
    view.vectorScale_LB.setEnabled(enabled)
    view.vectorScale_LE.setEnabled(enabled)
    view.vectorRange_CB.setEnabled(enabled)
    view.xDelta_LE.setEnabled(enabled)
    view.yDelta_LE.setEnabled(enabled)
    view.zDelta_LE.setEnabled(enabled)
    view.xDelta_LB.setEnabled(enabled)
    view.yDelta_LB.setEnabled(enabled)
    view.zDelta_LB.setEnabled(enabled)
    view.sampleRate_LB.setEnabled(enabled)
    if enabled and view.vectorRange_CB.isChecked():
        view.vectorValueMin_LE.setEnabled(True)
        view.vectorValueMax_LE.setEnabled(True)
        view.vectorTo_LB.setEnabled(True)
    else:
        view.vectorValueMin_LE.setEnabled(False)
        view.vectorValueMax_LE.setEnabled(False)
        view.vectorTo_LB.setEnabled(False)
    if state == 0 or view.vector_CB.checkState() == 0:
        view.actorVector.SetVisibility(False)
    else:
        view.actorVector.SetVisibility(True)
    view.qvtkWidget.GetRenderWindow().Render()


def on_vector_range_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.vectorValueMin_LE.setEnabled(enabled)
    view.vectorValueMax_LE.setEnabled(enabled)
    view.vectorTo_LB.setEnabled(enabled)


def on_streamline_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.streamStepLength_LE.setEnabled(enabled)
    view.seedNumber_LE.setEnabled(enabled)
    view.seedRadius_LE.setEnabled(enabled)
    view.seedCenterX_LE.setEnabled(enabled)
    view.seedCenterY_LE.setEnabled(enabled)
    view.seedCenterZ_LE.setEnabled(enabled)
    view.streamSeedNum_LB.setEnabled(enabled)
    view.streamSeedCenter_LB.setEnabled(enabled)
    view.streamMaxLength_LB.setEnabled(enabled)
    view.streamSampleRadius_LB.setEnabled(enabled)
    view.actorStream.SetVisibility(enabled)
    view.qvtkWidget.GetRenderWindow().Render()


def on_extract_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.xmin_LE.setEnabled(enabled)
    view.xmax_LE.setEnabled(enabled)
    view.ymin_LE.setEnabled(enabled)
    view.ymax_LE.setEnabled(enabled)
    view.zmin_LE.setEnabled(enabled)
    view.zmax_LE.setEnabled(enabled)


def refresh_after_extraction_edit(view) -> None:
    if view.stackedWidget.currentIndex() != 0 or not view.extract_CB.isChecked():
        return
    has_visual_data = (
        (view.scalar_CB.isChecked() and view.scalarName and os.path.isfile(view.scalarName))
        or (view.vector_CB.isChecked() and view.vectorName and os.path.isfile(view.vectorName))
        or (view.domain_CB.isChecked() and view.domainName and os.path.isfile(view.domainName))
    )
    if has_visual_data:
        view.slotUpdate()


def on_scalar_range_cb_state_changed(view, state: int) -> None:
    enabled = bool(state)
    view.scalarValueMin_LE.setEnabled(enabled)
    view.scalarValueMax_LE.setEnabled(enabled)
    view.scalarTo_LB.setEnabled(enabled)


def on_scalar_legend_bar_cb_state_changed(view, state: int) -> None:
    if state:
        view.scalarLegendWidget.On()
        view.scalarScaleBarActor.SetVisibility(True)
    else:
        view.scalarLegendWidget.Off()
        view.scalarScaleBarActor.SetVisibility(False)
    view.qvtkWidget.GetRenderWindow().Render()


def on_vector_legend_bar_cb_state_changed(view, state: int) -> None:
    if state:
        if view.vectorColorMode_Combo.currentIndex() == 4:
            view.vectorOrientationLegend.On()
            view.vectorRTActor.SetVisibility(True)
            view.vectorLegendWidget.Off()
            view.vectorScaleBarActor.SetVisibility(False)
        else:
            view.vectorLegendWidget.On()
            view.vectorScaleBarActor.SetVisibility(True)
            view.vectorOrientationLegend.Off()
            view.vectorRTActor.SetVisibility(False)
    else:
        view.vectorLegendWidget.Off()
        view.vectorOrientationLegend.Off()
        view.vectorRTActor.SetVisibility(False)
        view.vectorScaleBarActor.SetVisibility(False)
    view.qvtkWidget.GetRenderWindow().Render()
