from __future__ import annotations

import os
from typing import Optional

import vtk

from color_utils import get_rgb


def update_vtk(view, scalarname: str, vectorname: str) -> None:
    fileNameScalar = scalarname
    fileNameVector = vectorname
    view._pointProbeScalarReader = None
    view._pointProbeScalarExtractor = None
    view._pointProbeScalarOutput = None
    view._pointProbeScalarColumn = None
    view._clear_point_probe_vector_dataset()

    renderer = vtk.vtkRenderer()
    if view.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
        view.qvtkWidget.GetRenderWindow().AddRenderer(renderer)
    else:
        renderer = view.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()

    scalar_range = [0.0, 0.0]
    vector_range = [0.0, 0.0]
    opacityScalar = vtk.vtkPiecewiseFunction()
    opacityVector = vtk.vtkPiecewiseFunction()
    colorScalar = vtk.vtkColorTransferFunction()
    colorVector = vtk.vtkColorTransferFunction()
    colorScalar.SetColorSpaceToLab()
    colorVector.SetColorSpaceToLab()
    vector_mapper = None
    ruler_extent: Optional[tuple[int, int, int, int, int, int]] = None

    renderer.SetBackground(0.9, 0.9, 0.9)
    renderer.AddActor(view.actorScalar)
    renderer.AddActor(view.actorVector)

    if fileNameScalar and os.path.isfile(fileNameScalar) and view.scalar_CB.isChecked():
        readerScalarOrigin = vtk.vtkStructuredPointsReader()
        readerScalarOrigin.SetFileName(fileNameScalar)
        readerScalarOrigin.Update()
        readerScalarOrigin.GetOutput().SetSpacing(
            float(view.rescaleX_LE.text() or 1),
            float(view.rescaleY_LE.text() or 1),
            float(view.rescaleZ_LE.text() or 1),
        )
        scalar_range = readerScalarOrigin.GetOutput().GetPointData().GetScalars().GetRange()

        readerScalar = vtk.vtkExtractVOI()
        readerScalar.SetInputConnection(readerScalarOrigin.GetOutputPort())
        scalar_extent = tuple(int(v) for v in readerScalarOrigin.GetOutput().GetExtent())
        if view.extract_CB.checkState():
            scalar_voi = view._get_clamped_extraction_voi(scalar_extent)
            readerScalar.SetVOI(*scalar_voi)
            ruler_extent = scalar_voi
        else:
            readerScalar.SetVOI(scalar_extent)
            ruler_extent = scalar_extent
        readerScalar.Update()
        view._pointProbeScalarReader = readerScalarOrigin
        view._pointProbeScalarExtractor = readerScalar
        view._pointProbeScalarOutput = readerScalar.GetOutput()
        view._pointProbeScalarColumn = view.scalarChoice.currentIndex() + 1 if view.scalarChoice.count() else 1

        if view.scalarRange_CB.isChecked():
            vmin = float(view.scalarValueMin_LE.text() or scalar_range[0])
            vmax = float(view.scalarValueMax_LE.text() or scalar_range[1])
            thresholdScalar = vtk.vtkThreshold()
            thresholdScalar.SetInputConnection(readerScalar.GetOutputPort())
            view._set_threshold_between(thresholdScalar, vmin, vmax)
            tetra = vtk.vtkDataSetTriangleFilter()
            tetra.SetInputConnection(thresholdScalar.GetOutputPort())
            mapperScalar = vtk.vtkUnstructuredGridVolumeRayCastMapper()
            mapperScalar.SetInputConnection(tetra.GetOutputPort())
            view.actorScalar.SetMapper(mapperScalar)
        else:
            mapperScalar = vtk.vtkSmartVolumeMapper()
            mapperScalar.SetInputConnection(readerScalar.GetOutputPort())
            mapperScalar.SetRequestedRenderModeToRayCast()
            view.actorScalar.SetMapper(mapperScalar)

        if view.isosurface_CB.isChecked():
            view.drawIsoSurface(readerScalar.GetOutputPort())

        if view.scalar_CB.checkState() == 0 or view.volume_CB.checkState() == 0:
            view.actorScalar.SetVisibility(False)
        else:
            view.actorScalar.SetVisibility(True)

        cutterScalar = vtk.vtkCutter()
        plane = vtk.vtkPlane()
        cutterScalar.SetInputConnection(readerScalar.GetOutputPort())
        if view.data2Dx or view.data2Dy or view.data2Dz:
            plane.SetOrigin(0, 0, 0)
            if view.data2Dx:
                plane.SetNormal(1, 0, 0)
            elif view.data2Dy:
                plane.SetNormal(0, 1, 0)
            else:
                plane.SetNormal(0, 0, 1)
            cutterScalar.SetCutFunction(plane)
            view.actorCutter.SetVisibility(True)
        else:
            plane.SetOrigin(
                float(view.sliceOriginX.text() or 0),
                float(view.sliceOriginY.text() or 0),
                float(view.sliceOriginZ.text() or 0),
            )
            plane.SetNormal(
                float(view.sliceNormalX.text() or 0),
                float(view.sliceNormalY.text() or 0),
                float(view.sliceNormalZ.text() or 1),
            )
            cutterScalar.SetCutFunction(plane)
            view.actorCutter.SetVisibility(bool(view.slice_CB.checkState()))

        cutterMapper = vtk.vtkPolyDataMapper()
        cutterMapper.SetInputConnection(cutterScalar.GetOutputPort())
        view.actorCutter.SetMapper(cutterMapper)
        renderer.AddActor(view.actorCutter)

        outlineScalar = vtk.vtkOutlineFilter()
        outlineScalar.SetInputConnection(readerScalar.GetOutputPort())
        outlineScalarMapper = vtk.vtkDataSetMapper()
        outlineScalarMapper.SetInputConnection(outlineScalar.GetOutputPort())
        view.outlineScalarActor.SetMapper(outlineScalarMapper)
        view.outlineScalarActor.GetProperty().SetColor(0, 0, 0)
        view.outlineScalarActor.GetProperty().SetLineWidth(view.outlineWidth)
        renderer.AddActor(view.outlineScalarActor)

    if fileNameVector and os.path.isfile(fileNameVector) and view.vector_CB.isChecked():
        if not view.updateFlag:
            view.readerVectorOrigin.ReadAllVectorsOn()
            view.readerVectorOrigin.SetFileName(fileNameVector)
        view.readerVectorOrigin.Update()
        view.readerVectorOrigin.GetOutput().SetSpacing(
            float(view.rescaleX_LE.text() or 1),
            float(view.rescaleY_LE.text() or 1),
            float(view.rescaleZ_LE.text() or 1),
        )
        vectors = view.readerVectorOrigin.GetOutput().GetPointData().GetVectors()
        if vectors is not None:
            vector_range = list(vectors.GetRange(-1))
        else:
            vector_range = [0.0, 0.0]
        view.readerVectorOrigin.GetOutput().GetPointData().SetActiveVectors("vector")

        readerVector = vtk.vtkExtractVOI()
        readerVector.SetInputConnection(view.readerVectorOrigin.GetOutputPort())
        readerVector.SetSampleRate(
            int(view.xDelta_LE.text() or 1),
            int(view.yDelta_LE.text() or 1),
            int(view.zDelta_LE.text() or 1),
        )
        vector_extent = tuple(int(v) for v in view.readerVectorOrigin.GetOutput().GetExtent())
        if view.extract_CB.checkState():
            vector_voi = view._get_clamped_extraction_voi(vector_extent)
            readerVector.SetVOI(*vector_voi)
            if ruler_extent is None:
                ruler_extent = vector_voi
        else:
            vector_voi = vector_extent
            readerVector.SetVOI(vector_extent)
            if ruler_extent is None:
                ruler_extent = vector_extent
        readerVector.Update()
        view._update_point_probe_vector_dataset(vector_voi)

        maskVector = vtk.vtkMaskPoints()
        maskVector.SetInputConnection(readerVector.GetOutputPort())
        if not view.vectorMaskNum_LE.text().strip():
            view.vectorMaskNum_LE.setText("5000")
        mask_num = int(float(view.vectorMaskNum_LE.text()))
        maskVector.SetMaximumNumberOfPoints(mask_num)
        if view.xmax and view.ymax and view.zmax:
            maskVector.SetOnRatio(max(1, int(view.xmax * view.ymax * view.zmax / mask_num)))
        maskVector.SetRandomMode(1)
        maskVector.Update()

        glyphVector = vtk.vtkGlyph3D()
        arrowVector = vtk.vtkArrowSource()
        translateHalf = vtk.vtkTransform()
        translateHalf.Translate(-0.5, 0, 0)
        glyphVector.SetSourceTransform(translateHalf)
        glyphVector.SetSourceConnection(arrowVector.GetOutputPort())
        if view.vectorRange_CB.isChecked():
            vector_range = [
                float(view.vectorValueMin_LE.text() or vector_range[0]),
                float(view.vectorValueMax_LE.text() or vector_range[1]),
            ]
            thresholdVector = vtk.vtkThresholdPoints()
            thresholdVector.SetInputConnection(maskVector.GetOutputPort())
            view._set_threshold_between(thresholdVector, vector_range[0], vector_range[1])
            glyphVector.SetInputConnection(thresholdVector.GetOutputPort())
        else:
            glyphVector.SetInputConnection(maskVector.GetOutputPort())
        glyphVector.SetInputArrayToProcess(1, 0, 0, 0, "vector")
        glyphVector.SetColorModeToColorByVector()
        glyphVector.OrientOn()
        glyphVector.SetVectorModeToUseVector()
        glyphVector.SetScaleModeToScaleByVector()
        glyphVector.SetScaleFactor(float(view.vectorScale_LE.text() or 1))
        glyphVector.Update()
        rgb_array = maskVector.GetOutput().GetPointData().GetArray("RGB")
        if rgb_array is not None and glyphVector.GetOutput().GetPointData().GetArray("RGB") is None:
            rgb_copy = vtk.vtkUnsignedCharArray()
            rgb_copy.DeepCopy(rgb_array)
            rgb_copy.SetName("RGB")
            glyphVector.GetOutput().GetPointData().AddArray(rgb_copy)

        mapperVector = vtk.vtkPolyDataMapper()
        mapperVector.SetInputConnection(glyphVector.GetOutputPort())
        mapperVector.ScalarVisibilityOn()
        mapperVector.SetScalarModeToUsePointFieldData()

        color_mode_index = view.vectorColorMode_Combo.currentIndex()
        if color_mode_index == 4:
            mapperVector.SelectColorArray("RGB")
            mapperVector.SetColorModeToDefault()
            colorVector.SetVectorModeToRGBColors()
        elif color_mode_index == 5:
            mapperVector.SelectColorArray("")
        else:
            mapperVector.SelectColorArray("GlyphVector")
            if color_mode_index == 0:
                colorVector.SetVectorModeToMagnitude()
            else:
                colorVector.SetVectorModeToComponent()
                colorVector.SetVectorComponent(color_mode_index - 1)

        if color_mode_index in (1, 2, 3):
            vector_index = view.vectorChoice.currentIndex()
            row = vector_index * 3 + color_mode_index - 1
            if 0 <= row < view.vector_Table.rowCount():
                min_item = view.vector_Table.item(row, 0)
                max_item = view.vector_Table.item(row, 1)
                if min_item is not None and max_item is not None:
                    vector_range = [float(min_item.text()), float(max_item.text())]

        mapperVector.SetLookupTable(colorVector)
        mapperVector.SetScalarRange(vector_range)
        mapperVector.Update()
        vector_mapper = mapperVector

        view.actorVector.SetMapper(mapperVector)
        view.actorVector.SetVisibility(view.vectorGlyph_CB.checkState() != 0)

        outlineVector = vtk.vtkOutlineFilter()
        outlineVector.SetInputConnection(readerVector.GetOutputPort())
        outlineVectorMapper = vtk.vtkDataSetMapper()
        outlineVectorMapper.SetInputConnection(outlineVector.GetOutputPort())
        view.outlineVectorActor.SetMapper(outlineVectorMapper)
        view.outlineVectorActor.GetProperty().SetColor(0, 0, 0)
        view.outlineVectorActor.GetProperty().SetLineWidth(view.outlineWidth)
        renderer.AddActor(view.outlineVectorActor)

        if view.streamline_CB.isChecked():
            vectorSeed = vtk.vtkPointSource()
            vectorSeed.SetCenter(
                float(view.seedCenterX_LE.text() or 0),
                float(view.seedCenterY_LE.text() or 0),
                float(view.seedCenterZ_LE.text() or 0),
            )
            vectorSeed.SetNumberOfPoints(int(float(view.seedNumber_LE.text() or 10)))
            vectorSeed.SetRadius(float(view.seedRadius_LE.text() or 1))
            stream = vtk.vtkStreamTracer()
            stream.SetSourceConnection(vectorSeed.GetOutputPort())
            stream.SetInputConnection(readerVector.GetOutputPort())
            stream.SetMaximumPropagation(float(view.streamStepLength_LE.text() or 1))
            stream.SetIntegrationDirectionToForward()
            streamMapper = vtk.vtkDataSetMapper()
            streamMapper.SetInputConnection(stream.GetOutputPort())
            view.actorStream.SetMapper(streamMapper)
            renderer.AddActor(view.actorStream)

    if view.alpha_Combo.currentIndex() == 0:
        opacityScalar.AddPoint(scalar_range[0], 1.0)
        opacityScalar.AddPoint((scalar_range[0] + scalar_range[1]) / 2, 0)
        opacityScalar.AddPoint(scalar_range[1], 1.0)
        opacityVector.AddPoint(vector_range[0], 1.0)
        opacityVector.AddPoint((vector_range[0] + vector_range[1]) / 2, 0)
        opacityVector.AddPoint(vector_range[1], 1.0)
    else:
        for i in range(view.alphaScalar_Table.rowCount()):
            value = float(view.alphaScalar_Table.item(i, 0).text())
            alpha = float(view.alphaScalar_Table.item(i, 1).text())
            opacityScalar.AddPoint(value, alpha)
        for i in range(view.alphaVector_Table.rowCount()):
            value = float(view.alphaVector_Table.item(i, 0).text())
            alpha = float(view.alphaVector_Table.item(i, 1).text())
            opacityVector.AddPoint(value, alpha)

    if view.RGB_Combo.currentIndex() == 0:
        colorScalar.AddRGBPoint(scalar_range[0], 0.0, 0.0, 1.0)
        colorScalar.AddRGBPoint((scalar_range[0] + scalar_range[1]) / 2, 0, 1, 0)
        colorScalar.AddRGBPoint(scalar_range[1], 1.0, 0.0, 0.0)
        colorVector.AddRGBPoint(vector_range[0], 0.0, 0.0, 1.0)
        colorVector.AddRGBPoint((vector_range[0] + vector_range[1]) / 2, 0, 1, 0)
        colorVector.AddRGBPoint(vector_range[1], 1.0, 0.0, 0.0)
    else:
        for i in range(view.RGBScalar_Table.rowCount()):
            rgb_value = float(view.RGBScalar_Table.item(i, 0).text())
            r = float(view.RGBScalar_Table.item(i, 1).text()) / 255
            g = float(view.RGBScalar_Table.item(i, 2).text()) / 255
            b = float(view.RGBScalar_Table.item(i, 3).text()) / 255
            colorScalar.AddRGBPoint(rgb_value, r, g, b)
        for i in range(view.RGBVector_Table.rowCount()):
            rgb_value = float(view.RGBVector_Table.item(i, 0).text())
            r = float(view.RGBVector_Table.item(i, 1).text()) / 255
            g = float(view.RGBVector_Table.item(i, 2).text()) / 255
            b = float(view.RGBVector_Table.item(i, 3).text()) / 255
            colorVector.AddRGBPoint(rgb_value, r, g, b)
    colorScalar.Build()
    colorVector.Build()
    if vector_mapper is not None:
        vector_mapper.SetLookupTable(colorVector)
        vector_mapper.SetScalarRange(vector_range)
        vector_mapper.Update()

    if view.volume_CB.checkState():
        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetScalarOpacity(opacityScalar)
        volume_property.SetColor(colorScalar)
        volume_property.SetInterpolationTypeToNearest()
        view.actorScalar.SetProperty(volume_property)

    view.widget.SetOutlineColor(0.93, 0.57, 0.13)
    view.widget.SetOrientationMarker(view.axes)
    view.widget.SetInteractor(view.qvtkWidget.GetRenderWindow().GetInteractor())
    view.widget.SetViewport(0.0, 0.0, 0.2, 0.2)
    view.widget.SetEnabled(1)
    view.widget.InteractiveOn()

    view.scalarScaleBarActor.SetLookupTable(colorScalar)
    view.scalarScaleBarActor.SetTitle(view.scalarLegend_LE.text())
    view.scalarScaleBarActor.SetNumberOfLabels(3)
    view.scalarScaleBarActor.SetMaximumWidthInPixels(80)
    view.scalarScaleBarActor.GetTitleTextProperty().SetColor(0, 0, 0)
    view.scalarScaleBarActor.GetTitleTextProperty().SetJustificationToLeft()
    view.scalarScaleBarActor.GetLabelTextProperty().SetColor(0, 0, 0)
    view.scalarScaleBarActor.DrawTickLabelsOn()
    view.scalarScaleBarActor.UseOpacityOn()
    view.scalarLegendWidget.SetInteractor(view.qvtkWidget.GetRenderWindow().GetInteractor())
    view.scalarLegendWidget.SetScalarBarActor(view.scalarScaleBarActor)
    view.scalarLegendWidget.ResizableOn()
    view.scalarLegendWidget.On()

    vectorRT = vtk.vtkRTAnalyticSource()
    vectorRTContour = vtk.vtkContourFilter()
    vectorRTMapper = vtk.vtkPolyDataMapper()
    vectorRTLookupTable = vtk.vtkLookupTable()
    rgb = vtk.vtkUnsignedCharArray()
    vectorRT.SetWholeExtent(-10, 10, -10, 10, -10, 10)
    vectorRT.SetCenter(0, 0, 0)
    vectorRT.SetXFreq(0)
    vectorRT.SetYFreq(0)
    vectorRT.SetZFreq(0)
    vectorRT.SetXMag(10)
    vectorRT.SetYMag(10)
    vectorRT.SetZMag(10)
    vectorRT.Update()
    vectorRTContour.SetInputConnection(vectorRT.GetOutputPort())
    vectorRTContour.SetValue(0, 200)
    vectorRTContour.ComputeNormalsOn()
    vectorRTContour.Update()
    rgb.SetNumberOfComponents(3)
    rgb.SetName("RGB1")
    normals = vectorRTContour.GetOutput().GetPointData().GetNormals()
    if normals is not None:
        for i in range(normals.GetNumberOfTuples()):
            normal = normals.GetTuple(i)
            rgb_value = get_rgb(normal[0], normal[1], normal[2], [0, 1], [-1, 1])
            rgb.InsertNextTuple3(
                int(rgb_value[0]),
                int(rgb_value[1]),
                int(rgb_value[2]),
            )
    vectorRTContour.GetOutput().GetPointData().AddArray(rgb)
    vectorRTContour.Update()

    vectorContourAssign = vtk.vtkAssignAttribute()
    vectorContourAssign.SetInputConnection(vectorRTContour.GetOutputPort())
    vectorContourAssign.Assign(
        "RGB1",
        vtk.vtkDataSetAttributes.VECTORS,
        vtk.vtkAssignAttribute.POINT_DATA,
    )
    vectorContourAssign.Update()

    vectorRTLookupTable.SetVectorModeToRGBColors()
    vectorRTLookupTable.Build()
    vectorRTMapper.SetInputConnection(vectorContourAssign.GetOutputPort())
    vectorRTMapper.SetScalarModeToUsePointFieldData()
    vectorRTMapper.SetColorModeToDefault()
    vectorRTMapper.SetLookupTable(vectorRTLookupTable)
    vectorRTMapper.ScalarVisibilityOn()
    vectorRTMapper.SelectColorArray("RGB1")
    vectorRTMapper.Update()
    view.vectorRTActor.SetMapper(vectorRTMapper)
    view.vectorOrientationLegend.SetOutlineColor(0.93, 0.57, 0.13)
    view.vectorOrientationLegend.SetOrientationMarker(view.vectorRTActor)
    view.vectorOrientationLegend.SetInteractor(view.qvtkWidget.GetRenderWindow().GetInteractor())
    view.vectorOrientationLegend.SetViewport(0.8, 0.4, 1.0, 0.6)
    view.vectorOrientationLegend.SetEnabled(1)
    view.vectorOrientationLegend.InteractiveOn()

    view.vectorScaleBarActor.SetLookupTable(colorVector)
    view.vectorScaleBarActor.SetTitle(view.vectorLegend_LE.text())
    view.vectorScaleBarActor.SetNumberOfLabels(3)
    view.vectorScaleBarActor.SetMaximumWidthInPixels(80)
    view.vectorScaleBarActor.GetTitleTextProperty().SetColor(0, 0, 0)
    view.vectorScaleBarActor.GetLabelTextProperty().SetColor(0, 0, 0)
    view.vectorScaleBarActor.UseOpacityOn()
    view.vectorLegendWidget.SetInteractor(view.qvtkWidget.GetRenderWindow().GetInteractor())
    view.vectorLegendWidget.SetScalarBarActor(view.vectorScaleBarActor)
    view.vectorLegendWidget.On()

    if view.outline_CB.checkState():
        view.outlineScalarActor.SetVisibility(view.scalar_CB.checkState() != 0)
        view.outlineVectorActor.SetVisibility(view.vector_CB.checkState() != 0)
    else:
        view.outlineScalarActor.SetVisibility(False)
        view.outlineVectorActor.SetVisibility(False)

    if view.axis_CB.checkState():
        view.widget.On()
    else:
        view.widget.Off()

    if view.scalarLegendBar_CB.checkState():
        view.scalarLegendWidget.On()
        view.scalarScaleBarActor.SetVisibility(True)
    else:
        view.scalarLegendWidget.Off()
        view.scalarScaleBarActor.SetVisibility(False)

    if view.vectorLegendBar_CB.checkState():
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

    view._update_coordinate_ruler(renderer, ruler_extent)

    if view.reset:
        view.updateCamera(-1)
        view.reset = False
    else:
        view.updateCamera(0)

    view._refresh_point_probe_source()
    if view.pointProbe_CB is not None and view.pointProbe_CB.isChecked():
        view._set_point_probe_hint()
