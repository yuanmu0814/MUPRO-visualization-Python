from __future__ import annotations

import math
import os
import sys
from typing import List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets, uic
try:
    from PyQt5 import QtUiTools
except ImportError:
    QtUiTools = None

import vtk

from plot_widget import QCustomPlot, QCPPlotTitle
from column1d import Column1D
from domain_criteria import DomainCriteria
from vo2_criteria import VO2Criteria
from batch3d import Batch3D

PI_VALUE = 3.141592653589


if QtUiTools is not None:
    class _UiLoader(QtUiTools.QUiLoader):
        def __init__(self, baseinstance: Optional[QtWidgets.QWidget] = None, custom_widgets=None):
            super().__init__(baseinstance)
            self._baseinstance = baseinstance
            self._custom_widgets = custom_widgets or {}

        def createWidget(self, class_name, parent=None, name=""):
            if self._baseinstance is not None and parent is None:
                return self._baseinstance
            if class_name in self._custom_widgets:
                widget = self._custom_widgets[class_name](parent)
            else:
                widget = super().createWidget(class_name, parent, name)
            if self._baseinstance is not None:
                setattr(self._baseinstance, name, widget)
            return widget
else:
    _UiLoader = None


class SimpleView(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ui_path = QtCore.QDir.toNativeSeparators(
            QtCore.QDir.current().absoluteFilePath("ui/SimpleView.ui")
        )

        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

        if _UiLoader is not None:
            custom_widgets = {
                "QVTKWidget": QVTKRenderWindowInteractor,
                "QCustomPlot": QCustomPlot,
                "column1D": Column1D,
            }
            loader = _UiLoader(self, custom_widgets=custom_widgets)
            ui_file = QtCore.QFile(ui_path)
            ui_file.open(QtCore.QFile.ReadOnly)
            loader.load(ui_file, self)
            ui_file.close()
        else:
            uic.loadUi(ui_path, self)

        QtCore.QMetaObject.connectSlotsByName(self)
        self.ui = self

        self.scalar = False
        self.vector = False
        self.domain = False

        self.tempX = 0
        self.tempY = 0
        self.tempZ = 0
        self.scalarColumn = 0
        self.vectorColumn = 0

        self.columns = 0
        self.scalarName = ""
        self.vectorName = ""
        self.domainName = ""
        self.scalarDir = QtCore.QFileInfo()
        self.vectorDir = QtCore.QFileInfo()
        self.domainDir = QtCore.QFileInfo()

        self.domainRGB: List[List[float]] = [[0.0, 0.0, 0.0] for _ in range(27)]
        self.domainRGBHold: List[List[float]] = [[0.0, 0.0, 0.0] for _ in range(27)]
        self.vo2DomainRGB: List[List[float]] = [[0.0, 0.0, 0.0] for _ in range(9)]
        self.vo2DomainRGBHold: List[List[float]] = [[0.0, 0.0, 0.0] for _ in range(9)]
        self.domainList: List[str] = []
        self.vo2DomainList: List[str] = []
        self.existDomain: List[bool] = [False] * 27
        self.pointFraction: List[float] = [0.0] * 27

        self.vtk_data: List[List[float]] = []
        self.updateFlag = False

        self.camera = vtk.vtkCamera()
        self.axes = vtk.vtkAxesActor()
        self.axes.SetScale(10)
        self.axes.SetTotalLength(10, 10, 10)

        self.outlineScalarActor = vtk.vtkActor()
        self.outlineVectorActor = vtk.vtkActor()
        self.outlineDomainActor = vtk.vtkActor()
        self.actorIsosurface = vtk.vtkActor()
        self.actorCutter = vtk.vtkActor()
        self.actorVector = vtk.vtkActor()
        self.actorStream = vtk.vtkActor()
        self.vectorRTActor = vtk.vtkActor()
        self.actorScalar = vtk.vtkVolume()
        self.coordRulerActor = vtk.vtkCubeAxesActor()

        self.actorDomain = [vtk.vtkActor() for _ in range(27)]
        self.actorIso: List[vtk.vtkActor] = []

        self.widget = vtk.vtkOrientationMarkerWidget()
        self.vectorOrientationLegend = vtk.vtkOrientationMarkerWidget()
        self.scalarLegendWidget = vtk.vtkScalarBarWidget()
        self.vectorLegendWidget = vtk.vtkScalarBarWidget()
        self.scalarScaleBarActor = vtk.vtkScalarBarActor()
        self.vectorScaleBarActor = vtk.vtkScalarBarActor()
        self.coordRuler_CB: Optional[QtWidgets.QCheckBox] = None
        self.pointProbe_CB: Optional[QtWidgets.QCheckBox] = None
        self.pointProbeCoordValue_LB: Optional[QtWidgets.QLabel] = None
        self.pointProbeIndexValue_LB: Optional[QtWidgets.QLabel] = None
        self.pointProbeDataValue_LB: Optional[QtWidgets.QLabel] = None
        self.pointProbeSourceValue_LB: Optional[QtWidgets.QLabel] = None
        self._pointProbeObserverTag: Optional[int] = None
        self._pointProbeStyleObserverTag: Optional[int] = None
        self._pointProbePicker = vtk.vtkCellPicker()
        self._pointProbeWorldPicker = vtk.vtkWorldPointPicker()
        self._pointProbePicker.SetTolerance(0.0005)
        self._pointProbeScalarReader: Optional[vtk.vtkStructuredPointsReader] = None
        self._pointProbeScalarExtractor: Optional[vtk.vtkExtractVOI] = None
        self._pointProbeScalarOutput: Optional[vtk.vtkImageData] = None
        self._pointProbeScalarColumn: Optional[int] = None
        self._pointProbeVectorExtractor: Optional[vtk.vtkExtractVOI] = None
        self._pointProbeVectorOutput: Optional[vtk.vtkImageData] = None
        self._pointProbeVectorColumns: Optional[str] = None
        self._middlePanObserverPressTag: Optional[int] = None
        self._middlePanObserverReleaseTag: Optional[int] = None
        self._middlePanObserverMoveTag: Optional[int] = None
        self._middlePanActive = False
        self._middlePanCamera: Optional[vtk.vtkCamera] = None
        self._middlePanViewDirection: Optional[tuple[float, float, float]] = None
        self._middlePanViewUp: Optional[tuple[float, float, float]] = None

        self.readerVectorOrigin = vtk.vtkStructuredPointsReader()

        self.reset = True
        self.data2Dx = False
        self.data2Dy = False
        self.data2Dz = False

        self.xmin = 0
        self.xmax = 0
        self.ymin = 0
        self.ymax = 0
        self.zmin = 0
        self.zmax = 0
        self.xminAll = 0
        self.xmaxAll = 0
        self.yminAll = 0
        self.ymaxAll = 0
        self.zminAll = 0
        self.zmaxAll = 0
        self.outlineWidth = 1

        self.domainStandardValue = 0.3
        self.domainStandardAngle = 180.0
        self.domainStandardAngleRad = 180.0 * PI_VALUE / 180.0
        self.M1mod = 0.1
        self.M2mod = 0.1
        self.M1ang = 10.0 * PI_VALUE / 180.0
        self.M2ang = 10.0 * PI_VALUE / 180.0

        self.coordRulerActor.SetXTitle("X")
        self.coordRulerActor.SetYTitle("Y")
        self.coordRulerActor.SetZTitle("Z")
        self.coordRulerActor.SetXLabelFormat("%g")
        self.coordRulerActor.SetYLabelFormat("%g")
        self.coordRulerActor.SetZLabelFormat("%g")
        self.coordRulerActor.SetFlyModeToOuterEdges()
        self.coordRulerActor.SetXAxisRange(1.0, 1.0)
        self.coordRulerActor.SetYAxisRange(1.0, 1.0)
        self.coordRulerActor.SetZAxisRange(1.0, 1.0)
        ruler_color = (0.25, 0.25, 0.25)
        self.coordRulerActor.GetXAxesLinesProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetYAxesLinesProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetZAxesLinesProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetXAxesLabelProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetYAxesLabelProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetZAxesLabelProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetXAxesTitleProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetYAxesTitleProperty().SetColor(*ruler_color)
        self.coordRulerActor.GetZAxesTitleProperty().SetColor(*ruler_color)
        self.coordRulerActor.VisibilityOff()

        self.domainOrth = [
            [0, 0, 0],
            [1 / math.sqrt(3), 1 / math.sqrt(3), 1 / math.sqrt(3)],
            [-1 / math.sqrt(3), -1 / math.sqrt(3), -1 / math.sqrt(3)],
            [-1 / math.sqrt(3), 1 / math.sqrt(3), 1 / math.sqrt(3)],
            [1 / math.sqrt(3), -1 / math.sqrt(3), -1 / math.sqrt(3)],
            [-1 / math.sqrt(3), -1 / math.sqrt(3), 1 / math.sqrt(3)],
            [1 / math.sqrt(3), 1 / math.sqrt(3), -1 / math.sqrt(3)],
            [1 / math.sqrt(3), -1 / math.sqrt(3), 1 / math.sqrt(3)],
            [-1 / math.sqrt(3), 1 / math.sqrt(3), -1 / math.sqrt(3)],
            [1 / math.sqrt(2), 1 / math.sqrt(2), 0],
            [-1 / math.sqrt(2), -1 / math.sqrt(2), 0],
            [1 / math.sqrt(2), -1 / math.sqrt(2), 0],
            [-1 / math.sqrt(2), 1 / math.sqrt(2), 0],
            [1 / math.sqrt(2), 0, 1 / math.sqrt(2)],
            [-1 / math.sqrt(2), 0, -1 / math.sqrt(2)],
            [1 / math.sqrt(2), 0, -1 / math.sqrt(2)],
            [-1 / math.sqrt(2), 0, 1 / math.sqrt(2)],
            [0, 1 / math.sqrt(2), 1 / math.sqrt(2)],
            [0, -1 / math.sqrt(2), -1 / math.sqrt(2)],
            [0, 1 / math.sqrt(2), -1 / math.sqrt(2)],
            [0, -1 / math.sqrt(2), 1 / math.sqrt(2)],
            [1, 0, 0],
            [-1, 0, 0],
            [0, 1, 0],
            [0, -1, 0],
            [0, 0, 1],
            [0, 0, -1],
        ]

        self._setup_ui()
        self._init_renderer()
        self._apply_icons()
        self._init_domain_colors()
        self._init_vo2_colors()

        self.camera.SetPosition(100, 100, 100)
        self.camera.SetFocalPoint(0, 0, 0)
        self.camera.SetViewUp(0, 0, 1)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        app_icon = QtWidgets.QApplication.windowIcon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        super().showEvent(event)
        self._force_windows_taskbar_icon()
        QtCore.QTimer.singleShot(0, self._force_windows_taskbar_icon)

    def _force_windows_taskbar_icon(self) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
        except Exception:
            return

        icon_candidates = [
            QtCore.QDir.current().absoluteFilePath("Icons/mupro-logo-new.ico"),
        ]
        icon_path = ""
        for candidate in icon_candidates:
            if os.path.isfile(candidate):
                icon_path = candidate
                break
        if not icon_path:
            return

        hwnd = int(self.winId())
        if hwnd == 0:
            return

        user32 = ctypes.windll.user32
        image_icon = 1
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1
        lr_loadfromfile = 0x0010
        hicon_small = user32.LoadImageW(None, icon_path, image_icon, 16, 16, lr_loadfromfile)
        hicon_big = user32.LoadImageW(None, icon_path, image_icon, 32, 32, lr_loadfromfile)
        if hicon_small:
            user32.SendMessageW(hwnd, wm_seticon, icon_small, hicon_small)
            self._hicon_small = hicon_small
        if hicon_big:
            user32.SendMessageW(hwnd, wm_seticon, icon_big, hicon_big)
            self._hicon_big = hicon_big

    def _setup_ui(self) -> None:
        self.vectorChoice.setView(QtWidgets.QListView())
        self.RGB_Combo.setView(QtWidgets.QListView())
        self.alpha_Combo.setView(QtWidgets.QListView())
        self.scalarChoice.setView(QtWidgets.QListView())
        self.domainAlpha_Combo.setView(QtWidgets.QListView())
        self.vectorColorMode_Combo.setView(QtWidgets.QListView())
        self.RGBDomain_Combo.setView(QtWidgets.QListView())
        self.isoValue_Combo.setView(QtWidgets.QListView())

        self.scalar_Table.setColumnWidth(0, 70)
        self.scalar_Table.setColumnWidth(1, 70)
        self.scalar_Table.setColumnWidth(2, 70)
        self.vector_Table.setColumnWidth(0, 70)
        self.vector_Table.setColumnWidth(1, 70)
        self.vector_Table.setColumnWidth(2, 70)
        self.domain_Table.setColumnWidth(0, 70)
        self.domain_Table.setColumnWidth(1, 70)
        self.domain_Table.setColumnWidth(2, 70)

        self.RGBScalar_Table.setColumnWidth(0, 40)
        self.RGBScalar_Table.setColumnWidth(1, 50)
        self.RGBScalar_Table.setColumnWidth(2, 50)
        self.RGBScalar_Table.setColumnWidth(3, 50)
        self.RGBVector_Table.setColumnWidth(0, 40)
        self.RGBVector_Table.setColumnWidth(1, 50)
        self.RGBVector_Table.setColumnWidth(2, 50)
        self.RGBVector_Table.setColumnWidth(3, 50)
        self.RGBIso_Table.setColumnWidth(0, 40)
        self.RGBIso_Table.setColumnWidth(1, 50)
        self.RGBIso_Table.setColumnWidth(2, 50)
        self.RGBIso_Table.setColumnWidth(3, 50)
        self.RGBDomain_Table.setColumnWidth(0, 40)
        self.RGBDomain_Table.setColumnWidth(1, 50)
        self.RGBDomain_Table.setColumnWidth(2, 50)
        self.RGBDomain_Table.setColumnWidth(3, 50)

        self.alphaScalar_Table.setColumnWidth(0, 90)
        self.alphaScalar_Table.setColumnWidth(1, 90)
        self.alphaDomain_Table.setColumnWidth(0, 90)
        self.alphaDomain_Table.setColumnWidth(1, 90)

        self.viewportSizeX.setText("2000")
        self.viewportSizeY.setText("2000")
        if not self.exportRatio.text().strip():
            self.exportRatio.setText("1")

        interactor = self.qvtkWidget.GetRenderWindow().GetInteractor()
        interactor.Initialize()
        interactor_style = vtk.vtkInteractorStyleTrackballCamera()
        interactor.SetInteractorStyle(interactor_style)
        self._pointProbeObserverTag = interactor_style.AddObserver(
            "LeftButtonPressEvent", self._on_vtk_left_button_press
        )
        self._middlePanObserverPressTag = interactor.AddObserver(
            "MiddleButtonPressEvent", self._on_vtk_middle_button_press, -1.0
        )
        self._middlePanObserverReleaseTag = interactor.AddObserver(
            "MiddleButtonReleaseEvent", self._on_vtk_middle_button_release, -1.0
        )
        self._middlePanObserverMoveTag = interactor.AddObserver(
            "MouseMoveEvent", self._on_vtk_mouse_move_lock_pan, -1.0
        )
        self.widget.SetInteractor(interactor)
        self.vectorOrientationLegend.SetInteractor(interactor)
        self.scalarLegendWidget.SetInteractor(interactor)
        self.vectorLegendWidget.SetInteractor(interactor)

        self.actionOpenFile_scalar.triggered.connect(self.slotOpenFile_scalar)
        self.actionOpenFile_vector.triggered.connect(self.slotOpenFile_vector)
        self.actionOpenFile_domain.triggered.connect(self.slotOpenFile_domain)
        self.actionExit.triggered.connect(self.slotExit)
        self.actionRefresh.triggered.connect(self.slotUpdate)
        self.actionClear.triggered.connect(self.slotClear)
        self.actionSave.triggered.connect(self.saveImage)
        self.actionExportX3D.triggered.connect(self.saveScene)
        self.actionRotateToXP.triggered.connect(self.slotUpdateCamera1)
        self.actionRotateToXN.triggered.connect(self.slotUpdateCamera2)
        self.actionRotateToYP.triggered.connect(self.slotUpdateCamera3)
        self.actionRotateToYN.triggered.connect(self.slotUpdateCamera4)
        self.actionRotateToZP.triggered.connect(self.slotUpdateCamera5)
        self.actionRotateToZN.triggered.connect(self.slotUpdateCamera6)
        self.action1D.triggered.connect(self.slotSwitch1D)
        self.action3D.triggered.connect(self.slotSwitch3D)
        self.actionOutputStatus.triggered.connect(self.slotOutputStatus)
        self.actionLoadStatus.triggered.connect(self.slotLoadStatus)
        self.actionBatch3D.triggered.connect(self.slotBatch3D)

        if hasattr(self.file1_Widget, "figureReplot"):
            self.file1_Widget.figureReplot.connect(self.figurePlot)
        if hasattr(self.file2_Widget, "figureReplot"):
            self.file2_Widget.figureReplot.connect(self.figurePlot)
        self._add_coordinate_ruler_page()
        self._add_point_probe_page()

    def _add_coordinate_ruler_page(self) -> None:
        if not hasattr(self, "toolBox"):
            return
        page = QtWidgets.QWidget(self.toolBox)
        page.setObjectName("page_coordinate_ruler")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.coordRuler_CB = QtWidgets.QCheckBox("Show edge coordinate ruler", page)
        self.coordRuler_CB.setObjectName("coordRuler_CB")
        self.coordRuler_CB.setToolTip(
            "Show coordinate ruler on visualization edges.\n"
            "Ruler values follow extraction xyz range and start at 1."
        )
        self.coordRuler_CB.setCheckState(QtCore.Qt.Unchecked)
        layout.addWidget(self.coordRuler_CB)

        layout.addStretch(1)

        self.toolBox.addItem(page, "Coordinate Ruler")
        self.coordRuler_CB.stateChanged.connect(self.on_coordRuler_CB_stateChanged)

    def _add_point_probe_page(self) -> None:
        if not hasattr(self, "toolBox"):
            return
        page = QtWidgets.QWidget(self.toolBox)
        page.setObjectName("page_point_probe")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.pointProbe_CB = QtWidgets.QCheckBox("Enable point probe", page)
        self.pointProbe_CB.setObjectName("pointProbe_CB")
        self.pointProbe_CB.setToolTip(
            "Click in the 3D visualization to inspect point coordinates.\n"
            "Scalar mode: original scalar value.\n"
            "Vector mode: magnitude and angles to X/Y/Z axes."
        )
        self.pointProbe_CB.setCheckState(QtCore.Qt.Unchecked)
        layout.addWidget(self.pointProbe_CB)

        self.pointProbeCoordValue_LB = QtWidgets.QLabel("-", page)
        self.pointProbeIndexValue_LB = QtWidgets.QLabel("-", page)
        self.pointProbeDataValue_LB = QtWidgets.QLabel("-", page)
        self.pointProbeSourceValue_LB = QtWidgets.QLabel("-", page)
        labels = (
            self.pointProbeCoordValue_LB,
            self.pointProbeIndexValue_LB,
            self.pointProbeDataValue_LB,
            self.pointProbeSourceValue_LB,
        )
        for label in labels:
            label.setWordWrap(True)
            label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            label.setStyleSheet("padding-left: 12px;")

        def _add_probe_block(title_text: str, value_label: QtWidgets.QLabel) -> None:
            title_label = QtWidgets.QLabel(title_text, page)
            title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            layout.addWidget(title_label)
            layout.addWidget(value_label)

        _add_probe_block("World coordinate:", self.pointProbeCoordValue_LB)
        _add_probe_block("Grid index (1-based):", self.pointProbeIndexValue_LB)
        _add_probe_block("Probe result:", self.pointProbeDataValue_LB)
        _add_probe_block("Source:", self.pointProbeSourceValue_LB)
        layout.addStretch(1)

        self.toolBox.addItem(page, "Point Probe")
        self.pointProbe_CB.stateChanged.connect(self.on_pointProbe_CB_stateChanged)
        self._reset_point_probe_display()
        self._refresh_point_probe_source()

    def _set_point_probe_label(
        self, label: Optional[QtWidgets.QLabel], text: str
    ) -> None:
        if label is not None:
            label.setText(text)

    def _reset_point_probe_display(self) -> None:
        self._set_point_probe_label(self.pointProbeCoordValue_LB, "-")
        self._set_point_probe_label(self.pointProbeIndexValue_LB, "-")
        if self.pointProbe_CB is not None and self.pointProbe_CB.isChecked():
            self._set_point_probe_hint()
        else:
            self._set_point_probe_label(self.pointProbeDataValue_LB, "Point probe is disabled.")

    def _current_point_probe_mode(self) -> str:
        if self.vector_CB.isChecked() and self._pointProbeVectorOutput is not None:
            return "vector"
        if self.scalar_CB.isChecked() and self._pointProbeScalarOutput is not None:
            return "scalar"
        if self._pointProbeVectorOutput is not None and self._pointProbeScalarOutput is None:
            return "vector"
        if self._pointProbeScalarOutput is not None:
            return "scalar"
        return "none"

    def _set_point_probe_hint(self) -> None:
        mode = self._current_point_probe_mode()
        if mode == "vector":
            self._set_point_probe_label(
                self.pointProbeDataValue_LB, "Click a point to view magnitude and X/Y/Z angles."
            )
        elif mode == "scalar":
            self._set_point_probe_label(
                self.pointProbeDataValue_LB, "Click a point to view original scalar value."
            )
        elif self.vector_CB.isChecked():
            self._set_point_probe_label(self.pointProbeDataValue_LB, "No vector field loaded.")
        elif self.scalar_CB.isChecked():
            self._set_point_probe_label(self.pointProbeDataValue_LB, "No scalar field loaded.")
        else:
            self._set_point_probe_label(self.pointProbeDataValue_LB, "No probe data loaded.")

    def _refresh_point_probe_source(self) -> None:
        mode = self._current_point_probe_mode()
        if mode == "vector":
            if self._pointProbeVectorColumns:
                self._set_point_probe_label(
                    self.pointProbeSourceValue_LB, f"Vector columns:\n{self._pointProbeVectorColumns}"
                )
            else:
                self._set_point_probe_label(self.pointProbeSourceValue_LB, "Vector columns unknown.")
            return
        if mode == "scalar":
            if self._pointProbeScalarColumn is None:
                self._set_point_probe_label(self.pointProbeSourceValue_LB, "Scalar column unknown.")
            else:
                self._set_point_probe_label(
                    self.pointProbeSourceValue_LB, f"Scalar column:\n{self._pointProbeScalarColumn}"
                )
            return
        if self.vector_CB.isChecked():
            self._set_point_probe_label(self.pointProbeSourceValue_LB, "No vector field loaded.")
        elif self.scalar_CB.isChecked():
            self._set_point_probe_label(self.pointProbeSourceValue_LB, "No scalar field loaded.")
        else:
            self._set_point_probe_label(self.pointProbeSourceValue_LB, "No probe data loaded.")

    def _sample_grid_index_and_point_id(
        self, image: Optional[vtk.vtkImageData], world_pos: tuple[float, float, float]
    ) -> tuple[Optional[tuple[int, int, int]], int]:
        if image is None:
            return None, -1

        extent = image.GetExtent()
        i_min, i_max, j_min, j_max, k_min, k_max = extent

        if hasattr(image, "TransformPhysicalPointToContinuousIndex"):
            continuous_ijk = [0.0, 0.0, 0.0]
            image.TransformPhysicalPointToContinuousIndex(world_pos, continuous_ijk)
            i = int(round(continuous_ijk[0]))
            j = int(round(continuous_ijk[1]))
            k = int(round(continuous_ijk[2]))
        else:
            origin = image.GetOrigin()
            spacing = image.GetSpacing()

            def _coord_to_index(
                coord: float, axis_origin: float, axis_spacing: float, low: int, high: int
            ) -> int:
                if math.isclose(axis_spacing, 0.0):
                    return low
                raw_index = int(round((coord - axis_origin) / axis_spacing))
                return max(low, min(high, raw_index))

            i = _coord_to_index(world_pos[0], origin[0], spacing[0], i_min, i_max)
            j = _coord_to_index(world_pos[1], origin[1], spacing[1], j_min, j_max)
            k = _coord_to_index(world_pos[2], origin[2], spacing[2], k_min, k_max)

        if i < i_min or i > i_max or j < j_min or j > j_max or k < k_min or k > k_max:
            return None, -1

        point_id = image.ComputePointId((i, j, k))
        return (i, j, k), point_id

    def _sample_scalar_value_at_world(
        self, world_pos: tuple[float, float, float]
    ) -> tuple[Optional[tuple[int, int, int]], Optional[float]]:
        image = self._pointProbeScalarOutput
        index_ijk, point_id = self._sample_grid_index_and_point_id(image, world_pos)
        if index_ijk is None:
            return None, None
        if point_id < 0:
            return index_ijk, None

        scalars = image.GetPointData().GetScalars()
        if scalars is None or point_id >= scalars.GetNumberOfTuples():
            return index_ijk, None

        return index_ijk, float(scalars.GetTuple1(point_id))

    def _sample_vector_value_at_world(
        self, world_pos: tuple[float, float, float]
    ) -> tuple[Optional[tuple[int, int, int]], Optional[tuple[float, float, float]], Optional[float]]:
        image = self._pointProbeVectorOutput
        index_ijk, point_id = self._sample_grid_index_and_point_id(image, world_pos)
        if index_ijk is None:
            return None, None, None
        if point_id < 0:
            return index_ijk, None, None

        point_data = image.GetPointData()
        vectors = point_data.GetVectors()
        if vectors is None:
            vectors = point_data.GetArray("vector")

        vector_value: Optional[tuple[float, float, float]] = None
        if vectors is not None and point_id < vectors.GetNumberOfTuples():
            vector_tuple = vectors.GetTuple(point_id)
            if len(vector_tuple) >= 3:
                vector_value = (
                    float(vector_tuple[0]),
                    float(vector_tuple[1]),
                    float(vector_tuple[2]),
                )

        magnitude: Optional[float] = None
        scalars = point_data.GetScalars()
        if scalars is not None and point_id < scalars.GetNumberOfTuples():
            magnitude = float(scalars.GetTuple1(point_id))
        elif vector_value is not None:
            vx, vy, vz = vector_value
            magnitude = math.sqrt(vx * vx + vy * vy + vz * vz)

        return index_ijk, vector_value, magnitude

    def _format_vector_probe_text(
        self, vector_value: Optional[tuple[float, float, float]], magnitude: Optional[float]
    ) -> str:
        if vector_value is None:
            if magnitude is None:
                return "Vector value unavailable."
            return f"|V|: {magnitude:.8g}"

        vx, vy, vz = vector_value
        mag = magnitude
        if mag is None:
            mag = math.sqrt(vx * vx + vy * vy + vz * vz)
        if not math.isfinite(mag) or mag <= 1.0e-12:
            return (
                f"Vx: {vx:.8g}\n"
                f"Vy: {vy:.8g}\n"
                f"Vz: {vz:.8g}\n"
                f"|V|: {mag:.8g}\n"
                "Ang-X: undefined\n"
                "Ang-Y: undefined\n"
                "Ang-Z: undefined"
            )

        def _axis_angle_deg(component: float) -> float:
            cos_value = component / mag
            if cos_value > 1.0:
                cos_value = 1.0
            elif cos_value < -1.0:
                cos_value = -1.0
            return math.degrees(math.acos(cos_value))

        angle_x = _axis_angle_deg(vx)
        angle_y = _axis_angle_deg(vy)
        angle_z = _axis_angle_deg(vz)
        return (
            f"Vx: {vx:.8g}\n"
            f"Vy: {vy:.8g}\n"
            f"Vz: {vz:.8g}\n"
            f"|V|: {mag:.8g}\n"
            f"Ang-X: {angle_x:.6g} deg\n"
            f"Ang-Y: {angle_y:.6g} deg\n"
            f"Ang-Z: {angle_z:.6g} deg"
        )

    def _pick_world_position(
        self, renderer: vtk.vtkRenderer, click_x: int, click_y: int
    ) -> Optional[tuple[float, float, float]]:
        picked = self._pointProbePicker.Pick(float(click_x), float(click_y), 0.0, renderer)
        if picked > 0:
            picked_pos = self._pointProbePicker.GetPickPosition()
            if all(math.isfinite(v) for v in picked_pos):
                return (float(picked_pos[0]), float(picked_pos[1]), float(picked_pos[2]))

        world_picked = self._pointProbeWorldPicker.Pick(float(click_x), float(click_y), 0.0, renderer)
        if world_picked > 0:
            picked_pos = self._pointProbeWorldPicker.GetPickPosition()
            if all(math.isfinite(v) for v in picked_pos):
                return (float(picked_pos[0]), float(picked_pos[1]), float(picked_pos[2]))
        return None

    @staticmethod
    def _normalized_vector(
        x: float, y: float, z: float
    ) -> Optional[tuple[float, float, float]]:
        length = math.sqrt(x * x + y * y + z * z)
        if not math.isfinite(length) or length <= 1.0e-12:
            return None
        return (x / length, y / length, z / length)

    def _on_vtk_middle_button_press(self, _obj, _event) -> None:
        self._clear_middle_pan_state()
        if self.stackedWidget.currentIndex() != 0:
            return
        renderers = self.qvtkWidget.GetRenderWindow().GetRenderers()
        if renderers.GetNumberOfItems() == 0:
            return
        renderer = renderers.GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        if camera is None:
            return

        position = camera.GetPosition()
        focal = camera.GetFocalPoint()
        view_up = camera.GetViewUp()
        view_direction = self._normalized_vector(
            focal[0] - position[0], focal[1] - position[1], focal[2] - position[2]
        )
        normalized_up = self._normalized_vector(view_up[0], view_up[1], view_up[2])
        if view_direction is None or normalized_up is None:
            return

        self._middlePanActive = True
        self._middlePanCamera = camera
        self._middlePanViewDirection = view_direction
        self._middlePanViewUp = normalized_up

    def _clear_middle_pan_state(self) -> None:
        self._middlePanActive = False
        self._middlePanCamera = None
        self._middlePanViewDirection = None
        self._middlePanViewUp = None

    def _is_middle_button_down(self) -> bool:
        interactor = self.qvtkWidget.GetRenderWindow().GetInteractor()
        if interactor is None or not hasattr(interactor, "GetMiddleButton"):
            return self._middlePanActive
        try:
            return bool(interactor.GetMiddleButton())
        except Exception:
            return self._middlePanActive

    def _on_vtk_middle_button_release(self, _obj, _event) -> None:
        self._clear_middle_pan_state()

    def _on_vtk_mouse_move_lock_pan(self, _obj, _event) -> None:
        if not self._middlePanActive:
            return
        if not self._is_middle_button_down():
            self._clear_middle_pan_state()
            return
        camera = self._middlePanCamera
        direction = self._middlePanViewDirection
        view_up = self._middlePanViewUp
        if camera is None or direction is None or view_up is None:
            return

        position = camera.GetPosition()
        focal = camera.GetFocalPoint()
        distance = math.sqrt(
            (focal[0] - position[0]) ** 2
            + (focal[1] - position[1]) ** 2
            + (focal[2] - position[2]) ** 2
        )
        if not math.isfinite(distance) or distance <= 1.0e-12:
            return

        camera.SetFocalPoint(
            position[0] + direction[0] * distance,
            position[1] + direction[1] * distance,
            position[2] + direction[2] * distance,
        )
        camera.SetViewUp(*view_up)
        camera.OrthogonalizeViewUp()

    def _on_vtk_left_button_press(self, _obj, _event) -> None:
        def _forward_to_default_left_button() -> None:
            if hasattr(_obj, "OnLeftButtonDown"):
                _obj.OnLeftButtonDown()
                return
            interactor = self.qvtkWidget.GetRenderWindow().GetInteractor()
            style = interactor.GetInteractorStyle() if interactor is not None else None
            if style is not None and hasattr(style, "OnLeftButtonDown"):
                style.OnLeftButtonDown()

        if self.pointProbe_CB is None or not self.pointProbe_CB.isChecked():
            _forward_to_default_left_button()
            return
        if self.stackedWidget.currentIndex() != 0:
            _forward_to_default_left_button()
            return

        renderers = self.qvtkWidget.GetRenderWindow().GetRenderers()
        if renderers.GetNumberOfItems() == 0:
            _forward_to_default_left_button()
            return
        renderer = renderers.GetFirstRenderer()

        interactor = self.qvtkWidget.GetRenderWindow().GetInteractor()
        click_x, click_y = interactor.GetEventPosition()
        world = self._pick_world_position(renderer, click_x, click_y)
        if world is None:
            self._set_point_probe_label(self.pointProbeCoordValue_LB, "-")
            self._set_point_probe_label(self.pointProbeIndexValue_LB, "-")
            self._set_point_probe_label(self.pointProbeDataValue_LB, "No point picked.")
            return

        self._set_point_probe_label(
            self.pointProbeCoordValue_LB,
            f"x: {world[0]:.6g}\n"
            f"y: {world[1]:.6g}\n"
            f"z: {world[2]:.6g}",
        )

        mode = self._current_point_probe_mode()
        if mode == "vector":
            index_ijk, vector_value, magnitude = self._sample_vector_value_at_world(world)
            if index_ijk is None:
                self._set_point_probe_label(self.pointProbeIndexValue_LB, "-")
                if self._pointProbeVectorOutput is None:
                    self._set_point_probe_label(self.pointProbeDataValue_LB, "No vector field loaded.")
                else:
                    self._set_point_probe_label(self.pointProbeDataValue_LB, "Point is outside vector data.")
                return

            self._set_point_probe_label(
                self.pointProbeIndexValue_LB,
                f"x: {index_ijk[0] + 1}\n"
                f"y: {index_ijk[1] + 1}\n"
                f"z: {index_ijk[2] + 1}",
            )
            self._set_point_probe_label(
                self.pointProbeDataValue_LB,
                self._format_vector_probe_text(vector_value, magnitude),
            )
            return

        if mode == "scalar":
            index_ijk, scalar_value = self._sample_scalar_value_at_world(world)
            if index_ijk is None:
                self._set_point_probe_label(self.pointProbeIndexValue_LB, "-")
                if self._pointProbeScalarOutput is None:
                    self._set_point_probe_label(self.pointProbeDataValue_LB, "No scalar field loaded.")
                else:
                    self._set_point_probe_label(self.pointProbeDataValue_LB, "Point is outside scalar data.")
                return

            self._set_point_probe_label(
                self.pointProbeIndexValue_LB,
                f"x: {index_ijk[0] + 1}\n"
                f"y: {index_ijk[1] + 1}\n"
                f"z: {index_ijk[2] + 1}",
            )
            if scalar_value is None:
                self._set_point_probe_label(self.pointProbeDataValue_LB, "Scalar value unavailable.")
            else:
                self._set_point_probe_label(self.pointProbeDataValue_LB, f"{scalar_value:.8g}")
            return

        self._set_point_probe_label(self.pointProbeIndexValue_LB, "-")
        self._set_point_probe_label(self.pointProbeDataValue_LB, "No probe data loaded.")
        _forward_to_default_left_button()

    def _update_point_probe_vector_dataset(
        self,
        vector_voi: tuple[int, int, int, int, int, int],
    ) -> None:
        probe_extractor = vtk.vtkExtractVOI()
        probe_extractor.SetInputConnection(self.readerVectorOrigin.GetOutputPort())
        probe_extractor.SetVOI(*vector_voi)
        probe_extractor.SetSampleRate(1, 1, 1)
        probe_extractor.Update()
        self._pointProbeVectorExtractor = probe_extractor
        self._pointProbeVectorOutput = probe_extractor.GetOutput()

        choice_text = self.vectorChoice.currentText().strip() if self.vectorChoice.count() else ""
        self._pointProbeVectorColumns = choice_text or "123"

    def _clear_point_probe_vector_dataset(self) -> None:
        self._pointProbeVectorExtractor = None
        self._pointProbeVectorOutput = None
        self._pointProbeVectorColumns = None

    def _update_coordinate_ruler(
        self,
        renderer: Optional[vtk.vtkRenderer],
        extent: Optional[tuple[int, int, int, int, int, int]],
    ) -> None:
        if renderer is None:
            return
        if not renderer.HasViewProp(self.coordRulerActor):
            renderer.AddActor(self.coordRulerActor)

        enabled = (
            self.stackedWidget.currentIndex() == 0
            and self.coordRuler_CB is not None
            and self.coordRuler_CB.isChecked()
            and extent is not None
        )
        if not enabled:
            self.coordRulerActor.VisibilityOff()
            return

        xmin, xmax, ymin, ymax, zmin, zmax = extent
        x0, x1_raw = sorted((xmin, xmax))
        y0, y1_raw = sorted((ymin, ymax))
        z0, z1_raw = sorted((zmin, zmax))

        def _safe_positive_spacing(edit: QtWidgets.QLineEdit) -> float:
            text = edit.text().strip()
            if not text:
                return 1.0
            try:
                value = float(text)
            except ValueError:
                return 1.0
            if not math.isfinite(value) or value == 0:
                return 1.0
            return abs(value)

        sx = _safe_positive_spacing(self.rescaleX_LE)
        sy = _safe_positive_spacing(self.rescaleY_LE)
        sz = _safe_positive_spacing(self.rescaleZ_LE)

        x1 = float(x0 + 1) * sx
        x2 = float(x1_raw + 1) * sx
        y1 = float(y0 + 1) * sy
        y2 = float(y1_raw + 1) * sy
        z1 = float(z0 + 1) * sz
        z2 = float(z1_raw + 1) * sz

        if math.isclose(x1, x2):
            x2 = x1 + sx
        if math.isclose(y1, y2):
            y2 = y1 + sy
        if math.isclose(z1, z2):
            z2 = z1 + sz

        self.coordRulerActor.SetBounds(
            float(x0) * sx,
            float(x1_raw) * sx,
            float(y0) * sy,
            float(y1_raw) * sy,
            float(z0) * sz,
            float(z1_raw) * sz,
        )
        self.coordRulerActor.SetXAxisRange(x1, x2)
        self.coordRulerActor.SetYAxisRange(y1, y2)
        self.coordRulerActor.SetZAxisRange(z1, z2)
        self.coordRulerActor.SetCamera(renderer.GetActiveCamera())
        self.coordRulerActor.VisibilityOn()

    def _init_renderer(self) -> None:
        if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
            renderer = vtk.vtkRenderer()
            self.qvtkWidget.GetRenderWindow().AddRenderer(renderer)
        else:
            renderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()
        renderer.SetBackground(0.9, 0.9, 0.9)
        if not renderer.HasViewProp(self.coordRulerActor):
            renderer.AddActor(self.coordRulerActor)
        self.coordRulerActor.SetCamera(renderer.GetActiveCamera())
        self.coordRulerActor.VisibilityOff()
        self.qvtkWidget.GetRenderWindow().Render()
        self.qvtkWidget.update()

    def _apply_icons(self) -> None:
        icon_dir = QtCore.QDir.current().absoluteFilePath("Icons")

        def icon_path(name: str) -> str:
            return QtCore.QDir.toNativeSeparators(os.path.join(icon_dir, name))

        def set_action_icon(action: Optional[QtWidgets.QAction], filename: str) -> None:
            if action is not None:
                action.setIcon(QtGui.QIcon(icon_path(filename)))

        set_action_icon(self.actionOpenFile_scalar, "scalar-open.png")
        set_action_icon(self.actionOpenFile_vector, "vector-open.png")
        set_action_icon(self.actionOpenFile_domain, "domain-open.png")
        set_action_icon(self.actionPrint, "print.png")
        set_action_icon(self.actionRefresh, "refresh.png")
        set_action_icon(self.actionSave, "filesave.png")
        set_action_icon(self.actionRotateToXP, "x+.png")
        set_action_icon(self.actionRotateToXN, "X-.png")
        set_action_icon(self.actionRotateToYP, "Y+.png")
        set_action_icon(self.actionRotateToYN, "Y-.png")
        set_action_icon(self.actionRotateToZP, "Z+.png")
        set_action_icon(self.actionRotateToZN, "Z-.png")
        set_action_icon(self.actionClear, "clear-icon.png")
        set_action_icon(self.action3D, "3d.png")
        set_action_icon(self.action1D, "1D.png")
        set_action_icon(self.actionOutputStatus, "outputStatus.png")
        set_action_icon(self.actionLoadStatus, "loadStatus.png")
        set_action_icon(self.actionBatch3D, "batch3D.png")
        set_action_icon(self.actionExportX3D, "x3d.png")

        if hasattr(self, "toolBar"):
            self.toolBar.setIconSize(QtCore.QSize(22, 22))
            self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)

        self.setWindowIcon(QtGui.QIcon(icon_path("mupro-logo-new.png")))

    def _init_domain_colors(self) -> None:
        colors = [
            (0.752912, 0.752912, 0.752912),
            (0, 0, 1),
            (0.46, 0.7175, 0.8135),
            (0, 0.153787, 0.0),
            (0, 1, 0),
            (1, 0, 0),
            (1, 0.566921, 0.633741),
            (1, 0.418685, 0),
            (1, 1, 0),
            (1, 0, 1),
            (0.64629, 0.130165, 0.130165),
            (0.9, 0.566921, 0.633741),
            (0.751111, 0.393695, 0.751111),
            (0.418685, 0.027128, 0.027128),
            (0.678201, 0.498270, 0.301423),
            (0.476371, 0.035432, 0.14173),
            (0.961169, 0.251965, 0.199862),
            (0.355309, 0.968874, 0.355309),
            (0.038446, 0.646290, 0.038446),
            (0.766921, 0.766921, 0.766921),
            (0.169550, 0.169550, 0.169550),
            (0.566921, 0.566921, 0.566921),
            (0.393695, 0.015747, 0.885813),
            (0.0, 0.0, 0.0),
            (1.0, 0.710881, 0.0),
            (0.885813, 0.813533, 0.301423),
            (0.8867188, 0.4335937, 0.0273438),
        ]
        for i, (r, g, b) in enumerate(colors):
            self.domainRGB[i] = [r, g, b]
            self.domainRGBHold[i] = [r, g, b]
            item = self.domain_TW.item(i + 4, 0)
            if item is not None:
                item.setForeground(QtGui.QColor(int(r * 255), int(g * 255), int(b * 255)))

        self.domainList = [
            "All domains",
            "All R domains",
            "All O domains",
            "All T domains",
            "Substrate",
            "R1+(+,+,+)",
            "R1-(-,-,-)",
            "R2+(-,+,+)",
            "R2-(+,-,-)",
            "R3+(-,-,+)",
            "R3-(+,+,-)",
            "R4+(+,-,+)",
            "R4-(-,+,-)",
            "O1+(+,+,0)",
            "O1-(-,-,0)",
            "O2+(+,-,0)",
            "O2-(-,+,0)",
            "O3+(+,0,+)",
            "O3-(-,0,-)",
            "O4+(+,0,-)",
            "O4-(-,0,+)",
            "O5+(0,+,+)",
            "O5-(0,-,-)",
            "O6+(0,+,-)",
            "O6-(0,-,+)",
            "T1+(+,0,0)",
            "T1-(-,0,0)",
            "T2+(0,+,0)",
            "T2-(0,-,0)",
            "T3+(0,0,+)",
            "T3-(0,0,-)",
        ]

    def _init_vo2_colors(self) -> None:
        colors = [
            (0.752912, 0.752912, 0.752912),
            (0, 1, 0),
            (1, 0, 0),
            (0, 0.5, 0),
            (0.5, 0, 0),
            (0, 0, 1),
            (0, 1, 1),
            (0, 0, 0.5),
            (0, 0.5, 0.5),
        ]
        for i, (r, g, b) in enumerate(colors):
            self.vo2DomainRGB[i] = [r, g, b]
            self.vo2DomainRGBHold[i] = [r, g, b]
            item = self.vo2Domain_LW.item(i)
            if item is not None:
                item.setForeground(QtGui.QColor(int(r * 255), int(g * 255), int(b * 255)))
        self.vo2DomainList = ["R", "M1.V1", "M1.V2", "M1.V3", "M1.V4", "M2.V1", "M2.V2", "M2.V3", "M2.V4"]

    def figurePlot(self) -> None:
        self.customPlot.replot()

    def slotSwitch1D(self) -> None:
        self.stackedWidget.setCurrentIndex(1)
        self.xmin = 0
        self.xmax = 0
        self.ymin = 0
        self.ymax = 0
        self.zmax = 0
        self.zmin = 0
        self.actionOpenFile_scalar.setEnabled(False)
        self.actionOpenFile_vector.setEnabled(False)
        self.actionOpenFile_domain.setEnabled(False)
        self.actionRotateToXN.setEnabled(False)
        self.actionRotateToXP.setEnabled(False)
        self.actionRotateToYN.setEnabled(False)
        self.actionRotateToYP.setEnabled(False)
        self.actionRotateToZN.setEnabled(False)
        self.actionRotateToZP.setEnabled(False)
        self.actionOutputStatus.setEnabled(False)
        self.actionLoadStatus.setEnabled(False)
        self.coordRulerActor.VisibilityOff()

    def slotSwitch3D(self) -> None:
        self.stackedWidget.setCurrentIndex(0)
        self.xmin = 0
        self.xmax = 0
        self.ymin = 0
        self.ymax = 0
        self.zmax = 0
        self.zmin = 0
        self.actionOpenFile_scalar.setEnabled(True)
        self.actionOpenFile_vector.setEnabled(True)
        self.actionOpenFile_domain.setEnabled(True)
        self.actionRotateToXN.setEnabled(True)
        self.actionRotateToXP.setEnabled(True)
        self.actionRotateToYN.setEnabled(True)
        self.actionRotateToYP.setEnabled(True)
        self.actionRotateToZN.setEnabled(True)
        self.actionRotateToZP.setEnabled(True)
        self.actionOutputStatus.setEnabled(True)
        self.actionLoadStatus.setEnabled(True)
        if self.coordRuler_CB is not None and self.coordRuler_CB.isChecked():
            self.slotUpdate()

    def slotUpdate(self) -> None:
        if self.stackedWidget.currentIndex() == 0:
            self.updateVTK(self.scalarName, self.vectorName)
            if self.domain_Combo.currentIndex() == 0:
                self.drawDomain(self.domainName)
            elif self.domain_Combo.currentIndex() == 1:
                self.drawVO2Domain(self.domainName)
        else:
            self.setup1DFigure(self.customPlot)
        self.updateFlag = True

    def slotClear(self) -> None:
        if self.stackedWidget.currentIndex() == 0:
            if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
                return
            new_view = SimpleView()
            new_view.show()
            self.centralwidget.deleteLater()
            self.close()
        else:
            self.customPlot.clearGraphs()

    def slotExit(self) -> None:
        QtWidgets.QApplication.instance().quit()

    def slotUpdateCamera1(self) -> None:
        self.updateCamera(1)

    def slotUpdateCamera2(self) -> None:
        self.updateCamera(2)

    def slotUpdateCamera3(self) -> None:
        self.updateCamera(3)

    def slotUpdateCamera4(self) -> None:
        self.updateCamera(4)

    def slotUpdateCamera5(self) -> None:
        self.updateCamera(5)

    def slotUpdateCamera6(self) -> None:
        self.updateCamera(6)

    def setup1DFigure(self, customPlot: QCustomPlot) -> None:
        customPlot.clearGraphs()
        customPlot.clearItems()
        customPlot.clearPlottables()
        data_rows1 = self.file1_Widget.getFilteredCount()
        data_rows2 = self.file2_Widget.getFilteredCount()

        xmin1 = 1.0
        xmax1 = 0.0
        ymin1 = 1.0
        ymax1 = 0.0
        xmin2 = 1.0
        xmax2 = 0.0
        ymin2 = 1.0
        ymax2 = 0.0

        if self.plot1DAutoTickX1_CB.isChecked():
            customPlot.xAxis.setAutoTicks(True)
            customPlot.xAxis.setAutoTickLabels(True)
        else:
            customPlot.xAxis.setAutoTicks(False)
            customPlot.xAxis.setAutoTickLabels(False)
            ticks = []
            labels = []
            for part in self.plot1DTickValueX1_LE.text().split(","):
                part = part.strip()
                if part:
                    try:
                        ticks.append(float(part))
                    except ValueError:
                        continue
            for part in self.plot1DTickLabelX1_LE.text().split(","):
                part = part.strip()
                if part:
                    labels.append(part)
            customPlot.xAxis.setTickVector(ticks)
            customPlot.xAxis.setTickVectorLabels(labels)

        customPlot.xAxis.setTickLabels(self.plot1DTickLabelX1_CB.isChecked())
        customPlot.xAxis2.setTickLabels(self.plot1DTickLabelX2_CB.isChecked())
        customPlot.yAxis.setTickLabels(self.plot1DTickLabelY1_CB.isChecked())
        customPlot.yAxis2.setTickLabels(self.plot1DTickLabelY2_CB.isChecked())

        graph_num = 0
        columns1 = self.file1_Widget.getColumns()
        columns2 = self.file2_Widget.getColumns()

        for col_y in range(columns1):
            if data_rows1 > 0:
                item = self.file1_Widget.findChild(QtWidgets.QListWidget, "plot1DFileY_LW").item(col_y)
                if item and item.checkState() != QtCore.Qt.Unchecked:
                    x_vals = self.file1_Widget.returnX()
                    y_vals = self.file1_Widget.returnY(col_y)
                    xmin1 = min(xmin1, self.file1_Widget.returnXMin())
                    xmax1 = max(xmax1, self.file1_Widget.returnXMax())
                    ymin1 = min(ymin1, self.file1_Widget.returnYMin())
                    ymax1 = max(ymax1, self.file1_Widget.returnYMax())
                    customPlot.addGraph()
                    customPlot.graph(graph_num).setData(x_vals, y_vals)
                    customPlot.graph(graph_num).setPen(self.file1_Widget.getLineStyle(graph_num))
                    customPlot.graph(graph_num).setScatterStyle(self.file1_Widget.getScatterStyle(graph_num))
                    customPlot.graph(graph_num).setName(self.file1_Widget.getLineName(graph_num))
                    graph_num += 1

        xmin1 = self._override_range(self.plot1DRangeMinX1_LE, xmin1)
        xmax1 = self._override_range(self.plot1DRangeMaxX1_LE, xmax1)
        ymin1 = self._override_range(self.plot1DRangeMinY1_LE, ymin1)
        ymax1 = self._override_range(self.plot1DRangeMaxY1_LE, ymax1)

        graph_num_left = graph_num
        for col_y in range(columns2):
            if data_rows2 > 0:
                item = self.file2_Widget.findChild(QtWidgets.QListWidget, "plot1DFileY_LW").item(col_y)
                if item and item.checkState() != QtCore.Qt.Unchecked:
                    x_vals = self.file2_Widget.returnX()
                    y_vals = self.file2_Widget.returnY(col_y)
                    xmin2 = min(xmin2, self.file2_Widget.returnXMin())
                    xmax2 = max(xmax2, self.file2_Widget.returnXMax())
                    ymin2 = min(ymin2, self.file2_Widget.returnYMin())
                    ymax2 = max(ymax2, self.file2_Widget.returnYMax())
                    customPlot.addGraph(customPlot.xAxis2, customPlot.yAxis2)
                    customPlot.graph(graph_num).setData(x_vals, y_vals)
                    customPlot.graph(graph_num).setPen(
                        self.file2_Widget.getLineStyle(graph_num - graph_num_left)
                    )
                    customPlot.graph(graph_num).setScatterStyle(
                        self.file2_Widget.getScatterStyle(graph_num - graph_num_left)
                    )
                    customPlot.graph(graph_num).setName(
                        self.file2_Widget.getLineName(graph_num - graph_num_left)
                    )
                    graph_num += 1

        xmin2 = self._override_range(self.plot1DRangeMinX2_LE, xmin2)
        xmax2 = self._override_range(self.plot1DRangeMaxX2_LE, xmax2)
        ymin2 = self._override_range(self.plot1DRangeMinY2_LE, ymin2)
        ymax2 = self._override_range(self.plot1DRangeMaxY2_LE, ymax2)

        customPlot.xAxis.setLabel(self.plot1DLabelX1_LE.text())
        customPlot.yAxis.setLabel(self.plot1DLabelY1_LE.text())
        customPlot.xAxis2.setLabel(self.plot1DLabelX2_LE.text())
        customPlot.yAxis2.setLabel(self.plot1DLabelY2_LE.text())

        plot_title = QCPPlotTitle(customPlot, self.plot1DFigureTitle_LE.text())
        if customPlot.plotLayout().rowCount() == 1:
            customPlot.plotLayout().insertRow(0)
            customPlot.plotLayout().addElement(0, 0, plot_title)
        else:
            customPlot.plotLayout().removeAt(0)
            customPlot.plotLayout().addElement(0, 0, plot_title)

        customPlot.xAxis.setRange(xmin1, xmax1)
        customPlot.yAxis.setRange(ymin1, ymax1)
        customPlot.xAxis2.setRange(xmin2, xmax2)
        customPlot.yAxis2.setRange(ymin2, ymax2)

        customPlot.xAxis.grid().setVisible(self.plot1DXGrid_CB.isChecked())
        customPlot.yAxis.grid().setVisible(self.plot1DYGrid_CB.isChecked())

        if self.plot1DLegend_CB.isChecked():
            self.customPlot.legend.setVisible(True)
            try:
                x = float(self.plot1DLegendX_LE.text())
                y = float(self.plot1DLegendY_LE.text())
                w = float(self.plot1DLegendW_LE.text())
                h = float(self.plot1DLegendH_LE.text())
                self.customPlot.axisRect().insetLayout().setInsetRect(0, QtCore.QRectF(x, y, w, h))
            except ValueError:
                pass

        if not self.plot1DFont_CB.isChecked():
            title_font = self.plot1DFont_fontComboBox.currentFont()
            axis_font = self.plot1DFont_fontComboBox.currentFont()
            tick_font = self.plot1DFont_fontComboBox.currentFont()
            legend_font = self.plot1DFont_fontComboBox.currentFont()
            if self.plot1DTitleFontSize_LE.text():
                title_font.setPointSize(int(self.plot1DTitleFontSize_LE.text()))
            if self.plot1DAxisFontSize_LE.text():
                axis_font.setPointSize(int(self.plot1DAxisFontSize_LE.text()))
            if self.plot1DTickFontSize_LE.text():
                tick_font.setPointSize(int(self.plot1DTickFontSize_LE.text()))
            if self.plot1DLegendFontSize_LE.text():
                legend_font.setPointSize(int(self.plot1DLegendFontSize_LE.text()))
            title = customPlot.plotLayout().element(0, 0)
            if title:
                title.setFont(title_font)
            customPlot.legend.setFont(legend_font)
            customPlot.xAxis.setLabelFont(axis_font)
            customPlot.yAxis.setLabelFont(axis_font)
            customPlot.xAxis2.setLabelFont(axis_font)
            customPlot.yAxis2.setLabelFont(axis_font)
            customPlot.xAxis.setTickLabelFont(tick_font)
            customPlot.yAxis.setTickLabelFont(tick_font)
            customPlot.xAxis2.setTickLabelFont(tick_font)
            customPlot.yAxis2.setTickLabelFont(tick_font)

        customPlot.replot()

    def _override_range(self, line_edit: QtWidgets.QLineEdit, current: float) -> float:
        text = line_edit.text()
        if text:
            try:
                value = float(text)
                if not math.isnan(value):
                    return value
            except ValueError:
                pass
        return current

    def slotOpenFile_scalar(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Input", "", "Input (*.*)")
        if not file_path:
            return
        suffix = QtCore.QFileInfo(file_path).suffix().lower()
        if suffix != "vtk":
            self.columns = self.loadData(file_path)
            self.inputTab.setCurrentIndex(0)
            self.data2Dx = self.tempX == 1
            self.data2Dy = self.tempY == 1
            self.data2Dz = self.tempZ == 1

            self.scalar_CB.setCheckState(QtCore.Qt.Checked)
            self.volume_CB.setCheckState(QtCore.Qt.Checked)
            self.vector_CB.setCheckState(QtCore.Qt.Unchecked)
            self.domain_CB.setCheckState(QtCore.Qt.Unchecked)

            file_info = QtCore.QFileInfo(file_path)
            self.scalarDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

            self.scalarChoice.clear()
            for i in range(self.columns):
                self.outputScalar(self.scalarDir.absoluteFilePath(), i, self.xmax, self.ymax, self.zmax)
                self.scalarChoice.addItem(str(i + 1))

            self.inputFileScalar.setText(file_info.fileName())
            self.rowcolScalar.setText(str(self.columns))
            self.xMinMaxScalar.setText(f"1 - {self.xmax + 1}")
            self.yMinMaxScalar.setText(f"1 - {self.ymax + 1}")
            self.zMinMaxScalar.setText(f"1 - {self.zmax + 1}")

            self.scalar_Table.clearContents()
            while self.scalar_Table.rowCount() > 0:
                self.scalar_Table.removeRow(0)
            for i in range(self.columns):
                col_values = [row[i] for row in self.vtk_data]
                self.scalar_Table.insertRow(self.scalar_Table.rowCount())
                self.scalar_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(self.getMin(col_values))))
                self.scalar_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(self.getMax(col_values))))
                self.scalar_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(self.getAvg(col_values))))

            self.scalarName = f"{self.scalarDir.absoluteFilePath()}.{self.scalarChoice.currentIndex()+1}.vtk"
            self.updateVTK(self.scalarName, self.vectorName)
            self.vtk_data = []
        else:
            self.columns = 1
            self.scalarChoice.clear()
            self.scalarChoice.addItem("1")
            self.scalar_Table.clearContents()
            while self.scalar_Table.rowCount() > 0:
                self.scalar_Table.removeRow(0)
            self.scalar_CB.setCheckState(QtCore.Qt.Checked)
            self.volume_CB.setCheckState(QtCore.Qt.Checked)
            self.vector_CB.setCheckState(QtCore.Qt.Unchecked)
            self.domain_CB.setCheckState(QtCore.Qt.Unchecked)
            self.xmax = 10
            self.ymax = 10
            self.zmax = 10
            self.scalarName = file_path
            self.updateVTK(self.scalarName, self.vectorName)

    def on_scalarChoice_currentIndexChanged(self, _index: int) -> None:
        if self.scalarChoice.count() <= 0:
            return
        base = self.scalarDir.absoluteFilePath()
        if base:
            self.scalarName = f"{base}.{self.scalarChoice.currentIndex()+1}.vtk"
        self.updateFlag = False
        if self.stackedWidget.currentIndex() == 0 and self.scalar_CB.isChecked():
            self.slotUpdate()

    def slotOpenFile_vector(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Input", "", "Input (*.*)")
        if not file_path:
            return
        suffix = QtCore.QFileInfo(file_path).suffix().lower()
        if suffix != "vtk":
            self.columns = self.loadData(file_path)
            self.inputTab.setCurrentIndex(1)
            file_info = QtCore.QFileInfo(file_path)
            self.vectorDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

            self.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
            self.volume_CB.setCheckState(QtCore.Qt.Unchecked)
            self.vector_CB.setCheckState(QtCore.Qt.Checked)
            self.vectorGlyph_CB.setCheckState(QtCore.Qt.Checked)
            self.domain_CB.setCheckState(QtCore.Qt.Unchecked)

            self.vectorChoice.clear()
            for i in range(self.columns // 3):
                self.outputVector(
                    self.vectorDir.absoluteFilePath(), 3 * i, 3 * i + 1, 3 * i + 2, self.xmax, self.ymax, self.zmax
                )
                self.vectorChoice.addItem(f"{3*i+1}{3*i+2}{3*i+3}")

            self.inputFileVector.setText(file_info.fileName())
            self.rowcolVector.setText(str(self.columns))
            self.xMinMaxVector.setText(f"1 - {self.xmax + 1}")
            self.yMinMaxVector.setText(f"1 - {self.ymax + 1}")
            self.zMinMaxVector.setText(f"1 - {self.zmax + 1}")

            self.vector_Table.clearContents()
            while self.vector_Table.rowCount() > 0:
                self.vector_Table.removeRow(0)
            for i in range(self.columns):
                col_values = [row[i] for row in self.vtk_data]
                self.vector_Table.insertRow(self.vector_Table.rowCount())
                self.vector_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(self.getMin(col_values))))
                self.vector_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(self.getMax(col_values))))
                self.vector_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(self.getAvg(col_values))))

            magnitudes = [
                math.sqrt(row[0] * row[0] + row[1] * row[1] + row[2] * row[2])
                for row in self.vtk_data
            ]
            if magnitudes:
                self.vectorValueMin_LE.setText(str(min(magnitudes)))
                self.vectorValueMax_LE.setText(str(max(magnitudes)))
                if max(magnitudes) != 0:
                    self.vectorScale_LE.setText(str(5 / max(magnitudes)))

            index = self.vectorChoice.currentIndex()
            self.vectorName = (
                f"{self.vectorDir.absoluteFilePath()}.{3*index+1}{3*index+2}{3*index+3}.vtk"
            )
            self.updateVTK(self.scalarName, self.vectorName)
            self.vtk_data = []
        else:
            self.columns = 3
            self.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
            self.volume_CB.setCheckState(QtCore.Qt.Unchecked)
            self.vector_CB.setCheckState(QtCore.Qt.Checked)
            self.vectorGlyph_CB.setCheckState(QtCore.Qt.Checked)
            self.domain_CB.setCheckState(QtCore.Qt.Unchecked)
            self.vectorScale_LE.setText("1")
            self.vectorChoice.clear()
            self.vectorChoice.addItem("123")
            self.xmax = 10
            self.ymax = 10
            self.zmax = 10
            self.vectorName = file_path
            self.updateVTK(self.scalarName, self.vectorName)

    def on_vectorChoice_currentIndexChanged(self, index) -> None:
        if self.vectorChoice.count() <= 0:
            return
        try:
            index_value = int(index)
        except (TypeError, ValueError):
            index_value = self.vectorChoice.currentIndex()
        base = self.vectorDir.absoluteFilePath()
        if base:
            self.vectorName = (
                f"{base}.{3*index_value+1}{3*index_value+2}{3*index_value+3}.vtk"
            )
        self.updateFlag = False
        if self.stackedWidget.currentIndex() == 0 and self.vector_CB.isChecked():
            self.slotUpdate()

    def slotOpenFile_domain(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Input", "", "Input (*.*)")
        if not file_path:
            return
        switch_control = self.domain_Combo.currentIndex()
        if switch_control == 0:
            domain_dialog = DomainCriteria(self)
            if domain_dialog.exec() == QtWidgets.QDialog.Accepted:
                self.domainStandardAngle = domain_dialog.getDomainStdAngle()
                self.domainStandardAngleRad = self.domainStandardAngle * PI_VALUE / 180.0
                self.domainStandardValue = domain_dialog.getDomainStdValue()
                self.domainStdAngle_LE.setText(str(self.domainStandardAngle))
                self.domainStdValue_LE.setText(str(self.domainStandardValue))

                self.columns = self.loadData(file_path)
                self.inputTab.setCurrentIndex(2)
                self.existDomain = [False] * 27
                file_info = QtCore.QFileInfo(file_path)
                self.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
                self.volume_CB.setCheckState(QtCore.Qt.Unchecked)
                self.vector_CB.setCheckState(QtCore.Qt.Unchecked)
                self.domain_CB.setCheckState(QtCore.Qt.Checked)
                self.domainDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

                self.outputDomain(self.domainDir.absoluteFilePath(), self.xmax, self.ymax, self.zmax)
                self.inputFileDomain.setText(file_info.fileName())
                self.rowcolDomain.setText(str(self.columns))
                self.xMinMaxDomain.setText(f"1 - {self.xmax + 1}")
                self.yMinMaxDomain.setText(f"1 - {self.ymax + 1}")
                self.zMinMaxDomain.setText(f"1 - {self.zmax + 1}")

                self.domain_Table.clearContents()
                while self.domain_Table.rowCount() > 0:
                    self.domain_Table.removeRow(0)
                for i in range(self.columns):
                    col_values = [row[i] for row in self.vtk_data]
                    self.domain_Table.insertRow(self.domain_Table.rowCount())
                    self.domain_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(self.getMin(col_values))))
                    self.domain_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(self.getMax(col_values))))
                    self.domain_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(self.getAvg(col_values))))

                self.domainName = f"{self.domainDir.absoluteFilePath()}.domain.vtk"
                self.drawDomain(self.domainName)
        elif switch_control == 1:
            vo2_dialog = VO2Criteria(self)
            if vo2_dialog.exec() == QtWidgets.QDialog.Accepted:
                self.M1mod = vo2_dialog.getM1_mod()
                self.M1ang = vo2_dialog.getM1_ang() * PI_VALUE / 180.0
                self.M2mod = vo2_dialog.getM2_mod()
                self.M2ang = vo2_dialog.getM2_ang() * PI_VALUE / 180.0
                self.vo2_M1_mod_LE.setText(str(self.M1mod))
                self.vo2_M1_ang_LE.setText(str(self.M1ang * 180.0 / PI_VALUE))
                self.vo2_M2_mod_LE.setText(str(self.M2mod))
                self.vo2_M2_ang_LE.setText(str(self.M2ang * 180.0 / PI_VALUE))
                self.columns = self.loadData(file_path)
                self.inputTab.setCurrentIndex(2)
                self.existDomain = [False] * 27
                file_info = QtCore.QFileInfo(file_path)
                self.scalar_CB.setCheckState(QtCore.Qt.Unchecked)
                self.volume_CB.setCheckState(QtCore.Qt.Unchecked)
                self.vector_CB.setCheckState(QtCore.Qt.Unchecked)
                self.domain_CB.setCheckState(QtCore.Qt.Checked)
                self.domainDir = QtCore.QFileInfo(file_info.absolutePath() + "/" + file_info.completeBaseName())

                self.outputVO2Domain(self.domainDir.absoluteFilePath(), self.xmax, self.ymax, self.zmax)
                self.domainName = f"{self.domainDir.absoluteFilePath()}.domain.vtk"
                self.drawVO2Domain(self.domainName)

    def loadData(self, file_path: str) -> int:
        self.updateFlag = False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if len(lines) < 2:
            return 0
        line1 = lines[0].strip()
        line2 = lines[1].strip()
        count1 = len(line1.split())
        count2 = len(line2.split())

        x = y = z = 0
        if count1 != count2:
            parts = line1.split()
            if len(parts) >= 3:
                x, y, z = map(int, parts[:3])
            data_lines = lines[1:]
        else:
            last_line = lines[-1].strip()
            parts = last_line.split()
            if len(parts) >= 3:
                x, y, z = map(int, parts[:3])
            data_lines = lines

        column_number = count2 - 3
        row_number = x * y * z
        self.vtk_data = []
        for line in data_lines[:row_number]:
            parts = line.split()
            if len(parts) < 3 + column_number:
                continue
            row = [float(value) for value in parts[3 : 3 + column_number]]
            self.vtk_data.append(row)

        self.tempX = x
        self.tempY = y
        self.tempZ = z
        self.updateExtraction(x, y, z)
        return column_number

    def updateExtraction(self, x: int, y: int, z: int) -> None:
        if self.xmaxAll < x - 1:
            self.xmaxAll = x - 1
        if self.ymaxAll < y - 1:
            self.ymaxAll = y - 1
        if self.zmaxAll < z - 1:
            self.zmaxAll = z - 1
        self.xminAll = 0
        self.yminAll = 0
        self.zminAll = 0
        self.xmax = x - 1
        self.ymax = y - 1
        self.zmax = z - 1
        self.xmin = 0
        self.ymin = 0
        self.zmin = 0

        self.xmin_LE.setText(str(self.xminAll + 1))
        self.ymin_LE.setText(str(self.yminAll + 1))
        self.zmin_LE.setText(str(self.zminAll + 1))
        self.xmax_LE.setText(str(self.xmaxAll + 1))
        self.ymax_LE.setText(str(self.ymaxAll + 1))
        self.zmax_LE.setText(str(self.zmaxAll + 1))

        total_points = (self.xmaxAll - self.xminAll + 1) * (self.ymaxAll - self.yminAll + 1) * (self.zmaxAll - self.zminAll + 1)
        interval = 1
        if self.xminAll != self.xmaxAll and self.yminAll != self.ymaxAll and self.zminAll != self.zmaxAll:
            if total_points > 1000000:
                interval = math.ceil((total_points / 1000000.0) ** (1 / 3.0))
        else:
            if total_points > 1000000:
                interval = math.ceil((total_points / 1000000.0) ** (1 / 2.0))
        self.xDelta_LE.setText(str(interval))
        self.yDelta_LE.setText(str(interval))
        self.zDelta_LE.setText(str(interval))

    def outputScalar(self, path: str, column_number: int, x: int, y: int, z: int) -> None:
        if self.data2Dx:
            x += 2
        else:
            x += 1
        if self.data2Dy:
            y += 2
        else:
            y += 1
        if self.data2Dz:
            z += 2
        else:
            z += 1
        row_number = x * y * z
        out_path = f"{path}.{column_number+1}.vtk"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# vtk DataFile Version 3.0\n")
            f.write("Structured Points\n")
            f.write("ASCII\n\n")
            f.write("DATASET STRUCTURED_POINTS\n")
            f.write(f"DIMENSIONS {x} {y} {z}\n")
            f.write("ORIGIN 0 0 0\n")
            f.write(
                f"SPACING {self.rescaleX_LE.text()} {self.rescaleY_LE.text()} {self.rescaleZ_LE.text()}\n\n"
            )
            f.write(f"POINT_DATA {row_number}\n")
            f.write("SCALARS scalar float\n")
            f.write("LOOKUP_TABLE default\n")
            for m in range(z):
                for n in range(y):
                    for w in range(x):
                        if self.data2Dx or self.data2Dy or self.data2Dz:
                            if self.data2Dx:
                                value = self.vtk_data[n * z + m][column_number]
                            elif self.data2Dy:
                                value = self.vtk_data[w * (y - 1) * z + m][column_number]
                            else:
                                value = self.vtk_data[w * y * (z - 1) + n * (z - 1)][column_number]
                        else:
                            value = self.vtk_data[w * y * z + n * z + m][column_number]
                        f.write(f"{value:14.6e}\n")
        self.scalarName = out_path

    def outputVector(self, path: str, colX: int, colY: int, colZ: int, x: int, y: int, z: int) -> None:
        x += 1
        y += 1
        z += 1
        row_number = x * y * z
        out_path = f"{path}.{colX+1}{colY+1}{colZ+1}.vtk"
        magnitude = [0.0] * row_number
        xy_magnitude = [0.0] * row_number
        z_magnitude = [0.0] * row_number
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# vtk DataFile Version 3.0\n")
            f.write("Structured Points\n")
            f.write("ASCII\n\n")
            f.write("DATASET STRUCTURED_POINTS\n")
            f.write(f"DIMENSIONS {x} {y} {z}\n")
            f.write("ORIGIN 0 0 0\n")
            f.write(
                f"SPACING {self.rescaleX_LE.text()} {self.rescaleY_LE.text()} {self.rescaleZ_LE.text()}\n\n"
            )
            f.write(f"POINT_DATA {row_number}\n")
            f.write("SCALARS Magnitude float \n")
            f.write("LOOKUP_TABLE default \n")
            for m in range(z):
                for n in range(y):
                    for w in range(x):
                        idx = w * y * z + n * z + m
                        value = math.sqrt(
                            self.vtk_data[idx][colX] ** 2
                            + self.vtk_data[idx][colY] ** 2
                            + self.vtk_data[idx][colZ] ** 2
                        )
                        f.write(f"{value:14.6e}\n")
            f.write("\n")
            f.write("VECTORS vector float\n")
            for m in range(z):
                for n in range(y):
                    for w in range(x):
                        idx = w * y * z + n * z + m
                        vx = self.vtk_data[idx][colX]
                        vy = self.vtk_data[idx][colY]
                        vz = self.vtk_data[idx][colZ]
                        f.write(f"{vx:14.6e} {vy:14.6e} {vz:14.6e}\n")
                        magnitude[idx] = math.sqrt(vx * vx + vy * vy + vz * vz)
                        xy_magnitude[idx] = math.sqrt(vx * vx + vy * vy)
                        z_magnitude[idx] = vz

            magnitude_range = [0.0, max(magnitude) if magnitude else 1.0]
            xy_range = [0.0, max(xy_magnitude) if xy_magnitude else 1.0]
            z_range = [-magnitude_range[1], magnitude_range[1]]

            f.write("\n")
            f.write("VECTORS RGB unsigned_char\n")
            for m in range(z):
                for n in range(y):
                    for w in range(x):
                        idx = w * y * z + n * z + m
                        rgb = self.getRGB(
                            self.vtk_data[idx][colX],
                            self.vtk_data[idx][colY],
                            self.vtk_data[idx][colZ],
                            magnitude_range,
                            xy_range,
                            z_range,
                        )
                        f.write(f"{rgb[0]:.0f} {rgb[1]:.0f} {rgb[2]:.0f}\n")
        self.vectorName = out_path

    def convertHSLToRGB(self, hue: float, saturation: float, lightness: float) -> List[float]:
        if saturation <= 1.0e-6:
            return [lightness * 255, lightness * 255, lightness * 255]
        if lightness < 0.5:
            v2 = lightness * (1 + saturation)
        else:
            v2 = (lightness + saturation) - (saturation * lightness)
        v1 = 2 * lightness - v2

        def hue_to_rgb(v1_: float, v2_: float, vH: float) -> float:
            if vH < 0:
                vH += 1
            if vH > 1:
                vH -= 1
            if (6 * vH) < 1:
                return v1_ + (v2_ - v1_) * 6 * vH
            if (2 * vH) < 1:
                return v2_
            if (3 * vH) < 2:
                return v1_ + (v2_ - v1_) * ((2 / 3.0) - vH) * 6
            return v1_

        return [
            255 * hue_to_rgb(v1, v2, hue / 360.0 + (1 / 3.0)),
            255 * hue_to_rgb(v1, v2, hue / 360.0),
            255 * hue_to_rgb(v1, v2, hue / 360.0 - (1 / 3.0)),
        ]

    def rescale(self, value: float, value_range: List[float]) -> float:
        if value_range[1] - value_range[0] < 1.0e-6:
            return 0.5
        if value <= value_range[0]:
            return 0.0
        if value >= value_range[1]:
            return 1.0
        return (value - value_range[0]) / (value_range[1] - value_range[0])

    def _set_threshold_between(self, threshold, lower: float, upper: float) -> None:
        if hasattr(threshold, "ThresholdBetween"):
            threshold.ThresholdBetween(lower, upper)
            return
        if hasattr(threshold, "SetLowerThreshold"):
            threshold.SetLowerThreshold(lower)
        if hasattr(threshold, "SetUpperThreshold"):
            threshold.SetUpperThreshold(upper)
        if hasattr(threshold, "SetThresholdFunction"):
            mode = getattr(threshold, "THRESHOLD_BETWEEN", None)
            if mode is None and hasattr(vtk, "vtkThreshold"):
                mode = getattr(vtk.vtkThreshold, "THRESHOLD_BETWEEN", None)
            if mode is not None:
                threshold.SetThresholdFunction(mode)

    def getRGB(
        self,
        px: float,
        py: float,
        pz: float,
        magnitude_range: List[float],
        xy_range: List[float],
        z_range: List[float],
    ) -> List[float]:
        xy_magnitude = math.sqrt(px * px + py * py)
        if xy_magnitude < 1.0e-6:
            hue = 0.0
            saturation = 0.0
            lightness = self.rescale(pz, z_range)
        else:
            if py >= 0:
                hue = math.acos(px / xy_magnitude) / PI_VALUE * 180
            else:
                hue = 360 - (math.acos(px / xy_magnitude) / PI_VALUE * 180)
            magnitude = math.sqrt(px * px + py * py + pz * pz)
            saturation = self.rescale(magnitude, magnitude_range)
            lightness = (pz / magnitude + 1) / 2.0 if magnitude != 0 else 0.5
        return self.convertHSLToRGB(hue, saturation, lightness)

    def _safe_int_from_lineedit(self, edit: QtWidgets.QLineEdit, default_value: int) -> int:
        text = edit.text().strip()
        if not text:
            return default_value
        try:
            return int(text)
        except ValueError:
            try:
                return int(float(text))
            except ValueError:
                return default_value

    def _get_clamped_extraction_voi(self, extent: tuple[int, int, int, int, int, int]) -> tuple[int, int, int, int, int, int]:
        xmin_ui = self._safe_int_from_lineedit(self.xmin_LE, extent[0] + 1)
        xmax_ui = self._safe_int_from_lineedit(self.xmax_LE, extent[1] + 1)
        ymin_ui = self._safe_int_from_lineedit(self.ymin_LE, extent[2] + 1)
        ymax_ui = self._safe_int_from_lineedit(self.ymax_LE, extent[3] + 1)
        zmin_ui = self._safe_int_from_lineedit(self.zmin_LE, extent[4] + 1)
        zmax_ui = self._safe_int_from_lineedit(self.zmax_LE, extent[5] + 1)

        use_zero_based_input = min(xmin_ui, xmax_ui, ymin_ui, ymax_ui, zmin_ui, zmax_ui) <= 0
        if use_zero_based_input:
            xmin, xmax = xmin_ui, xmax_ui
            ymin, ymax = ymin_ui, ymax_ui
            zmin, zmax = zmin_ui, zmax_ui
        else:
            xmin, xmax = xmin_ui - 1, xmax_ui - 1
            ymin, ymax = ymin_ui - 1, ymax_ui - 1
            zmin, zmax = zmin_ui - 1, zmax_ui - 1

        xmin = max(extent[0], min(xmin, extent[1]))
        xmax = max(extent[0], min(xmax, extent[1]))
        ymin = max(extent[2], min(ymin, extent[3]))
        ymax = max(extent[2], min(ymax, extent[3]))
        zmin = max(extent[4], min(zmin, extent[5]))
        zmax = max(extent[4], min(zmax, extent[5]))

        if xmin > xmax:
            xmin, xmax = xmax, xmin
        if ymin > ymax:
            ymin, ymax = ymax, ymin
        if zmin > zmax:
            zmin, zmax = zmax, zmin

        self.xminAll, self.xmaxAll = xmin, xmax
        self.yminAll, self.ymaxAll = ymin, ymax
        self.zminAll, self.zmaxAll = zmin, zmax

        self.xmin_LE.setText(str(xmin + 1))
        self.xmax_LE.setText(str(xmax + 1))
        self.ymin_LE.setText(str(ymin + 1))
        self.ymax_LE.setText(str(ymax + 1))
        self.zmin_LE.setText(str(zmin + 1))
        self.zmax_LE.setText(str(zmax + 1))

        return xmin, xmax, ymin, ymax, zmin, zmax

    def updateVTK(self, scalarname: str, vectorname: str) -> None:
        fileNameScalar = scalarname
        fileNameVector = vectorname
        self._pointProbeScalarReader = None
        self._pointProbeScalarExtractor = None
        self._pointProbeScalarOutput = None
        self._pointProbeScalarColumn = None
        self._clear_point_probe_vector_dataset()

        renderer = vtk.vtkRenderer()
        if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
            self.qvtkWidget.GetRenderWindow().AddRenderer(renderer)
        else:
            renderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()

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
        renderer.AddActor(self.actorScalar)
        renderer.AddActor(self.actorVector)

        if fileNameScalar and os.path.isfile(fileNameScalar) and self.scalar_CB.isChecked():
            readerScalarOrigin = vtk.vtkStructuredPointsReader()
            readerScalarOrigin.SetFileName(fileNameScalar)
            readerScalarOrigin.Update()
            readerScalarOrigin.GetOutput().SetSpacing(
                float(self.rescaleX_LE.text() or 1),
                float(self.rescaleY_LE.text() or 1),
                float(self.rescaleZ_LE.text() or 1),
            )
            scalar_range = readerScalarOrigin.GetOutput().GetPointData().GetScalars().GetRange()

            readerScalar = vtk.vtkExtractVOI()
            readerScalar.SetInputConnection(readerScalarOrigin.GetOutputPort())
            scalar_extent = tuple(int(v) for v in readerScalarOrigin.GetOutput().GetExtent())
            if self.extract_CB.checkState():
                scalar_voi = self._get_clamped_extraction_voi(scalar_extent)
                readerScalar.SetVOI(*scalar_voi)
                ruler_extent = scalar_voi
            else:
                readerScalar.SetVOI(scalar_extent)
                ruler_extent = scalar_extent
            readerScalar.Update()
            self._pointProbeScalarReader = readerScalarOrigin
            self._pointProbeScalarExtractor = readerScalar
            self._pointProbeScalarOutput = readerScalar.GetOutput()
            self._pointProbeScalarColumn = self.scalarChoice.currentIndex() + 1 if self.scalarChoice.count() else 1

            if self.scalarRange_CB.isChecked():
                vmin = float(self.scalarValueMin_LE.text() or scalar_range[0])
                vmax = float(self.scalarValueMax_LE.text() or scalar_range[1])
                thresholdScalar = vtk.vtkThreshold()
                thresholdScalar.SetInputConnection(readerScalar.GetOutputPort())
                self._set_threshold_between(thresholdScalar, vmin, vmax)
                tetra = vtk.vtkDataSetTriangleFilter()
                tetra.SetInputConnection(thresholdScalar.GetOutputPort())
                mapperScalar = vtk.vtkUnstructuredGridVolumeRayCastMapper()
                mapperScalar.SetInputConnection(tetra.GetOutputPort())
                self.actorScalar.SetMapper(mapperScalar)
            else:
                mapperScalar = vtk.vtkSmartVolumeMapper()
                mapperScalar.SetInputConnection(readerScalar.GetOutputPort())
                mapperScalar.SetRequestedRenderModeToRayCast()
                self.actorScalar.SetMapper(mapperScalar)

            if self.isosurface_CB.isChecked():
                self.drawIsoSurface(readerScalar.GetOutputPort())

            if self.scalar_CB.checkState() == 0 or self.volume_CB.checkState() == 0:
                self.actorScalar.SetVisibility(False)
            else:
                self.actorScalar.SetVisibility(True)

            cutterScalar = vtk.vtkCutter()
            plane = vtk.vtkPlane()
            cutterScalar.SetInputConnection(readerScalar.GetOutputPort())
            if self.data2Dx or self.data2Dy or self.data2Dz:
                plane.SetOrigin(0, 0, 0)
                if self.data2Dx:
                    plane.SetNormal(1, 0, 0)
                elif self.data2Dy:
                    plane.SetNormal(0, 1, 0)
                else:
                    plane.SetNormal(0, 0, 1)
                cutterScalar.SetCutFunction(plane)
                self.actorCutter.SetVisibility(True)
            else:
                plane.SetOrigin(
                    float(self.sliceOriginX.text() or 0),
                    float(self.sliceOriginY.text() or 0),
                    float(self.sliceOriginZ.text() or 0),
                )
                plane.SetNormal(
                    float(self.sliceNormalX.text() or 0),
                    float(self.sliceNormalY.text() or 0),
                    float(self.sliceNormalZ.text() or 1),
                )
                cutterScalar.SetCutFunction(plane)
                self.actorCutter.SetVisibility(bool(self.slice_CB.checkState()))

            cutterMapper = vtk.vtkPolyDataMapper()
            cutterMapper.SetInputConnection(cutterScalar.GetOutputPort())
            self.actorCutter.SetMapper(cutterMapper)
            renderer.AddActor(self.actorCutter)

            outlineScalar = vtk.vtkOutlineFilter()
            outlineScalar.SetInputConnection(readerScalar.GetOutputPort())
            outlineScalarMapper = vtk.vtkDataSetMapper()
            outlineScalarMapper.SetInputConnection(outlineScalar.GetOutputPort())
            self.outlineScalarActor.SetMapper(outlineScalarMapper)
            self.outlineScalarActor.GetProperty().SetColor(0, 0, 0)
            self.outlineScalarActor.GetProperty().SetLineWidth(self.outlineWidth)
            renderer.AddActor(self.outlineScalarActor)

        if fileNameVector and os.path.isfile(fileNameVector) and self.vector_CB.isChecked():
            if not self.updateFlag:
                self.readerVectorOrigin.ReadAllVectorsOn()
                self.readerVectorOrigin.SetFileName(fileNameVector)
            self.readerVectorOrigin.Update()
            self.readerVectorOrigin.GetOutput().SetSpacing(
                float(self.rescaleX_LE.text() or 1),
                float(self.rescaleY_LE.text() or 1),
                float(self.rescaleZ_LE.text() or 1),
            )
            vectors = self.readerVectorOrigin.GetOutput().GetPointData().GetVectors()
            if vectors is not None:
                vector_range = list(vectors.GetRange(-1))
            else:
                vector_range = [0.0, 0.0]
            self.readerVectorOrigin.GetOutput().GetPointData().SetActiveVectors("vector")

            readerVector = vtk.vtkExtractVOI()
            readerVector.SetInputConnection(self.readerVectorOrigin.GetOutputPort())
            readerVector.SetSampleRate(
                int(self.xDelta_LE.text() or 1),
                int(self.yDelta_LE.text() or 1),
                int(self.zDelta_LE.text() or 1),
            )
            vector_extent = tuple(int(v) for v in self.readerVectorOrigin.GetOutput().GetExtent())
            if self.extract_CB.checkState():
                vector_voi = self._get_clamped_extraction_voi(vector_extent)
                readerVector.SetVOI(*vector_voi)
                if ruler_extent is None:
                    ruler_extent = vector_voi
            else:
                vector_voi = vector_extent
                readerVector.SetVOI(vector_extent)
                if ruler_extent is None:
                    ruler_extent = vector_extent
            readerVector.Update()
            self._update_point_probe_vector_dataset(vector_voi)

            maskVector = vtk.vtkMaskPoints()
            maskVector.SetInputConnection(readerVector.GetOutputPort())
            if not self.vectorMaskNum_LE.text().strip():
                self.vectorMaskNum_LE.setText("5000")
            mask_num = int(float(self.vectorMaskNum_LE.text()))
            maskVector.SetMaximumNumberOfPoints(mask_num)
            if self.xmax and self.ymax and self.zmax:
                maskVector.SetOnRatio(max(1, int(self.xmax * self.ymax * self.zmax / mask_num)))
            maskVector.SetRandomMode(1)
            maskVector.Update()

            glyphVector = vtk.vtkGlyph3D()
            arrowVector = vtk.vtkArrowSource()
            translateHalf = vtk.vtkTransform()
            translateHalf.Translate(-0.5, 0, 0)
            glyphVector.SetSourceTransform(translateHalf)
            glyphVector.SetSourceConnection(arrowVector.GetOutputPort())
            if self.vectorRange_CB.isChecked():
                vector_range = [
                    float(self.vectorValueMin_LE.text() or vector_range[0]),
                    float(self.vectorValueMax_LE.text() or vector_range[1]),
                ]
                thresholdVector = vtk.vtkThresholdPoints()
                thresholdVector.SetInputConnection(maskVector.GetOutputPort())
                self._set_threshold_between(thresholdVector, vector_range[0], vector_range[1])
                glyphVector.SetInputConnection(thresholdVector.GetOutputPort())
            else:
                glyphVector.SetInputConnection(maskVector.GetOutputPort())
            glyphVector.SetInputArrayToProcess(1, 0, 0, 0, "vector")
            glyphVector.SetColorModeToColorByVector()
            glyphVector.OrientOn()
            glyphVector.SetVectorModeToUseVector()
            glyphVector.SetScaleModeToScaleByVector()
            glyphVector.SetScaleFactor(float(self.vectorScale_LE.text() or 1))
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

            color_mode_index = self.vectorColorMode_Combo.currentIndex()
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
                vector_index = self.vectorChoice.currentIndex()
                row = vector_index * 3 + color_mode_index - 1
                if 0 <= row < self.vector_Table.rowCount():
                    min_item = self.vector_Table.item(row, 0)
                    max_item = self.vector_Table.item(row, 1)
                    if min_item is not None and max_item is not None:
                        vector_range = [float(min_item.text()), float(max_item.text())]

            mapperVector.SetLookupTable(colorVector)
            mapperVector.SetScalarRange(vector_range)
            mapperVector.Update()
            vector_mapper = mapperVector

            self.actorVector.SetMapper(mapperVector)
            self.actorVector.SetVisibility(self.vectorGlyph_CB.checkState() != 0)

            outlineVector = vtk.vtkOutlineFilter()
            outlineVector.SetInputConnection(readerVector.GetOutputPort())
            outlineVectorMapper = vtk.vtkDataSetMapper()
            outlineVectorMapper.SetInputConnection(outlineVector.GetOutputPort())
            self.outlineVectorActor.SetMapper(outlineVectorMapper)
            self.outlineVectorActor.GetProperty().SetColor(0, 0, 0)
            self.outlineVectorActor.GetProperty().SetLineWidth(self.outlineWidth)
            renderer.AddActor(self.outlineVectorActor)

            if self.streamline_CB.isChecked():
                vectorSeed = vtk.vtkPointSource()
                vectorSeed.SetCenter(
                    float(self.seedCenterX_LE.text() or 0),
                    float(self.seedCenterY_LE.text() or 0),
                    float(self.seedCenterZ_LE.text() or 0),
                )
                vectorSeed.SetNumberOfPoints(int(float(self.seedNumber_LE.text() or 10)))
                vectorSeed.SetRadius(float(self.seedRadius_LE.text() or 1))
                stream = vtk.vtkStreamTracer()
                stream.SetSourceConnection(vectorSeed.GetOutputPort())
                stream.SetInputConnection(readerVector.GetOutputPort())
                stream.SetMaximumPropagation(float(self.streamStepLength_LE.text() or 1))
                stream.SetIntegrationDirectionToForward()
                streamMapper = vtk.vtkDataSetMapper()
                streamMapper.SetInputConnection(stream.GetOutputPort())
                self.actorStream.SetMapper(streamMapper)
                renderer.AddActor(self.actorStream)

        if self.alpha_Combo.currentIndex() == 0:
            opacityScalar.AddPoint(scalar_range[0], 1.0)
            opacityScalar.AddPoint((scalar_range[0] + scalar_range[1]) / 2, 0)
            opacityScalar.AddPoint(scalar_range[1], 1.0)
            opacityVector.AddPoint(vector_range[0], 1.0)
            opacityVector.AddPoint((vector_range[0] + vector_range[1]) / 2, 0)
            opacityVector.AddPoint(vector_range[1], 1.0)
        else:
            for i in range(self.alphaScalar_Table.rowCount()):
                value = float(self.alphaScalar_Table.item(i, 0).text())
                alpha = float(self.alphaScalar_Table.item(i, 1).text())
                opacityScalar.AddPoint(value, alpha)
            for i in range(self.alphaVector_Table.rowCount()):
                value = float(self.alphaVector_Table.item(i, 0).text())
                alpha = float(self.alphaVector_Table.item(i, 1).text())
                opacityVector.AddPoint(value, alpha)

        if self.RGB_Combo.currentIndex() == 0:
            colorScalar.AddRGBPoint(scalar_range[0], 0.0, 0.0, 1.0)
            colorScalar.AddRGBPoint((scalar_range[0] + scalar_range[1]) / 2, 0, 1, 0)
            colorScalar.AddRGBPoint(scalar_range[1], 1.0, 0.0, 0.0)
            colorVector.AddRGBPoint(vector_range[0], 0.0, 0.0, 1.0)
            colorVector.AddRGBPoint((vector_range[0] + vector_range[1]) / 2, 0, 1, 0)
            colorVector.AddRGBPoint(vector_range[1], 1.0, 0.0, 0.0)
        else:
            for i in range(self.RGBScalar_Table.rowCount()):
                rgb_value = float(self.RGBScalar_Table.item(i, 0).text())
                r = float(self.RGBScalar_Table.item(i, 1).text()) / 255
                g = float(self.RGBScalar_Table.item(i, 2).text()) / 255
                b = float(self.RGBScalar_Table.item(i, 3).text()) / 255
                colorScalar.AddRGBPoint(rgb_value, r, g, b)
            for i in range(self.RGBVector_Table.rowCount()):
                rgb_value = float(self.RGBVector_Table.item(i, 0).text())
                r = float(self.RGBVector_Table.item(i, 1).text()) / 255
                g = float(self.RGBVector_Table.item(i, 2).text()) / 255
                b = float(self.RGBVector_Table.item(i, 3).text()) / 255
                colorVector.AddRGBPoint(rgb_value, r, g, b)
        colorScalar.Build()
        colorVector.Build()
        if vector_mapper is not None:
            vector_mapper.SetLookupTable(colorVector)
            vector_mapper.SetScalarRange(vector_range)
            vector_mapper.Update()

        if self.volume_CB.checkState():
            volume_property = vtk.vtkVolumeProperty()
            volume_property.SetScalarOpacity(opacityScalar)
            volume_property.SetColor(colorScalar)
            volume_property.SetInterpolationTypeToNearest()
            self.actorScalar.SetProperty(volume_property)

        self.widget.SetOutlineColor(0.93, 0.57, 0.13)
        self.widget.SetOrientationMarker(self.axes)
        self.widget.SetInteractor(self.qvtkWidget.GetRenderWindow().GetInteractor())
        self.widget.SetViewport(0.0, 0.0, 0.2, 0.2)
        self.widget.SetEnabled(1)
        self.widget.InteractiveOn()

        self.scalarScaleBarActor.SetLookupTable(colorScalar)
        self.scalarScaleBarActor.SetTitle(self.scalarLegend_LE.text())
        self.scalarScaleBarActor.SetNumberOfLabels(3)
        self.scalarScaleBarActor.SetMaximumWidthInPixels(80)
        self.scalarScaleBarActor.GetTitleTextProperty().SetColor(0, 0, 0)
        self.scalarScaleBarActor.GetTitleTextProperty().SetJustificationToLeft()
        self.scalarScaleBarActor.GetLabelTextProperty().SetColor(0, 0, 0)
        self.scalarScaleBarActor.DrawTickLabelsOn()
        self.scalarScaleBarActor.UseOpacityOn()
        self.scalarLegendWidget.SetInteractor(self.qvtkWidget.GetRenderWindow().GetInteractor())
        self.scalarLegendWidget.SetScalarBarActor(self.scalarScaleBarActor)
        self.scalarLegendWidget.ResizableOn()
        self.scalarLegendWidget.On()

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
                rgb_value = self.getRGB(normal[0], normal[1], normal[2], [0, 1], [0, 1], [-1, 1])
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
        self.vectorRTActor.SetMapper(vectorRTMapper)
        self.vectorOrientationLegend.SetOutlineColor(0.93, 0.57, 0.13)
        self.vectorOrientationLegend.SetOrientationMarker(self.vectorRTActor)
        self.vectorOrientationLegend.SetInteractor(self.qvtkWidget.GetRenderWindow().GetInteractor())
        self.vectorOrientationLegend.SetViewport(0.8, 0.4, 1.0, 0.6)
        self.vectorOrientationLegend.SetEnabled(1)
        self.vectorOrientationLegend.InteractiveOn()

        self.vectorScaleBarActor.SetLookupTable(colorVector)
        self.vectorScaleBarActor.SetTitle(self.vectorLegend_LE.text())
        self.vectorScaleBarActor.SetNumberOfLabels(3)
        self.vectorScaleBarActor.SetMaximumWidthInPixels(80)
        self.vectorScaleBarActor.GetTitleTextProperty().SetColor(0, 0, 0)
        self.vectorScaleBarActor.GetLabelTextProperty().SetColor(0, 0, 0)
        self.vectorScaleBarActor.UseOpacityOn()
        self.vectorLegendWidget.SetInteractor(self.qvtkWidget.GetRenderWindow().GetInteractor())
        self.vectorLegendWidget.SetScalarBarActor(self.vectorScaleBarActor)
        self.vectorLegendWidget.On()

        if self.outline_CB.checkState():
            self.outlineScalarActor.SetVisibility(self.scalar_CB.checkState() != 0)
            self.outlineVectorActor.SetVisibility(self.vector_CB.checkState() != 0)
        else:
            self.outlineScalarActor.SetVisibility(False)
            self.outlineVectorActor.SetVisibility(False)

        if self.axis_CB.checkState():
            self.widget.On()
        else:
            self.widget.Off()

        if self.scalarLegendBar_CB.checkState():
            self.scalarLegendWidget.On()
            self.scalarScaleBarActor.SetVisibility(True)
        else:
            self.scalarLegendWidget.Off()
            self.scalarScaleBarActor.SetVisibility(False)

        if self.vectorLegendBar_CB.checkState():
            if self.vectorColorMode_Combo.currentIndex() == 4:
                self.vectorOrientationLegend.On()
                self.vectorRTActor.SetVisibility(True)
                self.vectorLegendWidget.Off()
                self.vectorScaleBarActor.SetVisibility(False)
            else:
                self.vectorLegendWidget.On()
                self.vectorScaleBarActor.SetVisibility(True)
                self.vectorOrientationLegend.Off()
                self.vectorRTActor.SetVisibility(False)
        else:
            self.vectorLegendWidget.Off()
            self.vectorOrientationLegend.Off()
            self.vectorRTActor.SetVisibility(False)
            self.vectorScaleBarActor.SetVisibility(False)

        self._update_coordinate_ruler(renderer, ruler_extent)

        if self.reset:
            self.updateCamera(-1)
            self.reset = False
        else:
            self.updateCamera(0)

        self._refresh_point_probe_source()
        if self.pointProbe_CB is not None and self.pointProbe_CB.isChecked():
            self._set_point_probe_hint()

    def updateCamera(self, choice: int) -> None:
        renderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()
        if choice == -1:
            renderer.ResetCamera()
        elif choice == 1:
            self.camera.SetPosition(-100, 0, 0)
            self.camera.SetFocalPoint(0, 0, 0)
            self.camera.SetViewUp(0, 0, 1)
        elif choice == 2:
            self.camera.SetPosition(100, 0, 0)
            self.camera.SetFocalPoint(0, 0, 0)
            self.camera.SetViewUp(0, 0, 1)
        elif choice == 3:
            self.camera.SetPosition(0, -100, 0)
            self.camera.SetFocalPoint(0, 0, 0)
            self.camera.SetViewUp(0, 0, 1)
        elif choice == 4:
            self.camera.SetPosition(0, 100, 0)
            self.camera.SetFocalPoint(0, 0, 0)
            self.camera.SetViewUp(0, 0, 1)
        elif choice == 5:
            self.camera.SetPosition(0, 0, -100)
            self.camera.SetFocalPoint(0, 0, 0)
            self.camera.SetViewUp(0, 1, 0)
        elif choice == 6:
            self.camera.SetPosition(0, 0, 100)
            self.camera.SetFocalPoint(0, 0, 0)
            self.camera.SetViewUp(0, 1, 0)
        renderer.SetActiveCamera(self.camera)
        self.coordRulerActor.SetCamera(renderer.GetActiveCamera())
        self.qvtkWidget.GetRenderWindow().Render()
        self.qvtkWidget.update()
        self.camera = renderer.GetActiveCamera()
        self.reset = False

    def on_axis_CB_stateChanged(self, state: int) -> None:
        if state:
            self.widget.On()
        else:
            self.widget.Off()
        self.qvtkWidget.GetRenderWindow().Render()

    def on_coordRuler_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        if (
            enabled
            and self.stackedWidget.currentIndex() == 0
            and (
                (self.scalarName and os.path.isfile(self.scalarName))
                or (self.vectorName and os.path.isfile(self.vectorName))
                or (self.domainName and os.path.isfile(self.domainName))
            )
        ):
            self.slotUpdate()
            return
        self.coordRulerActor.SetVisibility(enabled and self.stackedWidget.currentIndex() == 0)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_pointProbe_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        if not enabled:
            self._reset_point_probe_display()
            return
        self._refresh_point_probe_source()
        self._set_point_probe_hint()

    def on_outline_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        if self.scalar_CB.checkState():
            self.outlineScalarActor.SetVisibility(enabled)
        else:
            self.outlineScalarActor.SetVisibility(False)
        if self.vector_CB.checkState():
            self.outlineVectorActor.SetVisibility(enabled)
        else:
            self.outlineVectorActor.SetVisibility(False)
        if self.domain_CB.checkState():
            self.outlineDomainActor.SetVisibility(enabled)
        self.outlineWidth_LB.setEnabled(enabled)
        self.outlineWidth_LE.setEnabled(enabled)
        self.outlinePx_LB.setEnabled(enabled)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_scalar_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.scalarChoice.setEnabled(enabled)
        self.volume_CB.setEnabled(enabled)
        self.scalarColumn_LB.setEnabled(enabled)
        self.slice_CB.setEnabled(enabled)
        self.isosurface_CB.setEnabled(enabled)
        self.scalarLegendBar_CB.setEnabled(enabled)
        self.scalarLegend_LE.setEnabled(enabled)
        self.scalarRange_CB.setEnabled(False)
        self.scalarValueMin_LE.setEnabled(False)
        self.scalarValueMax_LE.setEnabled(False)
        self.scalarTo_LB.setEnabled(False)
        self.slicePoint_LB.setEnabled(False)
        self.sliceNormal_LB.setEnabled(False)
        self.sliceNormalX.setEnabled(False)
        self.sliceNormalY.setEnabled(False)
        self.sliceNormalZ.setEnabled(False)
        self.sliceOriginX.setEnabled(False)
        self.sliceOriginY.setEnabled(False)
        self.sliceOriginZ.setEnabled(False)
        self.isoValue_LB.setEnabled(False)
        self.isoValue_LE.setEnabled(False)
        self.isoAdd_PB.setEnabled(False)
        self.isoDelete_PB.setEnabled(False)
        self.isosurfaces_LB.setEnabled(False)
        self.isosurface_LW.setEnabled(False)

        if enabled:
            if self.volume_CB.isChecked():
                self.scalarRange_CB.setEnabled(True)
                if self.scalarRange_CB.isChecked():
                    self.scalarValueMin_LE.setEnabled(True)
                    self.scalarValueMax_LE.setEnabled(True)
                    self.scalarTo_LB.setEnabled(True)
            if self.slice_CB.isChecked():
                self.slicePoint_LB.setEnabled(True)
                self.sliceNormal_LB.setEnabled(True)
                self.sliceNormalX.setEnabled(True)
                self.sliceNormalY.setEnabled(True)
                self.sliceNormalZ.setEnabled(True)
                self.sliceOriginX.setEnabled(True)
                self.sliceOriginY.setEnabled(True)
                self.sliceOriginZ.setEnabled(True)
            if self.isosurface_CB.isChecked():
                self.isoValue_LB.setEnabled(True)
                self.isoValue_LE.setEnabled(True)
                self.isoAdd_PB.setEnabled(True)
                self.isoDelete_PB.setEnabled(True)
                self.isosurfaces_LB.setEnabled(True)
                self.isosurface_LW.setEnabled(True)

        if state == 0 or self.volume_CB.checkState() == 0:
            self.actorScalar.SetVisibility(False)
        else:
            self.actorScalar.SetVisibility(True)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_volume_CB_stateChanged(self, state: int) -> None:
        if state == 0:
            self.scalarRange_CB.setEnabled(False)
            self.scalarValueMin_LE.setEnabled(False)
            self.scalarValueMax_LE.setEnabled(False)
            self.scalarTo_LB.setEnabled(False)
        else:
            self.scalarRange_CB.setEnabled(True)
            if self.scalarRange_CB.isChecked():
                self.scalarValueMin_LE.setEnabled(True)
                self.scalarValueMax_LE.setEnabled(True)
                self.scalarTo_LB.setEnabled(True)
            else:
                self.scalarValueMin_LE.setEnabled(False)
                self.scalarValueMax_LE.setEnabled(False)
                self.scalarTo_LB.setEnabled(False)
        if state == 0 or self.scalar_CB.checkState() == 0:
            self.actorScalar.SetVisibility(False)
        else:
            self.actorScalar.SetVisibility(True)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_vector_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.vectorChoice.setEnabled(enabled)
        self.vector_LB.setEnabled(enabled)
        self.vectorGlyph_CB.setEnabled(enabled)
        self.streamline_CB.setEnabled(enabled)
        self.vectorLegend_LE.setEnabled(enabled)
        self.vectorLegendBar_CB.setEnabled(enabled)
        self.vectorColorMode_Combo.setEnabled(enabled)
        self.vectorColorMode_LB.setEnabled(enabled)

        if not enabled:
            self.vectorValueMin_LE.setEnabled(False)
            self.vectorValueMax_LE.setEnabled(False)
            self.vectorTo_LB.setEnabled(False)
            self.vectorMaskNum_LE.setEnabled(False)
            self.vectorMaxPoints_LB.setEnabled(False)
            self.vectorScale_LB.setEnabled(False)
            self.vectorScale_LE.setEnabled(False)
            self.vectorRange_CB.setEnabled(False)
            self.streamStepLength_LE.setEnabled(False)
            self.seedNumber_LE.setEnabled(False)
            self.seedRadius_LE.setEnabled(False)
            self.seedCenterX_LE.setEnabled(False)
            self.seedCenterY_LE.setEnabled(False)
            self.seedCenterZ_LE.setEnabled(False)
            self.streamSeedNum_LB.setEnabled(False)
            self.streamSeedCenter_LB.setEnabled(False)
            self.streamMaxLength_LB.setEnabled(False)
            self.streamSampleRadius_LB.setEnabled(False)
            self.xDelta_LE.setEnabled(False)
            self.yDelta_LE.setEnabled(False)
            self.zDelta_LE.setEnabled(False)
            self.xDelta_LB.setEnabled(False)
            self.yDelta_LB.setEnabled(False)
            self.zDelta_LB.setEnabled(False)
            self.sampleRate_LB.setEnabled(False)
        else:
            if self.vectorGlyph_CB.isChecked():
                self.vectorMaskNum_LE.setEnabled(True)
                self.vectorMaxPoints_LB.setEnabled(True)
                self.vectorScale_LB.setEnabled(True)
                self.vectorScale_LE.setEnabled(True)
                self.vectorRange_CB.setEnabled(True)
                self.xDelta_LE.setEnabled(True)
                self.yDelta_LE.setEnabled(True)
                self.zDelta_LE.setEnabled(True)
                self.xDelta_LB.setEnabled(True)
                self.yDelta_LB.setEnabled(True)
                self.zDelta_LB.setEnabled(True)
                self.sampleRate_LB.setEnabled(True)
                if self.vectorRange_CB.isChecked():
                    self.vectorValueMin_LE.setEnabled(True)
                    self.vectorValueMax_LE.setEnabled(True)
                    self.vectorTo_LB.setEnabled(True)
                else:
                    self.vectorValueMin_LE.setEnabled(False)
                    self.vectorValueMax_LE.setEnabled(False)
                    self.vectorTo_LB.setEnabled(False)
            else:
                self.vectorMaskNum_LE.setEnabled(False)
                self.vectorMaxPoints_LB.setEnabled(False)
                self.vectorScale_LB.setEnabled(False)
                self.vectorScale_LE.setEnabled(False)
                self.vectorRange_CB.setEnabled(False)
                self.vectorValueMin_LE.setEnabled(False)
                self.vectorValueMax_LE.setEnabled(False)
                self.vectorTo_LB.setEnabled(False)

            if self.streamline_CB.isChecked():
                self.streamStepLength_LE.setEnabled(True)
                self.seedNumber_LE.setEnabled(True)
                self.seedRadius_LE.setEnabled(True)
                self.seedCenterX_LE.setEnabled(True)
                self.seedCenterY_LE.setEnabled(True)
                self.seedCenterZ_LE.setEnabled(True)
                self.streamSeedNum_LB.setEnabled(True)
                self.streamSeedCenter_LB.setEnabled(True)
                self.streamMaxLength_LB.setEnabled(True)
                self.streamSampleRadius_LB.setEnabled(True)
            else:
                self.streamStepLength_LE.setEnabled(False)
                self.seedNumber_LE.setEnabled(False)
                self.seedRadius_LE.setEnabled(False)
                self.seedCenterX_LE.setEnabled(False)
                self.seedCenterY_LE.setEnabled(False)
                self.seedCenterZ_LE.setEnabled(False)
                self.streamSeedNum_LB.setEnabled(False)
                self.streamSeedCenter_LB.setEnabled(False)
                self.streamMaxLength_LB.setEnabled(False)
                self.streamSampleRadius_LB.setEnabled(False)

        if state == 0:
            self.actorVector.SetVisibility(False)
        else:
            self.actorVector.SetVisibility(True)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_vectorGlyph_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.vectorMaskNum_LE.setEnabled(enabled)
        self.vectorMaxPoints_LB.setEnabled(enabled)
        self.vectorScale_LB.setEnabled(enabled)
        self.vectorScale_LE.setEnabled(enabled)
        self.vectorRange_CB.setEnabled(enabled)
        self.xDelta_LE.setEnabled(enabled)
        self.yDelta_LE.setEnabled(enabled)
        self.zDelta_LE.setEnabled(enabled)
        self.xDelta_LB.setEnabled(enabled)
        self.yDelta_LB.setEnabled(enabled)
        self.zDelta_LB.setEnabled(enabled)
        self.sampleRate_LB.setEnabled(enabled)
        if enabled and self.vectorRange_CB.isChecked():
            self.vectorValueMin_LE.setEnabled(True)
            self.vectorValueMax_LE.setEnabled(True)
            self.vectorTo_LB.setEnabled(True)
        else:
            self.vectorValueMin_LE.setEnabled(False)
            self.vectorValueMax_LE.setEnabled(False)
            self.vectorTo_LB.setEnabled(False)
        if state == 0 or self.vector_CB.checkState() == 0:
            self.actorVector.SetVisibility(False)
        else:
            self.actorVector.SetVisibility(True)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_vectorRange_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.vectorValueMin_LE.setEnabled(enabled)
        self.vectorValueMax_LE.setEnabled(enabled)
        self.vectorTo_LB.setEnabled(enabled)

    def on_vectorMaskNum_LE_editingFinished(self) -> None:
        if not self.vectorMaskNum_LE.text().strip():
            self.vectorMaskNum_LE.setText("5000")
        if (
            self.stackedWidget.currentIndex() == 0
            and self.vector_CB.checkState() != 0
            and self.vectorGlyph_CB.checkState() != 0
        ):
            self.slotUpdate()

    def on_streamline_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.streamStepLength_LE.setEnabled(enabled)
        self.seedNumber_LE.setEnabled(enabled)
        self.seedRadius_LE.setEnabled(enabled)
        self.seedCenterX_LE.setEnabled(enabled)
        self.seedCenterY_LE.setEnabled(enabled)
        self.seedCenterZ_LE.setEnabled(enabled)
        self.streamSeedNum_LB.setEnabled(enabled)
        self.streamSeedCenter_LB.setEnabled(enabled)
        self.streamMaxLength_LB.setEnabled(enabled)
        self.streamSampleRadius_LB.setEnabled(enabled)
        self.actorStream.SetVisibility(enabled)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_extract_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.xmin_LE.setEnabled(enabled)
        self.xmax_LE.setEnabled(enabled)
        self.ymin_LE.setEnabled(enabled)
        self.ymax_LE.setEnabled(enabled)
        self.zmin_LE.setEnabled(enabled)
        self.zmax_LE.setEnabled(enabled)

    def _refresh_after_extraction_edit(self) -> None:
        if self.stackedWidget.currentIndex() != 0 or not self.extract_CB.isChecked():
            return
        has_visual_data = (
            (self.scalar_CB.isChecked() and self.scalarName and os.path.isfile(self.scalarName))
            or (self.vector_CB.isChecked() and self.vectorName and os.path.isfile(self.vectorName))
            or (self.domain_CB.isChecked() and self.domainName and os.path.isfile(self.domainName))
        )
        if has_visual_data:
            self.slotUpdate()

    def on_xmin_LE_editingFinished(self) -> None:
        self._refresh_after_extraction_edit()

    def on_xmax_LE_editingFinished(self) -> None:
        self._refresh_after_extraction_edit()

    def on_ymin_LE_editingFinished(self) -> None:
        self._refresh_after_extraction_edit()

    def on_ymax_LE_editingFinished(self) -> None:
        self._refresh_after_extraction_edit()

    def on_zmin_LE_editingFinished(self) -> None:
        self._refresh_after_extraction_edit()

    def on_zmax_LE_editingFinished(self) -> None:
        self._refresh_after_extraction_edit()

    def on_scalarRange_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.scalarValueMin_LE.setEnabled(enabled)
        self.scalarValueMax_LE.setEnabled(enabled)
        self.scalarTo_LB.setEnabled(enabled)

    def on_scalarLegendBar_CB_stateChanged(self, state: int) -> None:
        if state:
            self.scalarLegendWidget.On()
            self.scalarScaleBarActor.SetVisibility(True)
        else:
            self.scalarLegendWidget.Off()
            self.scalarScaleBarActor.SetVisibility(False)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_vectorLegendBar_CB_stateChanged(self, state: int) -> None:
        if state:
            if self.vectorColorMode_Combo.currentIndex() == 4:
                self.vectorOrientationLegend.On()
                self.vectorRTActor.SetVisibility(True)
                self.vectorLegendWidget.Off()
                self.vectorScaleBarActor.SetVisibility(False)
            else:
                self.vectorLegendWidget.On()
                self.vectorScaleBarActor.SetVisibility(True)
                self.vectorOrientationLegend.Off()
                self.vectorRTActor.SetVisibility(False)
        else:
            self.vectorLegendWidget.Off()
            self.vectorOrientationLegend.Off()
            self.vectorRTActor.SetVisibility(False)
            self.vectorScaleBarActor.SetVisibility(False)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_scalarLegend_LE_textChanged(self, text: str) -> None:
        if self.scalarScaleBarActor:
            self.scalarScaleBarActor.SetTitle(text)

    def on_vectorLegend_LE_textChanged(self, text: str) -> None:
        if self.vectorScaleBarActor:
            self.vectorScaleBarActor.SetTitle(text)

    def on_RGBAdd_PB_released(self) -> None:
        index = self.RGB_Combo.currentIndex()
        if index == 0:
            return
        if not self.RGBR_LE.text() or not self.RGBG_LE.text() or not self.RGBB_LE.text():
            return

        if index == 1 and self.RGBValue_LE.text():
            row = self.RGBScalar_Table.rowCount()
            self.RGBScalar_Table.insertRow(row)
            self.RGBScalar_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(self.RGBValue_LE.text()))
            self.RGBScalar_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.RGBR_LE.text()))
            self.RGBScalar_Table.setItem(row, 2, QtWidgets.QTableWidgetItem(self.RGBG_LE.text()))
            self.RGBScalar_Table.setItem(row, 3, QtWidgets.QTableWidgetItem(self.RGBB_LE.text()))
            self.RGBScalar_Table.sortItems(0, QtCore.Qt.AscendingOrder)
        elif index == 2 and self.RGBValue_LE.text():
            row = self.RGBVector_Table.rowCount()
            self.RGBVector_Table.insertRow(row)
            self.RGBVector_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(self.RGBValue_LE.text()))
            self.RGBVector_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.RGBR_LE.text()))
            self.RGBVector_Table.setItem(row, 2, QtWidgets.QTableWidgetItem(self.RGBG_LE.text()))
            self.RGBVector_Table.setItem(row, 3, QtWidgets.QTableWidgetItem(self.RGBB_LE.text()))
            self.RGBVector_Table.sortItems(0, QtCore.Qt.AscendingOrder)
        elif index == 3 and self.isoValue_Combo.count() > 0:
            row = self.RGBIso_Table.rowCount()
            item = self.isoValue_Combo.currentText()
            for i in range(self.RGBIso_Table.rowCount()):
                if self.RGBIso_Table.item(i, 0).text() == item:
                    return
            self.RGBIso_Table.insertRow(row)
            self.RGBIso_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(item))
            self.RGBIso_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.RGBR_LE.text()))
            self.RGBIso_Table.setItem(row, 2, QtWidgets.QTableWidgetItem(self.RGBG_LE.text()))
            self.RGBIso_Table.setItem(row, 3, QtWidgets.QTableWidgetItem(self.RGBB_LE.text()))
            self.RGBIso_Table.sortItems(0, QtCore.Qt.AscendingOrder)
        elif index == 4:
            row = self.RGBDomain_Table.rowCount()
            if self.domain_Combo.currentIndex() == 0:
                item = self.RGBDomain_Combo.currentText()
            else:
                item = self.vo2RGB_Combo.currentText()
            for i in range(self.RGBDomain_Table.rowCount()):
                if self.RGBDomain_Table.item(i, 0).text() == item:
                    return
            self.RGBDomain_Table.insertRow(row)
            self.RGBDomain_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(item))
            self.RGBDomain_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.RGBR_LE.text()))
            self.RGBDomain_Table.setItem(row, 2, QtWidgets.QTableWidgetItem(self.RGBG_LE.text()))
            self.RGBDomain_Table.setItem(row, 3, QtWidgets.QTableWidgetItem(self.RGBB_LE.text()))

    def on_RGBDelete_PB_released(self) -> None:
        stack_index = self.RGB_Stack.currentIndex()
        if stack_index == 0:
            self.RGBScalar_Table.removeRow(self.RGBScalar_Table.currentRow())
        elif stack_index == 1:
            self.RGBVector_Table.removeRow(self.RGBVector_Table.currentRow())
        elif stack_index == 2:
            self.RGBIso_Table.removeRow(self.RGBIso_Table.currentRow())
        elif stack_index == 3:
            self.RGBDomain_Table.removeRow(self.RGBDomain_Table.currentRow())

    def on_RGB_Combo_currentIndexChanged(self, index: int) -> None:
        self.RGBValue_LE.setEnabled(False)
        self.RGBR_LE.setEnabled(True)
        self.RGBG_LE.setEnabled(True)
        self.RGBB_LE.setEnabled(True)
        self.RGBValue_LB.setEnabled(True)
        self.isoValue_Combo.setEnabled(False)
        self.RGBDomain_Combo.setEnabled(False)
        if index == 0:
            self.RGBR_LE.setEnabled(False)
            self.RGBG_LE.setEnabled(False)
            self.RGBB_LE.setEnabled(False)
            self.RGBValue_LB.setEnabled(False)
            self.RGBScalar_Table.setEnabled(False)
            self.RGBVector_Table.setEnabled(False)
            self.RGBIso_Table.setEnabled(False)
            self.RGBDomain_Table.setEnabled(False)
        elif index == 1:
            self.RGB_Stack.setCurrentIndex(0)
            self.RGBIso_SW.setCurrentIndex(0)
            self.RGBValue_LE.setEnabled(True)
            self.RGBScalar_Table.setEnabled(True)
        elif index == 2:
            self.RGBIso_SW.setCurrentIndex(0)
            self.RGB_Stack.setCurrentIndex(1)
            self.RGBValue_LE.setEnabled(True)
            self.RGBVector_Table.setEnabled(True)
        elif index == 3:
            self.RGBIso_SW.setCurrentIndex(1)
            self.RGB_Stack.setCurrentIndex(2)
            self.isoValue_Combo.setEnabled(True)
            self.RGBIso_Table.setEnabled(True)
        elif index == 4:
            self.RGBIso_SW.setCurrentIndex(2)
            self.RGB_Stack.setCurrentIndex(3)
            self.domainColor_Stack.setCurrentIndex(0)
            self.RGBDomain_Table.setEnabled(True)
            self.domainColor_Combo.setEnabled(True)
            self.RGBDomain_Combo.setEnabled(True)

    def on_alpha_Combo_currentIndexChanged(self, index: int) -> None:
        if index == 0:
            self.alphaValue_LE.setEnabled(False)
            self.alpha_LE.setEnabled(False)
            self.alphaScalar_Table.setEnabled(False)
            self.alphaVector_Table.setEnabled(False)
            self.domainAlpha_Combo.setEnabled(False)
            self.alphaDomain_Table.setEnabled(False)
            self.alpha_Stack.setEnabled(False)
        else:
            self.alphaValue_LE.setEnabled(True)
            self.alpha_LE.setEnabled(True)
            self.alphaScalar_Table.setEnabled(True)
            self.domainAlpha_Combo.setEnabled(True)
            self.alphaDomain_Table.setEnabled(True)
            self.alpha_Stack.setEnabled(True)
            if index == 1:
                self.alpha_Stack.setCurrentIndex(0)
                self.alphaValue_Stack.setCurrentIndex(0)
            elif index == 2:
                self.alpha_Stack.setCurrentIndex(1)
                self.alphaValue_Stack.setCurrentIndex(1)

    def on_alphaAdd_PB_released(self) -> None:
        if not self.alpha_LE.text():
            return
        if self.alpha_Stack.currentIndex() == 0 and self.alphaValue_LE.text():
            row = self.alphaScalar_Table.rowCount()
            self.alphaScalar_Table.insertRow(row)
            self.alphaScalar_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(self.alphaValue_LE.text()))
            self.alphaScalar_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.alpha_LE.text()))
            self.alphaScalar_Table.sortItems(0, QtCore.Qt.AscendingOrder)
        elif self.alpha_Stack.currentIndex() == 1:
            row = self.alphaDomain_Table.rowCount()
            self.alphaDomain_Table.insertRow(row)
            self.alphaDomain_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(self.domainAlpha_Combo.currentText()))
            self.alphaDomain_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.alpha_LE.text()))
            self.alphaDomain_Table.sortItems(0, QtCore.Qt.AscendingOrder)
        elif self.alpha_Stack.currentIndex() == 2:
            row = self.alphaVector_Table.rowCount()
            self.alphaVector_Table.insertRow(row)
            self.alphaVector_Table.setItem(row, 0, QtWidgets.QTableWidgetItem(self.alphaValue_LE.text()))
            self.alphaVector_Table.setItem(row, 1, QtWidgets.QTableWidgetItem(self.alpha_LE.text()))
            self.alphaVector_Table.sortItems(0, QtCore.Qt.AscendingOrder)

    def on_alphaDelete_PB_released(self) -> None:
        if self.alpha_Stack.currentIndex() == 0:
            self.alphaScalar_Table.removeRow(self.alphaScalar_Table.currentRow())
        elif self.alpha_Stack.currentIndex() == 1:
            self.alphaDomain_Table.removeRow(self.alphaDomain_Table.currentRow())
        elif self.alpha_Stack.currentIndex() == 2:
            self.alphaVector_Table.removeRow(self.alphaVector_Table.currentRow())

    def on_domainStdAngle_LE_editingFinished(self) -> None:
        try:
            self.domainStandardAngle = float(self.domainStdAngle_LE.text())
            self.domainStandardAngleRad = self.domainStandardAngle * PI_VALUE / 180.0
        except ValueError:
            return

    def on_domainStdValue_LE_editingFinished(self) -> None:
        try:
            self.domainStandardValue = float(self.domainStdValue_LE.text())
        except ValueError:
            return

    def on_domainRePlot_PB_released(self) -> None:
        if not self.domainDir.exists():
            return
        if self.domain_Combo.currentIndex() == 0:
            self.domainStandardAngle = float(self.domainStdAngle_LE.text() or self.domainStandardAngle)
            self.domainStandardAngleRad = self.domainStandardAngle * PI_VALUE / 180.0
            self.domainStandardValue = float(self.domainStdValue_LE.text() or self.domainStandardValue)
            self.existDomain = [False] * 27
            self.outputDomain(self.domainDir.absoluteFilePath(), self.xmax, self.ymax, self.zmax)
            self.domainName = f"{self.domainDir.absoluteFilePath()}.domain.vtk"
            self.drawDomain(self.domainName)
        else:
            self.outputVO2Domain(self.domainDir.absoluteFilePath(), self.xmax, self.ymax, self.zmax)
            self.domainName = f"{self.domainDir.absoluteFilePath()}.domain.vtk"
            self.drawVO2Domain(self.domainName)

    def on_outlineWidth_LE_editingFinished(self) -> None:
        try:
            self.outlineWidth = int(self.outlineWidth_LE.text())
        except ValueError:
            self.outlineWidth = 1

    def on_domain_Combo_currentIndexChanged(self, index: int) -> None:
        self.domain_stack.setCurrentIndex(index)
        self.domainCriteria_Stack.setCurrentIndex(index)

    def on_domainColor_Combo_currentIndexChanged(self, index: int) -> None:
        self.domainColor_Stack.setCurrentIndex(index)

    def on_opacityDomain_Combo_currentIndexChanged(self, index: int) -> None:
        self.opacityDomain_Stack.setCurrentIndex(index)

    def on_vectorColorMode_Combo_currentIndexChanged(self, _index: int) -> None:
        return

    def on_plot1DGeneral_LW_currentRowChanged(self, index: int) -> None:
        self.plot1DGeneral_SW.setCurrentIndex(index)

    def on_plot1DXGrid_CB_stateChanged(self, state: int) -> None:
        self.customPlot.xAxis.grid().setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DYGrid_CB_stateChanged(self, state: int) -> None:
        self.customPlot.yAxis.grid().setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DAutoTickX1_CB_stateChanged(self, state: int) -> None:
        enabled = not bool(state)
        self.plot1DTickValueX1_LE.setEnabled(enabled)
        self.plot1DTickLabelX1_LE.setEnabled(enabled)

    def on_plot1DAutoTickX2_CB_stateChanged(self, state: int) -> None:
        enabled = not bool(state)
        self.plot1DTickValueX2_LE.setEnabled(enabled)
        self.plot1DTickLabelX2_LE.setEnabled(enabled)

    def on_plot1DAutoTickY1_CB_stateChanged(self, state: int) -> None:
        enabled = not bool(state)
        self.plot1DTickValueY1_LE.setEnabled(enabled)
        self.plot1DTickLabelY1_LE.setEnabled(enabled)

    def on_plot1DAutoTickY2_CB_stateChanged(self, state: int) -> None:
        enabled = not bool(state)
        self.plot1DTickValueY2_LE.setEnabled(enabled)
        self.plot1DTickLabelY2_LE.setEnabled(enabled)

    def on_plot1DAxisX1_CB_stateChanged(self, state: int) -> None:
        self.customPlot.xAxis.setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DAxisX2_CB_stateChanged(self, state: int) -> None:
        self.customPlot.xAxis2.setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DAxisY1_CB_stateChanged(self, state: int) -> None:
        self.customPlot.yAxis.setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DAxisY2_CB_stateChanged(self, state: int) -> None:
        self.customPlot.yAxis2.setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DTickLabelX1_CB_stateChanged(self, state: int) -> None:
        self.customPlot.xAxis.setTickLabels(bool(state))
        self.customPlot.replot()

    def on_plot1DTickLabelY1_CB_stateChanged(self, state: int) -> None:
        self.customPlot.yAxis.setTickLabels(bool(state))
        self.customPlot.replot()

    def on_plot1DTickLabelX2_CB_stateChanged(self, state: int) -> None:
        self.customPlot.xAxis2.setTickLabels(bool(state))
        self.customPlot.replot()

    def on_plot1DTickLabelY2_CB_stateChanged(self, state: int) -> None:
        self.customPlot.yAxis2.setTickLabels(bool(state))
        self.customPlot.replot()

    def on_plot1DLegend_CB_stateChanged(self, state: int) -> None:
        self.customPlot.legend.setVisible(bool(state))
        self.customPlot.replot()

    def on_plot1DFont_CB_stateChanged(self, state: int) -> None:
        enabled = not bool(state)
        self.plot1DFont_fontComboBox.setEnabled(enabled)
        self.plot1DTitleFontSize_LE.setEnabled(enabled)
        self.plot1DAxisFontSize_LE.setEnabled(enabled)
        self.plot1DTickFontSize_LE.setEnabled(enabled)
        self.plot1DLegendFontSize_LE.setEnabled(enabled)

    def on_slice_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        self.slicePoint_LB.setEnabled(enabled)
        self.sliceNormal_LB.setEnabled(enabled)
        self.sliceNormalX.setEnabled(enabled)
        self.sliceNormalY.setEnabled(enabled)
        self.sliceNormalZ.setEnabled(enabled)
        self.sliceOriginX.setEnabled(enabled)
        self.sliceOriginY.setEnabled(enabled)
        self.sliceOriginZ.setEnabled(enabled)

    def on_domain_CB_stateChanged(self, state: int) -> None:
        self.domain_TW.setEnabled(bool(state))
        self.outlineDomainActor.SetVisibility(bool(state))
        for i in range(27):
            self.actorDomain[i].SetVisibility(bool(state))
        self.qvtkWidget.GetRenderWindow().Render()

    def on_domain_TW_itemChanged(self, item: QtWidgets.QTableWidgetItem) -> None:
        row = self.domain_TW.row(item)
        if row == 0:
            for j in range(31):
                self.domain_TW.item(j, 0).setCheckState(
                    QtCore.Qt.Checked if item.checkState() else QtCore.Qt.Unchecked
                )
        elif row == 1:
            for j in range(5, 13):
                self.domain_TW.item(j, 0).setCheckState(
                    QtCore.Qt.Checked if item.checkState() else QtCore.Qt.Unchecked
                )
        elif row == 2:
            for j in range(13, 25):
                self.domain_TW.item(j, 0).setCheckState(
                    QtCore.Qt.Checked if item.checkState() else QtCore.Qt.Unchecked
                )
        elif row == 3:
            for j in range(25, 31):
                self.domain_TW.item(j, 0).setCheckState(
                    QtCore.Qt.Checked if item.checkState() else QtCore.Qt.Unchecked
                )
        else:
            idx = row - 4
            if 0 <= idx < len(self.actorDomain):
                self.actorDomain[idx].SetVisibility(item.checkState() == QtCore.Qt.Checked)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_vo2Domain_LW_itemChanged(self, item: QtWidgets.QListWidgetItem) -> None:
        idx = self.vo2Domain_LW.row(item)
        if 0 <= idx < len(self.actorDomain):
            self.actorDomain[idx].SetVisibility(item.checkState() == QtCore.Qt.Checked)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_isosurface_CB_stateChanged(self, state: int) -> None:
        enabled = bool(state)
        index = self.RGB_Combo.currentIndex()
        if index == 3:
            self.RGBIso_SW.setEnabled(True)
            self.isoValue_Combo.setEnabled(enabled)
            self.RGBValue_LE.setEnabled(enabled)
            self.RGBR_LE.setEnabled(enabled)
            self.RGBG_LE.setEnabled(enabled)
            self.RGBB_LE.setEnabled(enabled)
            self.RGBIso_Table.setEnabled(enabled)
            self.RGB_Stack.setEnabled(enabled)
        self.isoValue_LE.setEnabled(enabled)
        self.isoValue_LB.setEnabled(enabled)
        self.isoAdd_PB.setEnabled(enabled)
        self.isoDelete_PB.setEnabled(enabled)
        self.isosurface_LW.setEnabled(enabled)
        self.isosurfaces_LB.setEnabled(enabled)
        for actor in self.actorIso:
            actor.SetVisibility(enabled)

    def on_isoAdd_PB_released(self) -> None:
        text = self.isoValue_LE.text()
        if not text:
            return
        items = self.isosurface_LW.findItems(text, QtCore.Qt.MatchExactly)
        if items:
            return
        self.actorIso.append(vtk.vtkActor())
        row = self.isosurface_LW.count()
        self.isosurface_LW.insertItem(row, text)
        item = self.isosurface_LW.item(row)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.Checked)
        self.isoValue_Combo.addItem(text)

    def on_isosurface_LW_itemChanged(self, item: QtWidgets.QListWidgetItem) -> None:
        idx = self.isosurface_LW.row(item)
        if 0 <= idx < len(self.actorIso):
            self.actorIso[idx].SetVisibility(item.checkState() == QtCore.Qt.Checked)
        self.qvtkWidget.GetRenderWindow().Render()

    def on_isoDelete_PB_released(self) -> None:
        if not self.isosurface_LW.selectedItems():
            return
        row = self.isosurface_LW.currentRow()
        if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() != 0 and row < len(self.actorIso):
            renderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()
            renderer.RemoveActor(self.actorIso[row])
        if row < len(self.actorIso):
            self.actorIso.pop(row)
        text = self.isosurface_LW.currentItem().text()
        combo_row = self.isoValue_Combo.findText(text)
        if combo_row >= 0:
            self.isoValue_Combo.removeItem(combo_row)
        self.isosurface_LW.takeItem(row)
        items = self.RGBIso_Table.findItems(text, QtCore.Qt.MatchExactly)
        for item in items:
            if self.RGBIso_Table.column(item) == 0:
                self.RGBIso_Table.removeRow(self.RGBIso_Table.row(item))
                break
        self.qvtkWidget.GetRenderWindow().Render()

    def drawIsoSurface(self, readerScalarPort) -> None:
        if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
            return
        isoRenderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()
        contour_num = self.isosurface_LW.count()
        for i in range(contour_num):
            contour = vtk.vtkMarchingCubes()
            contour.SetInputConnection(readerScalarPort)
            contour.SetValue(0, float(self.isosurface_LW.item(i).text()))
            contour.ComputeNormalsOn()
            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputConnection(contour.GetOutputPort())
            if i < len(self.actorIso):
                self.actorIso[i].SetMapper(mapper)
                isoRenderer.RemoveActor(self.actorIso[i])
                isoRenderer.AddActor(self.actorIso[i])

        for i in range(self.RGBIso_Table.rowCount()):
            iso_text = self.RGBIso_Table.item(i, 0).text()
            items = self.isosurface_LW.findItems(iso_text, QtCore.Qt.MatchExactly)
            if not items:
                continue
            iso_num = self.isosurface_LW.row(items[0])
            r = float(self.RGBIso_Table.item(i, 1).text()) / 255
            g = float(self.RGBIso_Table.item(i, 2).text()) / 255
            b = float(self.RGBIso_Table.item(i, 3).text()) / 255
            if iso_num < len(self.actorIso):
                self.actorIso[iso_num].GetMapper().ScalarVisibilityOff()
                self.actorIso[iso_num].GetProperty().SetColor(r, g, b)

        if not self.reset:
            isoRenderer.SetActiveCamera(self.camera)
        self.camera = isoRenderer.GetActiveCamera()
        self.reset = False

    def drawDomain(self, domainname: str) -> None:
        if not domainname or not os.path.isfile(domainname):
            return
        if not self.domain_CB.isChecked():
            return
        for i in range(27):
            self.domainRGB[i] = list(self.domainRGBHold[i])
            item = self.domain_TW.item(i + 4, 0)
            if item is not None:
                item.setForeground(
                    QtGui.QColor(
                        int(self.domainRGB[i][0] * 255),
                        int(self.domainRGB[i][1] * 255),
                        int(self.domainRGB[i][2] * 255),
                    )
                )

        for i in range(self.RGBDomain_Table.rowCount()):
            index = self.RGBDomain_Combo.findText(self.RGBDomain_Table.item(i, 0).text())
            if index < 0 or index >= len(self.domainRGB):
                continue
            self.domainRGB[index][0] = float(self.RGBDomain_Table.item(i, 1).text()) / 255
            self.domainRGB[index][1] = float(self.RGBDomain_Table.item(i, 2).text()) / 255
            self.domainRGB[index][2] = float(self.RGBDomain_Table.item(i, 3).text()) / 255
            item = self.domain_TW.item(index + 4, 0)
            if item is not None:
                item.setForeground(
                    QtGui.QColor(
                        int(self.domainRGB[index][0] * 255),
                        int(self.domainRGB[index][1] * 255),
                        int(self.domainRGB[index][2] * 255),
                    )
                )
        readerDomainOrigin = vtk.vtkStructuredPointsReader()
        readerDomainOrigin.SetFileName(domainname)
        readerDomainOrigin.Update()
        readerDomainOrigin.GetOutput().SetSpacing(
            float(self.rescaleX_LE.text() or 1),
            float(self.rescaleY_LE.text() or 1),
            float(self.rescaleZ_LE.text() or 1),
        )
        readerDomainOrigin.GetOutput().GetPointData().SetActiveScalars("domain")
        readerDomainOrigin.GetOutput().GetPointData().SetActiveScalars("domain")

        readerDomain = vtk.vtkExtractVOI()
        readerDomain.SetInputConnection(readerDomainOrigin.GetOutputPort())
        readerDomain.SetVOI(0, self.xmax + 2, 0, self.ymax + 2, 0, self.zmax + 2)
        readerDomain.Update()

        if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
            self.qvtkWidget.GetRenderWindow().AddRenderer(vtk.vtkRenderer())
        domainRenderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()

        for i in range(27):
            threshold = vtk.vtkThreshold()
            surface = vtk.vtkDataSetSurfaceFilter()
            smooth = vtk.vtkSmoothPolyDataFilter()
            normal = vtk.vtkPolyDataNormals()
            mapper = vtk.vtkDataSetMapper()
            threshold.SetInputConnection(readerDomain.GetOutputPort())
            threshold.AllScalarsOff()
            self._set_threshold_between(threshold, i - 0.5, i + 0.5)
            surface.SetInputConnection(threshold.GetOutputPort())
            smooth.SetInputConnection(surface.GetOutputPort())
            smooth.SetNumberOfIterations(30)
            smooth.SetRelaxationFactor(0.1)
            smooth.FeatureEdgeSmoothingOff()
            smooth.BoundarySmoothingOn()
            normal.SetInputConnection(smooth.GetOutputPort())
            normal.ComputePointNormalsOn()
            normal.ComputeCellNormalsOn()
            mapper.SetInputConnection(normal.GetOutputPort())
            mapper.ScalarVisibilityOff()
            self.actorDomain[i].SetMapper(mapper)
            r, g, b = self.domainRGB[i]
            self.actorDomain[i].GetProperty().SetColor(r, g, b)
            self.actorDomain[i].GetProperty().SetOpacity(1)
            if self.domain_TW.item(i + 4, 0).checkState() == QtCore.Qt.Checked:
                self.actorDomain[i].SetVisibility(True)
                domainRenderer.AddActor(self.actorDomain[i])

        for i in range(self.alphaDomain_Table.rowCount()):
            index = self.domainAlpha_Combo.findText(self.alphaDomain_Table.item(i, 0).text())
            value = float(self.alphaDomain_Table.item(i, 1).text())
            if index >= 4:
                self.actorDomain[index - 4].GetProperty().SetOpacity(value)
            elif index == 0:
                for j in range(27):
                    self.actorDomain[j].GetProperty().SetOpacity(value)
            elif index == 1:
                for j in range(1, 9):
                    self.actorDomain[j].GetProperty().SetOpacity(value)
            elif index == 2:
                for j in range(9, 21):
                    self.actorDomain[j].GetProperty().SetOpacity(value)
            elif index == 3:
                for j in range(21, 27):
                    self.actorDomain[j].GetProperty().SetOpacity(value)

        outlineDomain = vtk.vtkOutlineFilter()
        outlineDomain.SetInputConnection(readerDomainOrigin.GetOutputPort())
        outlineMapper = vtk.vtkDataSetMapper()
        outlineMapper.SetInputConnection(outlineDomain.GetOutputPort())
        self.outlineDomainActor.SetMapper(outlineMapper)
        self.outlineDomainActor.GetProperty().SetColor(0, 1, 0)
        self.outlineDomainActor.GetProperty().SetLineWidth(self.outlineWidth)
        domainRenderer.SetBackground(0.9, 0.9, 0.9)
        domainRenderer.AddActor(self.outlineDomainActor)
        self.outlineDomainActor.SetVisibility(self.outline_CB.checkState() != 0)
        self._update_coordinate_ruler(
            domainRenderer,
            (0, self.xmax + 2, 0, self.ymax + 2, 0, self.zmax + 2),
        )

        if self.reset:
            self.updateCamera(-1)
            self.reset = False
        else:
            self.updateCamera(0)

    def drawVO2Domain(self, domainname: str) -> None:
        if not domainname or not os.path.isfile(domainname):
            return
        if not self.domain_CB.isChecked():
            return
        readerDomainOrigin = vtk.vtkStructuredPointsReader()
        readerDomainOrigin.SetFileName(domainname)
        readerDomainOrigin.Update()
        readerDomainOrigin.GetOutput().SetSpacing(
            float(self.rescaleX_LE.text() or 1),
            float(self.rescaleY_LE.text() or 1),
            float(self.rescaleZ_LE.text() or 1),
        )
        readerDomain = vtk.vtkExtractVOI()
        readerDomain.SetInputConnection(readerDomainOrigin.GetOutputPort())
        readerDomain.SetVOI(0, self.xmax + 2, 0, self.ymax + 2, 0, self.zmax + 2)
        readerDomain.Update()

        if self.qvtkWidget.GetRenderWindow().GetRenderers().GetNumberOfItems() == 0:
            self.qvtkWidget.GetRenderWindow().AddRenderer(vtk.vtkRenderer())
        domainRenderer = self.qvtkWidget.GetRenderWindow().GetRenderers().GetFirstRenderer()

        for i in range(9):
            self.vo2DomainRGB[i] = list(self.vo2DomainRGBHold[i])
            item = self.vo2Domain_LW.item(i)
            if item:
                item.setForeground(
                    QtGui.QColor(
                        int(self.vo2DomainRGB[i][0] * 255),
                        int(self.vo2DomainRGB[i][1] * 255),
                        int(self.vo2DomainRGB[i][2] * 255),
                    )
                )

        for i in range(self.RGBDomain_Table.rowCount()):
            index = self.vo2RGB_Combo.findText(self.RGBDomain_Table.item(i, 0).text())
            if 0 <= index < len(self.vo2DomainRGB):
                self.vo2DomainRGB[index][0] = float(self.RGBDomain_Table.item(i, 1).text()) / 255
                self.vo2DomainRGB[index][1] = float(self.RGBDomain_Table.item(i, 2).text()) / 255
                self.vo2DomainRGB[index][2] = float(self.RGBDomain_Table.item(i, 3).text()) / 255
                item = self.vo2Domain_LW.item(index)
                if item:
                    item.setForeground(
                        QtGui.QColor(
                            int(self.vo2DomainRGB[index][0] * 255),
                            int(self.vo2DomainRGB[index][1] * 255),
                            int(self.vo2DomainRGB[index][2] * 255),
                        )
                    )

        for i in range(9):
            threshold = vtk.vtkThreshold()
            surface = vtk.vtkDataSetSurfaceFilter()
            smooth = vtk.vtkSmoothPolyDataFilter()
            normal = vtk.vtkPolyDataNormals()
            mapper = vtk.vtkDataSetMapper()
            threshold.SetInputConnection(readerDomain.GetOutputPort())
            threshold.AllScalarsOff()
            self._set_threshold_between(threshold, i - 0.5, i + 0.5)
            surface.SetInputConnection(threshold.GetOutputPort())
            smooth.SetInputConnection(surface.GetOutputPort())
            smooth.SetNumberOfIterations(30)
            smooth.SetRelaxationFactor(0.1)
            smooth.FeatureEdgeSmoothingOff()
            smooth.BoundarySmoothingOn()
            normal.SetInputConnection(smooth.GetOutputPort())
            normal.ComputePointNormalsOn()
            normal.ComputeCellNormalsOn()
            mapper.SetInputConnection(normal.GetOutputPort())
            mapper.ScalarVisibilityOff()
            self.actorDomain[i].SetMapper(mapper)
            r, g, b = self.vo2DomainRGB[i]
            self.actorDomain[i].GetProperty().SetColor(r, g, b)
            self.actorDomain[i].GetProperty().SetOpacity(1)
            if self.vo2Domain_LW.item(i).checkState() == QtCore.Qt.Checked:
                self.actorDomain[i].SetVisibility(True)
                domainRenderer.AddActor(self.actorDomain[i])

        for i in range(self.alphaDomain_Table.rowCount()):
            index = self.vo2Opacity_Combo.findText(self.alphaDomain_Table.item(i, 0).text())
            value = float(self.alphaDomain_Table.item(i, 1).text())
            if 0 <= index < len(self.actorDomain):
                self.actorDomain[index].GetProperty().SetOpacity(value)

        outlineDomain = vtk.vtkOutlineFilter()
        outlineDomain.SetInputConnection(readerDomainOrigin.GetOutputPort())
        outlineMapper = vtk.vtkDataSetMapper()
        outlineMapper.SetInputConnection(outlineDomain.GetOutputPort())
        self.outlineDomainActor.SetMapper(outlineMapper)
        self.outlineDomainActor.GetProperty().SetColor(0, 1, 0)
        self.outlineDomainActor.GetProperty().SetLineWidth(self.outlineWidth)
        domainRenderer.SetBackground(0.9, 0.9, 0.9)
        domainRenderer.AddActor(self.outlineDomainActor)
        self.outlineDomainActor.SetVisibility(self.outline_CB.checkState() != 0)
        self._update_coordinate_ruler(
            domainRenderer,
            (0, self.xmax + 2, 0, self.ymax + 2, 0, self.zmax + 2),
        )

        if self.reset:
            self.updateCamera(-1)
            self.reset = False
        else:
            self.updateCamera(0)

    def domainType(self, px: float, py: float, pz: float) -> int:
        length = math.sqrt(px * px + py * py + pz * pz)
        if length <= self.domainStandardValue:
            return -1
        best_angle = PI_VALUE
        best_index = -1
        for i in range(1, 27):
            dot = px * self.domainOrth[i][0] + py * self.domainOrth[i][1] + pz * self.domainOrth[i][2]
            cos_value = dot / length
            if cos_value > 1:
                angle = 0
            elif cos_value < -1:
                angle = PI_VALUE
            else:
                angle = math.acos(cos_value)
            if angle < self.domainStandardAngleRad and angle < best_angle:
                best_angle = angle
                best_index = i
        return best_index

    def vo2DomainType(self, u1, u2, u3, u4, n1, n2, n3, n4) -> int:
        u_mod = math.sqrt(u1 * u1 + u2 * u2 + u3 * u3 + u4 * u4)
        n_mod = math.sqrt(n1 * n1 + n2 * n2 + n3 * n3 + n4 * n4)
        if u_mod < self.M1mod and n_mod < self.M1mod:
            return 0
        if u_mod > self.M1mod and abs(u1 / math.sqrt(2) + u3 / math.sqrt(2)) / u_mod > math.cos(self.M1ang) and n_mod > self.M1mod and abs(n1 / math.sqrt(2) + n3 / math.sqrt(2)) / n_mod > math.cos(self.M1ang):
            return 1
        if u_mod > self.M1mod and abs(u2 / math.sqrt(2) + u4 / math.sqrt(2)) / u_mod > math.cos(self.M1ang) and n_mod > self.M1mod and abs(n2 / math.sqrt(2) + n4 / math.sqrt(2)) / n_mod > math.cos(self.M1ang):
            return 2
        if u_mod > self.M1mod and abs(u1 / math.sqrt(2) - u3 / math.sqrt(2)) / u_mod > math.cos(self.M1ang) and n_mod > self.M1mod and abs(n1 / math.sqrt(2) - n3 / math.sqrt(2)) / n_mod > math.cos(self.M1ang):
            return 3
        if u_mod > self.M1mod and abs(u2 / math.sqrt(2) - u4 / math.sqrt(2)) / u_mod > math.cos(self.M1ang) and n_mod > self.M1mod and abs(n2 / math.sqrt(2) - n4 / math.sqrt(2)) / n_mod > math.cos(self.M1ang):
            return 4
        if u_mod > self.M2mod and abs(u1) / u_mod > math.cos(self.M2ang) and n_mod > self.M2mod and abs(n1) / n_mod > math.cos(self.M2ang):
            return 5
        if u_mod > self.M2mod and abs(u2) / u_mod > math.cos(self.M2ang) and n_mod > self.M2mod and abs(n2) / n_mod > math.cos(self.M2ang):
            return 6
        if u_mod > self.M2mod and abs(u3) / u_mod > math.cos(self.M2ang) and n_mod > self.M2mod and abs(n3) / n_mod > math.cos(self.M2ang):
            return 7
        if u_mod > self.M2mod and abs(u4) / u_mod > math.cos(self.M2ang) and n_mod > self.M2mod and abs(n4) / n_mod > math.cos(self.M2ang):
            return 8
        return -1

    def outputDomain(self, filedir: str, x: int, y: int, z: int) -> None:
        row_number = (x + 3) * (y + 3) * (z + 3)
        output_data = [-1] * row_number
        mR = mO = mT = mN = 0
        point_number = [0] * 27

        index = 0
        if self.columns == 6:
            index = 3

        nfs = 0
        nsub = 0
        for i in range(z + 1):
            for j in range(y + 1):
                for k in range(x + 1):
                    row = k * (z + 1) * (y + 1) + j * (z + 1) + i
                    px, py, pz = self.vtk_data[row][index : index + 3]
                    if abs(px) + abs(py) + abs(pz) > 1.0e-6:
                        nfs = i
                        break
        for i in range(z, 0, -1):
            for j in range(y + 1):
                for k in range(x + 1):
                    row = k * (z + 1) * (y + 1) + j * (z + 1) + i
                    px, py, pz = self.vtk_data[row][index : index + 3]
                    if abs(px) + abs(py) + abs(pz) > 1.0e-6:
                        nsub = i - 1
                        break

        for i in range(1, x + 2):
            for j in range(1, y + 2):
                for k in range(1, nsub + 1):
                    hold = k * (x + 3) * (y + 3) + j * (x + 3) + i
                    output_data[hold] = 0

        for i in range(1, x + 2):
            for j in range(1, y + 2):
                for k in range(nsub + 1, nfs + 2):
                    row = (i - 1) * (z + 1) * (y + 1) + (j - 1) * (z + 1) + (k - 1)
                    px, py, pz = self.vtk_data[row][index : index + 3]
                    hold = k * (x + 3) * (y + 3) + j * (x + 3) + i
                    output_data[hold] = self.domainType(px, py, pz)
                    if 1 <= output_data[hold] < 9:
                        mR += 1
                    if 9 <= output_data[hold] < 21:
                        mO += 1
                    if 21 <= output_data[hold] < 27:
                        mT += 1
                    if output_data[hold] == -1:
                        mN += 1
                    else:
                        point_number[output_data[hold]] += 1

        mfilm = mR + mO + mT
        if mfilm > 0:
            for i in range(1, 27):
                self.pointFraction[i] = point_number[i] / float(mfilm)
        else:
            for i in range(1, 27):
                self.pointFraction[i] = 0.0

        out_path = f"{filedir}.domain.vtk"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# vtk DataFile Version 3.0\n")
            f.write("Structured Points\n")
            f.write("ASCII\n\n")
            f.write("DATASET STRUCTURED_POINTS\n")
            f.write(f"DIMENSIONS {x+3} {y+3} {z+3}\n")
            f.write("ORIGIN -1 -1 -1\n")
            f.write(
                f"SPACING {self.rescaleX_LE.text()} {self.rescaleY_LE.text()} {self.rescaleZ_LE.text()}\n\n"
            )
            f.write(f"POINT_DATA {row_number}\n")
            f.write("SCALARS domain int\n")
            f.write("LOOKUP_TABLE default\n")
            for value in output_data:
                f.write(f"{value}\n")

        for i in range(row_number):
            if output_data[i] != -1:
                self.existDomain[output_data[i]] = True

        total_fraction = sum(self.pointFraction[1:27])
        r_fraction = sum(self.pointFraction[1:9])
        o_fraction = sum(self.pointFraction[9:21])
        t_fraction = sum(self.pointFraction[21:27])
        summary_values = [total_fraction, r_fraction, o_fraction, t_fraction]
        for idx, value in enumerate(summary_values):
            item = self.domain_TW.item(idx, 1)
            if item is None:
                item = QtWidgets.QTableWidgetItem()
                self.domain_TW.setItem(idx, 1, item)
            item.setText(f"{value * 100:.2f}%")

        for i in range(1, 27):
            item = self.domain_TW.item(i + 4, 1)
            if item is None:
                item = QtWidgets.QTableWidgetItem()
                self.domain_TW.setItem(i + 4, 1, item)
            item.setText(f"{self.pointFraction[i] * 100:.2f}%")
            state_item = self.domain_TW.item(i + 4, 0)
            if state_item is not None:
                state_item.setCheckState(
                    QtCore.Qt.Checked if self.existDomain[i] else QtCore.Qt.Unchecked
                )

    def outputVO2Domain(self, filedir: str, x: int, y: int, z: int) -> None:
        row_number = (x + 3) * (y + 3) * (z + 3)
        output_data = [-1] * row_number
        point_number = [0] * 9
        mfilm = 0

        for i in range(1, x + 2):
            for j in range(1, y + 2):
                for k in range(1, z + 2):
                    row = (i - 1) * (z + 1) * (y + 1) + (j - 1) * (z + 1) + (k - 1)
                    values = self.vtk_data[row]
                    u1, u2, u3, u4 = values[0:4]
                    n1, n2, n3, n4 = values[4:8]
                    hold = k * (x + 3) * (y + 3) + j * (x + 3) + i
                    output_data[hold] = self.vo2DomainType(u1, u2, u3, u4, n1, n2, n3, n4)
                    if output_data[hold] != -1:
                        point_number[output_data[hold]] += 1
                        if 1 <= output_data[hold] <= 8:
                            mfilm += 1

        for i in range(1, 9):
            self.pointFraction[i] = point_number[i] / float(mfilm) if mfilm else 0.0

        out_path = f"{filedir}.domain.vtk"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# vtk DataFile Version 3.0\n")
            f.write("Structured Points\n")
            f.write("ASCII\n\n")
            f.write("DATASET STRUCTURED_POINTS\n")
            f.write(f"DIMENSIONS {x+3} {y+3} {z+3}\n")
            f.write("ORIGIN -1 -1 -1\n")
            f.write(
                f"SPACING {self.rescaleX_LE.text()} {self.rescaleY_LE.text()} {self.rescaleZ_LE.text()}\n\n"
            )
            f.write(f"POINT_DATA {row_number}\n")
            f.write("SCALARS domain int\n")
            f.write("LOOKUP_TABLE default\n")
            for value in output_data:
                f.write(f"{value}\n")

        for i in range(row_number):
            if output_data[i] != -1:
                self.existDomain[output_data[i]] = True

        for i in range(9):
            item = self.vo2Domain_LW.item(i)
            if item:
                item.setText(f"{self.vo2DomainList[i]}\t{self.pointFraction[i]*100:.2f}%")
                item.setCheckState(QtCore.Qt.Checked if self.existDomain[i] else QtCore.Qt.Unchecked)

    def saveImage(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "", "Images (*.png)")
        if not file_path:
            return
        if self.stackedWidget.currentIndex() == 0:
            self.outputImage(file_path)
        else:
            target_w = self._safe_positive_int(self.viewportSizeX.text(), 2000)
            target_h = self._safe_positive_int(self.viewportSizeY.text(), 2000)
            magnify = self._safe_positive_int(self.exportRatio.text(), 1)
            self.customPlot.savePng(file_path, target_w * magnify, target_h * magnify, 600)

    def saveScene(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "", "Images (*.x3d)")
        if not file_path:
            return
        if self.stackedWidget.currentIndex() == 0:
            exporter = vtk.vtkX3DExporter()
            exporter.SetInput(self.qvtkWidget.GetRenderWindow())
            exporter.SetFileName(file_path)
            exporter.Update()
            exporter.Write()

    def _safe_positive_int(self, text: str, default: int) -> int:
        try:
            value = int(float(text))
        except ValueError:
            return default
        return value if value > 0 else default

    def _fit_export_size_to_view_aspect(
        self, view_w: int, view_h: int, req_w: int, req_h: int
    ) -> tuple[int, int]:
        view_w = max(1, int(view_w))
        view_h = max(1, int(view_h))
        req_w = max(1, int(req_w))
        req_h = max(1, int(req_h))
        view_ratio = view_w / float(view_h)
        req_ratio = req_w / float(req_h)
        if abs(req_ratio - view_ratio) <= max(1e-6, view_ratio * 0.01):
            return req_w, req_h
        if req_w >= req_h:
            fitted_w = req_w
            fitted_h = max(1, int(round(fitted_w / view_ratio)))
        else:
            fitted_h = req_h
            fitted_w = max(1, int(round(fitted_h * view_ratio)))
        return fitted_w, fitted_h

    def outputImage(self, load: str) -> None:
        render_window = self.qvtkWidget.GetRenderWindow()
        render_window.Render()
        self.qvtkWidget.update()
        QtWidgets.QApplication.processEvents()

        target_w = self._safe_positive_int(self.viewportSizeX.text(), 2000)
        target_h = self._safe_positive_int(self.viewportSizeY.text(), 2000)
        magnify = self._safe_positive_int(self.exportRatio.text(), 1)
        current_w, current_h = render_window.GetSize()
        fit_w, fit_h = self._fit_export_size_to_view_aspect(
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
            self._apply_png_dpi(load, 600)
        finally:
            render_window.SetSize(original_w, original_h)
            render_window.Render()
            self.qvtkWidget.update()


    def _apply_png_dpi(self, path: str, dpi: int = 600) -> None:
        image = QtGui.QImage(path)
        if image.isNull():
            return
        dots_per_meter = int(round(dpi / 0.0254))
        image.setDotsPerMeterX(dots_per_meter)
        image.setDotsPerMeterY(dots_per_meter)
        image.save(path, "PNG")

    def on_cameraSet_PB_released(self) -> None:
        try:
            positionX = float(self.cameraPositionX_LE.text())
            positionY = float(self.cameraPositionY_LE.text())
            positionZ = float(self.cameraPositionZ_LE.text())
            focalX = float(self.cameraFocalX_LE.text())
            focalY = float(self.cameraFocalY_LE.text())
            focalZ = float(self.cameraFocalZ_LE.text())
            viewX = float(self.cameraViewUpX_LE.text())
            viewY = float(self.cameraViewUpY_LE.text())
            viewZ = float(self.cameraViewUpZ_LE.text())
        except ValueError:
            return
        self.camera.SetPosition(positionX, positionY, positionZ)
        self.camera.SetFocalPoint(focalX, focalY, focalZ)
        self.camera.SetViewUp(viewX, viewY, viewZ)
        self.updateCamera(0)

    def on_cameraGet_PB_released(self) -> None:
        pos = self.camera.GetPosition()
        focal = self.camera.GetFocalPoint()
        view = self.camera.GetViewUp()
        self.cameraPositionX_LE.setText(str(pos[0]))
        self.cameraPositionY_LE.setText(str(pos[1]))
        self.cameraPositionZ_LE.setText(str(pos[2]))
        self.cameraFocalX_LE.setText(str(focal[0]))
        self.cameraFocalY_LE.setText(str(focal[1]))
        self.cameraFocalZ_LE.setText(str(focal[2]))
        self.cameraViewUpX_LE.setText(str(view[0]))
        self.cameraViewUpY_LE.setText(str(view[1]))
        self.cameraViewUpZ_LE.setText(str(view[2]))

    def outputStatus(self, file_info: QtCore.QFileInfo) -> None:
        with open(file_info.absoluteFilePath(), "w", encoding="utf-8") as f:
            f.write(f"{int(self.outline_CB.checkState())} {self.outlineWidth_LE.text()}\n")
            f.write(f"{int(self.axis_CB.checkState())}\n")
            f.write(f"{int(self.extract_CB.checkState())}\n")
            f.write(f"{self.xmin_LE.text()} {self.xmax_LE.text()} {self.xDelta_LE.text()}\n")
            f.write(f"{self.ymin_LE.text()} {self.ymax_LE.text()} {self.yDelta_LE.text()}\n")
            f.write(f"{self.zmin_LE.text()} {self.zmax_LE.text()} {self.zDelta_LE.text()}\n")
            f.write(f"{self.rescaleX_LE.text()} {self.rescaleY_LE.text()} {self.rescaleZ_LE.text()}\n")
            f.write(
                f"{self.cameraPositionX_LE.text()} {self.cameraPositionY_LE.text()} {self.cameraPositionZ_LE.text()}\n"
            )
            f.write(
                f"{self.cameraFocalX_LE.text()} {self.cameraFocalY_LE.text()} {self.cameraFocalZ_LE.text()}\n"
            )
            f.write(
                f"{self.cameraViewUpX_LE.text()} {self.cameraViewUpY_LE.text()} {self.cameraViewUpZ_LE.text()}\n"
            )
            f.write(f"{self.viewportSizeX.text()} {self.viewportSizeY.text()} {self.exportRatio.text()}\n")

            f.write(f"{self.RGB_Combo.currentIndex()}\n")
            f.write(f"{self.RGBScalar_Table.rowCount()}\n")
            for i in range(self.RGBScalar_Table.rowCount()):
                f.write(
                    f"{self.RGBScalar_Table.item(i,0).text()} {self.RGBScalar_Table.item(i,1).text()} "
                    f"{self.RGBScalar_Table.item(i,2).text()} {self.RGBScalar_Table.item(i,3).text()}\n"
                )
            f.write(f"{self.RGBVector_Table.rowCount()}\n")
            for i in range(self.RGBVector_Table.rowCount()):
                f.write(
                    f"{self.RGBVector_Table.item(i,0).text()} {self.RGBVector_Table.item(i,1).text()} "
                    f"{self.RGBVector_Table.item(i,2).text()} {self.RGBVector_Table.item(i,3).text()}\n"
                )
            f.write(f"{self.RGBIso_Table.rowCount()}\n")
            for i in range(self.RGBIso_Table.rowCount()):
                f.write(
                    f"{self.RGBIso_Table.item(i,0).text()} {self.RGBIso_Table.item(i,1).text()} "
                    f"{self.RGBIso_Table.item(i,2).text()} {self.RGBIso_Table.item(i,3).text()}\n"
                )
            f.write(f"{self.RGBDomain_Table.rowCount()}\n")
            for i in range(self.RGBDomain_Table.rowCount()):
                index = self.RGBDomain_Combo.findText(self.RGBDomain_Table.item(i, 0).text())
                f.write(
                    f"{index} {self.RGBDomain_Table.item(i,1).text()} "
                    f"{self.RGBDomain_Table.item(i,2).text()} {self.RGBDomain_Table.item(i,3).text()}\n"
                )

            f.write(f"{self.alpha_Combo.currentIndex()}\n")
            f.write(f"{self.alphaScalar_Table.rowCount()}\n")
            for i in range(self.alphaScalar_Table.rowCount()):
                f.write(
                    f"{self.alphaScalar_Table.item(i,0).text()} {self.alphaScalar_Table.item(i,1).text()}\n"
                )
            f.write(f"{self.alphaDomain_Table.rowCount()}\n")
            for i in range(self.alphaDomain_Table.rowCount()):
                index = self.domainAlpha_Combo.findText(self.alphaDomain_Table.item(i, 0).text())
                f.write(f"{index} {self.alphaDomain_Table.item(i,1).text()}\n")

            f.write(f"{int(self.scalar_CB.checkState())}\n")
            f.write(f"{self.scalarChoice.count()} {self.scalarChoice.currentIndex()}\n")
            f.write(f"{int(self.scalarLegendBar_CB.checkState())} {self.scalarLegend_LE.text()}\n")
            f.write(f"{int(self.volume_CB.checkState())}\n")
            f.write(f"{int(self.scalarRange_CB.checkState())}\n")
            f.write(f"{self.scalarValueMin_LE.text()} {self.scalarValueMax_LE.text()}\n")
            f.write(f"{int(self.slice_CB.checkState())}\n")
            f.write(f"{self.sliceOriginX.text()} {self.sliceOriginY.text()} {self.sliceOriginZ.text()}\n")
            f.write(f"{self.sliceNormalX.text()} {self.sliceNormalY.text()} {self.sliceNormalZ.text()}\n")
            f.write(f"{int(self.isosurface_CB.checkState())}\n")
            f.write(f"{self.isosurface_LW.count()}\n")
            for i in range(self.isosurface_LW.count()):
                item = self.isosurface_LW.item(i)
                f.write(f"{item.text()} {int(item.checkState())}\n")

            f.write(f"{int(self.vector_CB.checkState())}\n")
            f.write(f"{self.vectorChoice.count()} {self.vectorChoice.currentIndex()}\n")
            f.write(f"{self.vectorColorMode_Combo.currentIndex()}\n")
            f.write(f"{int(self.vectorLegendBar_CB.checkState())} {self.vectorLegend_LE.text()}\n")
            f.write(f"{int(self.vectorGlyph_CB.checkState())}\n")
            f.write(f"{self.vectorMaskNum_LE.text()}\n")
            f.write(f"{self.vectorScale_LE.text()}\n")
            f.write(f"{int(self.vectorRange_CB.checkState())}\n")
            f.write(f"{self.vectorValueMin_LE.text()} {self.vectorValueMax_LE.text()}\n")
            f.write(f"{int(self.streamline_CB.checkState())}\n")
            f.write(f"{self.seedNumber_LE.text()}\n")
            f.write(f"{self.seedRadius_LE.text()}\n")
            f.write(f"{self.seedCenterX_LE.text()} {self.seedCenterY_LE.text()} {self.seedCenterZ_LE.text()}\n")
            f.write(f"{self.streamStepLength_LE.text()}\n")

            f.write(f"{int(self.domain_CB.checkState())}\n")
            for i in range(self.domain_TW.rowCount()):
                f.write(f"{int(self.domain_TW.item(i,0).checkState())}\n")
            f.write(f"{self.domainStdAngle_LE.text()} {self.domainStdValue_LE.text()}\n")
            f.write(f"{self.domain_Combo.currentIndex()}\n")
            for i in range(self.vo2Domain_LW.count()):
                f.write(f"{int(self.vo2Domain_LW.item(i).checkState())}\n")
            f.write(f"{self.vo2_M1_mod_LE.text()} {self.vo2_M1_ang_LE.text()}\n")
            f.write(f"{self.vo2_M2_mod_LE.text()} {self.vo2_M2_ang_LE.text()}\n")
            if self.coordRuler_CB is not None:
                f.write(f"{int(self.coordRuler_CB.checkState())}\n")
            if self.pointProbe_CB is not None:
                f.write(f"{int(self.pointProbe_CB.checkState())}\n")

    def slotOutputStatus(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "", "Status (*.txt)")
        if file_path:
            self.outputStatus(QtCore.QFileInfo(file_path))

    def loadStatus(self, file_info: QtCore.QFileInfo) -> None:
        with open(file_info.absoluteFilePath(), "r", encoding="utf-8") as f:
            data = f.read().split()
        if not data:
            return
        it = iter(data)

        self.outline_CB.setCheckState(int(next(it)))
        self.outlineWidth_LE.setText(next(it))
        self.axis_CB.setCheckState(int(next(it)))
        self.extract_CB.setCheckState(int(next(it)))
        self.xmin_LE.setText(next(it))
        self.xmax_LE.setText(next(it))
        self.xDelta_LE.setText(next(it))
        self.ymin_LE.setText(next(it))
        self.ymax_LE.setText(next(it))
        self.yDelta_LE.setText(next(it))
        self.zmin_LE.setText(next(it))
        self.zmax_LE.setText(next(it))
        self.zDelta_LE.setText(next(it))
        self.rescaleX_LE.setText(next(it))
        self.rescaleY_LE.setText(next(it))
        self.rescaleZ_LE.setText(next(it))
        self.cameraPositionX_LE.setText(next(it))
        self.cameraPositionY_LE.setText(next(it))
        self.cameraPositionZ_LE.setText(next(it))
        self.cameraFocalX_LE.setText(next(it))
        self.cameraFocalY_LE.setText(next(it))
        self.cameraFocalZ_LE.setText(next(it))
        self.cameraViewUpX_LE.setText(next(it))
        self.cameraViewUpY_LE.setText(next(it))
        self.cameraViewUpZ_LE.setText(next(it))
        self.viewportSizeX.setText(next(it))
        self.viewportSizeY.setText(next(it))
        self.exportRatio.setText(next(it))

        self.RGB_Combo.setCurrentIndex(int(next(it)))
        count = int(next(it))
        self.RGBScalar_Table.setRowCount(0)
        for i in range(count):
            value = next(it)
            r = next(it)
            g = next(it)
            b = next(it)
            self.RGBScalar_Table.insertRow(i)
            self.RGBScalar_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
            self.RGBScalar_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
            self.RGBScalar_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
            self.RGBScalar_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

        count = int(next(it))
        self.RGBVector_Table.setRowCount(0)
        for i in range(count):
            value = next(it)
            r = next(it)
            g = next(it)
            b = next(it)
            self.RGBVector_Table.insertRow(i)
            self.RGBVector_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
            self.RGBVector_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
            self.RGBVector_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
            self.RGBVector_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

        count = int(next(it))
        self.RGBIso_Table.setRowCount(0)
        for i in range(count):
            value = next(it)
            r = next(it)
            g = next(it)
            b = next(it)
            self.RGBIso_Table.insertRow(i)
            self.RGBIso_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
            self.RGBIso_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
            self.RGBIso_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
            self.RGBIso_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

        count = int(next(it))
        self.RGBDomain_Table.setRowCount(0)
        for i in range(count):
            value = next(it)
            r = next(it)
            g = next(it)
            b = next(it)
            self.RGBDomain_Table.insertRow(i)
            self.RGBDomain_Table.setItem(
                i, 0, QtWidgets.QTableWidgetItem(self.RGBDomain_Combo.itemText(int(value)))
            )
            self.RGBDomain_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(r))
            self.RGBDomain_Table.setItem(i, 2, QtWidgets.QTableWidgetItem(g))
            self.RGBDomain_Table.setItem(i, 3, QtWidgets.QTableWidgetItem(b))

        self.alpha_Combo.setCurrentIndex(int(next(it)))
        count = int(next(it))
        self.alphaScalar_Table.setRowCount(0)
        for i in range(count):
            value = next(it)
            a = next(it)
            self.alphaScalar_Table.insertRow(i)
            self.alphaScalar_Table.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
            self.alphaScalar_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(a))

        count = int(next(it))
        self.alphaDomain_Table.setRowCount(0)
        for i in range(count):
            value = next(it)
            a = next(it)
            self.alphaDomain_Table.insertRow(i)
            self.alphaDomain_Table.setItem(
                i, 0, QtWidgets.QTableWidgetItem(self.domainAlpha_Combo.itemText(int(value)))
            )
            self.alphaDomain_Table.setItem(i, 1, QtWidgets.QTableWidgetItem(a))

        self.scalar_CB.setCheckState(int(next(it)))
        _count = int(next(it))
        index = int(next(it))
        self.scalarChoice.setCurrentIndex(index)
        self.scalarColumn = index
        self.scalarLegendBar_CB.setCheckState(int(next(it)))
        self.scalarLegend_LE.setText(next(it))
        self.volume_CB.setCheckState(int(next(it)))
        self.scalarRange_CB.setCheckState(int(next(it)))
        self.scalarValueMin_LE.setText(next(it))
        self.scalarValueMax_LE.setText(next(it))
        self.slice_CB.setCheckState(int(next(it)))
        self.sliceOriginX.setText(next(it))
        self.sliceOriginY.setText(next(it))
        self.sliceOriginZ.setText(next(it))
        self.sliceNormalX.setText(next(it))
        self.sliceNormalY.setText(next(it))
        self.sliceNormalZ.setText(next(it))
        self.isosurface_CB.setCheckState(int(next(it)))
        iso_count = int(next(it))
        while self.isosurface_LW.count() > 0:
            self.isosurface_LW.setCurrentRow(0)
            self.on_isoDelete_PB_released()
        for _ in range(iso_count):
            value = next(it)
            checkstate = int(next(it))
            self.isoValue_LE.setText(value)
            self.on_isoAdd_PB_released()
            item = self.isosurface_LW.item(self.isosurface_LW.count() - 1)
            item.setCheckState(checkstate)

        self.vector_CB.setCheckState(int(next(it)))
        _count = int(next(it))
        index = int(next(it))
        self.vectorChoice.setCurrentIndex(index)
        self.vectorColumn = index
        self.vectorColorMode_Combo.setCurrentIndex(int(next(it)))
        self.vectorLegendBar_CB.setCheckState(int(next(it)))
        self.vectorLegend_LE.setText(next(it))
        self.vectorGlyph_CB.setCheckState(int(next(it)))
        self.vectorMaskNum_LE.setText(next(it))
        self.vectorScale_LE.setText(next(it))
        self.vectorRange_CB.setCheckState(int(next(it)))
        self.vectorValueMin_LE.setText(next(it))
        self.vectorValueMax_LE.setText(next(it))
        self.streamline_CB.setCheckState(int(next(it)))
        self.seedNumber_LE.setText(next(it))
        self.seedRadius_LE.setText(next(it))
        self.seedCenterX_LE.setText(next(it))
        self.seedCenterY_LE.setText(next(it))
        self.seedCenterZ_LE.setText(next(it))
        self.streamStepLength_LE.setText(next(it))

        self.domain_CB.setCheckState(int(next(it)))
        for i in range(self.domain_TW.rowCount()):
            self.domain_TW.item(i, 0).setCheckState(int(next(it)))
        self.domainStdAngle_LE.setText(next(it))
        self.domainStdValue_LE.setText(next(it))
        self.domain_Combo.setCurrentIndex(int(next(it)))
        for i in range(self.vo2Domain_LW.count()):
            self.vo2Domain_LW.item(i).setCheckState(int(next(it)))
        self.vo2_M1_mod_LE.setText(next(it))
        self.vo2_M1_ang_LE.setText(next(it))
        self.vo2_M2_mod_LE.setText(next(it))
        self.vo2_M2_ang_LE.setText(next(it))
        try:
            coord_ruler_state = int(next(it))
        except StopIteration:
            coord_ruler_state = 0
        if self.coordRuler_CB is not None:
            self.coordRuler_CB.setCheckState(coord_ruler_state)
        try:
            point_probe_state = int(next(it))
        except StopIteration:
            point_probe_state = 0
        if self.pointProbe_CB is not None:
            self.pointProbe_CB.setCheckState(point_probe_state)

    def slotLoadStatus(self) -> str:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Status input", "", "Status input (*.*)")
        if file_path:
            self.loadStatus(QtCore.QFileInfo(file_path))
        return file_path

    def slotBatch3D(self) -> None:
        dialog = Batch3D(self)
        dialog.show()

    def getMin(self, values: List[float]) -> float:
        return min(values) if values else 0.0

    def getMax(self, values: List[float]) -> float:
        return max(values) if values else 0.0

    def getAvg(self, values: List[float]) -> float:
        return sum(values) / float(len(values)) if values else 0.0

    def domainProcessing(self, filedir: str) -> int:
        column_number = self.loadData(filedir)
        self.outputDomain(filedir, self.xmax, self.ymax, self.zmax)

        for i in range(5):
            item = self.domain_TW.item(i, 0)
            if item is not None:
                item.setCheckState(QtCore.Qt.Checked)

        for i in range(27):
            item = self.domain_TW.item(i + 4, 0)
            if item is None:
                continue
            if self.existDomain[i]:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

        return column_number
