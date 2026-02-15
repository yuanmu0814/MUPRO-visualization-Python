from PyQt5 import QtGui, QtWidgets
import vtk


def save_image(view) -> None:
    file_path, _ = QtWidgets.QFileDialog.getSaveFileName(view, "Save file", "", "Images (*.png)")
    if not file_path:
        return
    if view.stackedWidget.currentIndex() == 0:
        view.outputImage(file_path)
    else:
        target_w = view._safe_positive_int(view.viewportSizeX.text(), 2000)
        target_h = view._safe_positive_int(view.viewportSizeY.text(), 2000)
        magnify = view._safe_positive_int(view.exportRatio.text(), 1)
        view.customPlot.savePng(file_path, target_w * magnify, target_h * magnify, 600)


def save_scene(view) -> None:
    file_path, _ = QtWidgets.QFileDialog.getSaveFileName(view, "Save file", "", "Images (*.x3d)")
    if not file_path:
        return
    if view.stackedWidget.currentIndex() == 0:
        exporter = vtk.vtkX3DExporter()
        exporter.SetInput(view.qvtkWidget.GetRenderWindow())
        exporter.SetFileName(file_path)
        exporter.Update()
        exporter.Write()


def output_image(view, load: str) -> None:
    render_window = view.qvtkWidget.GetRenderWindow()
    render_window.Render()
    view.qvtkWidget.update()
    QtWidgets.QApplication.processEvents()

    target_w = view._safe_positive_int(view.viewportSizeX.text(), 2000)
    target_h = view._safe_positive_int(view.viewportSizeY.text(), 2000)
    magnify = view._safe_positive_int(view.exportRatio.text(), 1)
    current_w, current_h = render_window.GetSize()
    fit_w, fit_h = view._fit_export_size_to_view_aspect(
        current_w,
        current_h,
        target_w,
        target_h,
    )
    out_w = max(1, fit_w * magnify)
    out_h = max(1, fit_h * magnify)
    original_w, original_h = render_window.GetSize()

    try:
        render_window.SetSize(out_w, out_h)
        render_window.Render()
        QtWidgets.QApplication.processEvents()

        window_to_image = vtk.vtkWindowToImageFilter()
        window_to_image.SetInput(render_window)
        window_to_image.SetScale(1)
        window_to_image.SetInputBufferTypeToRGBA()
        window_to_image.FixBoundaryOff()
        window_to_image.ReadFrontBufferOff()
        window_to_image.ShouldRerenderOn()
        window_to_image.UpdateWholeExtent()

        writer = vtk.vtkPNGWriter()
        writer.SetFileName(load)
        writer.SetInputConnection(window_to_image.GetOutputPort())
        render_window.Render()
        window_to_image.Modified()
        writer.Write()
        view._apply_png_dpi(load, 600)
    finally:
        render_window.SetSize(original_w, original_h)
        render_window.Render()
        view.qvtkWidget.update()


def apply_png_dpi(path: str, dpi: int = 600) -> None:
    image = QtGui.QImage(path)
    if image.isNull():
        return
    dots_per_meter = int(round(dpi / 0.0254))
    image.setDotsPerMeterX(dots_per_meter)
    image.setDotsPerMeterY(dots_per_meter)
    image.save(path, "PNG")


def on_camera_set_pb_released(view) -> None:
    try:
        position_x = float(view.cameraPositionX_LE.text())
        position_y = float(view.cameraPositionY_LE.text())
        position_z = float(view.cameraPositionZ_LE.text())
        focal_x = float(view.cameraFocalX_LE.text())
        focal_y = float(view.cameraFocalY_LE.text())
        focal_z = float(view.cameraFocalZ_LE.text())
        view_x = float(view.cameraViewUpX_LE.text())
        view_y = float(view.cameraViewUpY_LE.text())
        view_z = float(view.cameraViewUpZ_LE.text())
    except ValueError:
        return
    view.camera.SetPosition(position_x, position_y, position_z)
    view.camera.SetFocalPoint(focal_x, focal_y, focal_z)
    view.camera.SetViewUp(view_x, view_y, view_z)
    view.updateCamera(0)


def on_camera_get_pb_released(view) -> None:
    pos = view.camera.GetPosition()
    focal = view.camera.GetFocalPoint()
    up = view.camera.GetViewUp()
    view.cameraPositionX_LE.setText(str(pos[0]))
    view.cameraPositionY_LE.setText(str(pos[1]))
    view.cameraPositionZ_LE.setText(str(pos[2]))
    view.cameraFocalX_LE.setText(str(focal[0]))
    view.cameraFocalY_LE.setText(str(focal[1]))
    view.cameraFocalZ_LE.setText(str(focal[2]))
    view.cameraViewUpX_LE.setText(str(up[0]))
    view.cameraViewUpY_LE.setText(str(up[1]))
    view.cameraViewUpZ_LE.setText(str(up[2]))
