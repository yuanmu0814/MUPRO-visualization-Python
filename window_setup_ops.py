import os
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets
import vtk


def init_renderer(view) -> None:
    if view.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
        renderer = vtk.vtkRenderer()
        view.qvtkWidget.GetRenderWindow().AddRenderer(renderer)
    else:
        renderer = view.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()
    renderer.SetBackground(0.9, 0.9, 0.9)
    if not renderer.HasViewProp(view.coordRulerActor):
        renderer.AddActor(view.coordRulerActor)
    view.coordRulerActor.SetCamera(renderer.GetActiveCamera())
    view.coordRulerActor.VisibilityOff()
    view.qvtkWidget.GetRenderWindow().Render()
    view.qvtkWidget.update()


def apply_icons(view) -> None:
    icon_dir = QtCore.QDir.current().absoluteFilePath("Icons")

    def icon_path(name: str) -> str:
        return QtCore.QDir.toNativeSeparators(os.path.join(icon_dir, name))

    def set_action_icon(action: Optional[QtWidgets.QAction], filename: str) -> None:
        if action is not None:
            action.setIcon(QtGui.QIcon(icon_path(filename)))

    set_action_icon(view.actionOpenFile_scalar, "scalar-open.png")
    set_action_icon(view.actionOpenFile_vector, "vector-open.png")
    set_action_icon(view.actionOpenFile_domain, "domain-open.png")
    set_action_icon(view.actionPrint, "print.png")
    set_action_icon(view.actionRefresh, "refresh.png")
    set_action_icon(view.actionSave, "filesave.png")
    set_action_icon(view.actionRotateToXP, "x+.png")
    set_action_icon(view.actionRotateToXN, "X-.png")
    set_action_icon(view.actionRotateToYP, "Y+.png")
    set_action_icon(view.actionRotateToYN, "Y-.png")
    set_action_icon(view.actionRotateToZP, "Z+.png")
    set_action_icon(view.actionRotateToZN, "Z-.png")
    set_action_icon(view.actionClear, "clear-icon.png")
    set_action_icon(view.action3D, "3d.png")
    set_action_icon(view.action1D, "1D.png")
    set_action_icon(view.actionOutputStatus, "outputStatus.png")
    set_action_icon(view.actionLoadStatus, "loadStatus.png")
    set_action_icon(view.actionBatch3D, "batch3D.png")
    set_action_icon(view.actionExportX3D, "x3d.png")

    if hasattr(view, "toolBar"):
        view.toolBar.setIconSize(QtCore.QSize(22, 22))
        view.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)

    view.setWindowIcon(QtGui.QIcon(icon_path("mupro-logo-new.png")))
