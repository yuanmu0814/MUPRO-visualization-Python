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
from batch3d import Batch3D
from color_utils import get_rgb
from data_io_ops import (
    load_data as data_load_data,
    output_scalar as data_output_scalar,
    output_vector as data_output_vector,
    update_extraction as data_update_extraction,
)
from domain_calculation import domain_type, vo2_domain_type
from constants import (
    DOMAIN_ORTH,
    DEFAULT_DOMAIN_COLORS,
    DEFAULT_DOMAIN_LIST,
    DEFAULT_VO2_COLORS,
    DEFAULT_VO2_DOMAIN_LIST,
    PI_VALUE,
)
from domain_workflow import domain_processing
from point_probe_ops import (
    clear_point_probe_vector_dataset as pp_clear_point_probe_vector_dataset,
    current_point_probe_mode as pp_current_point_probe_mode,
    format_vector_probe_text as pp_format_vector_probe_text,
    pick_world_position as pp_pick_world_position,
    refresh_point_probe_source as pp_refresh_point_probe_source,
    reset_point_probe_display as pp_reset_point_probe_display,
    sample_grid_index_and_point_id as pp_sample_grid_index_and_point_id,
    sample_scalar_value_at_world as pp_sample_scalar_value_at_world,
    sample_vector_value_at_world as pp_sample_vector_value_at_world,
    set_point_probe_hint as pp_set_point_probe_hint,
    set_point_probe_label as pp_set_point_probe_label,
    update_point_probe_vector_dataset as pp_update_point_probe_vector_dataset,
)
from vtk_interaction_ops import (
    clear_middle_pan_state as vtk_clear_middle_pan_state,
    is_middle_button_down as vtk_is_middle_button_down,
    normalized_vector as vtk_normalized_vector,
    on_vtk_left_button_press as vtk_on_vtk_left_button_press,
    on_vtk_middle_button_press as vtk_on_vtk_middle_button_press,
    on_vtk_middle_button_release as vtk_on_vtk_middle_button_release,
    on_vtk_mouse_move_lock_pan as vtk_on_vtk_mouse_move_lock_pan,
)
from coordinate_ruler_ops import update_coordinate_ruler as coord_update_coordinate_ruler
from vtk_pipeline_ops import update_vtk as pipeline_update_vtk
from export_ops import (
    apply_png_dpi as export_apply_png_dpi,
    on_camera_get_pb_released as export_on_camera_get_pb_released,
    on_camera_set_pb_released as export_on_camera_set_pb_released,
    output_image as export_output_image,
    save_image as export_save_image,
    save_scene as export_save_scene,
)
from file_open_ops import (
    on_scalar_choice_current_index_changed as open_on_scalar_choice_current_index_changed,
    on_vector_choice_current_index_changed as open_on_vector_choice_current_index_changed,
    slot_open_file_domain as open_slot_open_file_domain,
    slot_open_file_scalar as open_slot_open_file_scalar,
    slot_open_file_vector as open_slot_open_file_vector,
)
from status_ops import (
    load_status as state_load_status,
    output_status as state_output_status,
    slot_load_status as state_slot_load_status,
    slot_output_status as state_slot_output_status,
)
from ui_state_ops import (
    on_axis_cb_state_changed as ui_on_axis_cb_state_changed,
    on_coord_ruler_cb_state_changed as ui_on_coord_ruler_cb_state_changed,
    on_extract_cb_state_changed as ui_on_extract_cb_state_changed,
    on_outline_cb_state_changed as ui_on_outline_cb_state_changed,
    on_point_probe_cb_state_changed as ui_on_point_probe_cb_state_changed,
    on_scalar_cb_state_changed as ui_on_scalar_cb_state_changed,
    on_scalar_legend_bar_cb_state_changed as ui_on_scalar_legend_bar_cb_state_changed,
    on_scalar_range_cb_state_changed as ui_on_scalar_range_cb_state_changed,
    on_streamline_cb_state_changed as ui_on_streamline_cb_state_changed,
    on_vector_cb_state_changed as ui_on_vector_cb_state_changed,
    on_vector_glyph_cb_state_changed as ui_on_vector_glyph_cb_state_changed,
    on_vector_legend_bar_cb_state_changed as ui_on_vector_legend_bar_cb_state_changed,
    on_vector_range_cb_state_changed as ui_on_vector_range_cb_state_changed,
    on_volume_cb_state_changed as ui_on_volume_cb_state_changed,
    refresh_after_extraction_edit as ui_refresh_after_extraction_edit,
)
from window_setup_ops import apply_icons as setup_apply_icons, init_renderer as setup_init_renderer


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

        self.domainOrth = [vec.copy() for vec in DOMAIN_ORTH]

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
        pp_set_point_probe_label(self, label, text)

    def _reset_point_probe_display(self) -> None:
        pp_reset_point_probe_display(self)

    def _current_point_probe_mode(self) -> str:
        return pp_current_point_probe_mode(self)

    def _set_point_probe_hint(self) -> None:
        pp_set_point_probe_hint(self)

    def _refresh_point_probe_source(self) -> None:
        pp_refresh_point_probe_source(self)

    def _sample_grid_index_and_point_id(
        self, image: Optional[vtk.vtkImageData], world_pos: tuple[float, float, float]
    ) -> tuple[Optional[tuple[int, int, int]], int]:
        return pp_sample_grid_index_and_point_id(self, image, world_pos)

    def _sample_scalar_value_at_world(
        self, world_pos: tuple[float, float, float]
    ) -> tuple[Optional[tuple[int, int, int]], Optional[float]]:
        return pp_sample_scalar_value_at_world(self, world_pos)

    def _sample_vector_value_at_world(
        self, world_pos: tuple[float, float, float]
    ) -> tuple[Optional[tuple[int, int, int]], Optional[tuple[float, float, float]], Optional[float]]:
        return pp_sample_vector_value_at_world(self, world_pos)

    def _format_vector_probe_text(
        self, vector_value: Optional[tuple[float, float, float]], magnitude: Optional[float]
    ) -> str:
        return pp_format_vector_probe_text(vector_value, magnitude)

    def _pick_world_position(
        self, renderer: vtk.vtkRenderer, click_x: int, click_y: int
    ) -> Optional[tuple[float, float, float]]:
        return pp_pick_world_position(self, renderer, click_x, click_y)

    @staticmethod
    def _normalized_vector(
        x: float, y: float, z: float
    ) -> Optional[tuple[float, float, float]]:
        return vtk_normalized_vector(x, y, z)

    def _on_vtk_middle_button_press(self, _obj, _event) -> None:
        vtk_on_vtk_middle_button_press(self, _obj, _event)

    def _clear_middle_pan_state(self) -> None:
        vtk_clear_middle_pan_state(self)

    def _is_middle_button_down(self) -> bool:
        return vtk_is_middle_button_down(self)

    def _on_vtk_middle_button_release(self, _obj, _event) -> None:
        vtk_on_vtk_middle_button_release(self, _obj, _event)

    def _on_vtk_mouse_move_lock_pan(self, _obj, _event) -> None:
        vtk_on_vtk_mouse_move_lock_pan(self, _obj, _event)

    def _on_vtk_left_button_press(self, _obj, _event) -> None:
        vtk_on_vtk_left_button_press(self, _obj, _event)

    def _update_point_probe_vector_dataset(
        self,
        vector_voi: tuple[int, int, int, int, int, int],
    ) -> None:
        pp_update_point_probe_vector_dataset(self, vector_voi)

    def _clear_point_probe_vector_dataset(self) -> None:
        pp_clear_point_probe_vector_dataset(self)

    def _update_coordinate_ruler(
        self,
        renderer: Optional[vtk.vtkRenderer],
        extent: Optional[tuple[int, int, int, int, int, int]],
    ) -> None:
        coord_update_coordinate_ruler(self, renderer, extent)

    def _init_renderer(self) -> None:
        setup_init_renderer(self)

    def _apply_icons(self) -> None:
        setup_apply_icons(self)

    def _init_domain_colors(self) -> None:
        colors = DEFAULT_DOMAIN_COLORS
        for i, (r, g, b) in enumerate(colors):
            self.domainRGB[i] = [r, g, b]
            self.domainRGBHold[i] = [r, g, b]
            item = self.domain_TW.item(i + 4, 0)
            if item is not None:
                item.setForeground(QtGui.QColor(int(r * 255), int(g * 255), int(b * 255)))

        self.domainList = list(DEFAULT_DOMAIN_LIST)

    def _init_vo2_colors(self) -> None:
        colors = DEFAULT_VO2_COLORS
        for i, (r, g, b) in enumerate(colors):
            self.vo2DomainRGB[i] = [r, g, b]
            self.vo2DomainRGBHold[i] = [r, g, b]
            item = self.vo2Domain_LW.item(i)
            if item is not None:
                item.setForeground(QtGui.QColor(int(r * 255), int(g * 255), int(b * 255)))
        self.vo2DomainList = list(DEFAULT_VO2_DOMAIN_LIST)

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
        open_slot_open_file_scalar(self)

    def on_scalarChoice_currentIndexChanged(self, _index: int) -> None:
        open_on_scalar_choice_current_index_changed(self, _index)

    def slotOpenFile_vector(self) -> None:
        open_slot_open_file_vector(self)

    def on_vectorChoice_currentIndexChanged(self, index) -> None:
        open_on_vector_choice_current_index_changed(self, index)

    def slotOpenFile_domain(self) -> None:
        open_slot_open_file_domain(self)

    def loadData(self, file_path: str) -> int:
        return data_load_data(self, file_path)

    def updateExtraction(self, x: int, y: int, z: int) -> None:
        data_update_extraction(self, x, y, z)

    def outputScalar(self, path: str, column_number: int, x: int, y: int, z: int) -> None:
        data_output_scalar(self, path, column_number, x, y, z)

    def outputVector(self, path: str, colX: int, colY: int, colZ: int, x: int, y: int, z: int) -> None:
        data_output_vector(self, path, colX, colY, colZ, x, y, z)

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
        pipeline_update_vtk(self, scalarname, vectorname)

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
        ui_on_axis_cb_state_changed(self, state)

    def on_coordRuler_CB_stateChanged(self, state: int) -> None:
        ui_on_coord_ruler_cb_state_changed(self, state)

    def on_pointProbe_CB_stateChanged(self, state: int) -> None:
        ui_on_point_probe_cb_state_changed(self, state)

    def on_outline_CB_stateChanged(self, state: int) -> None:
        ui_on_outline_cb_state_changed(self, state)

    def on_scalar_CB_stateChanged(self, state: int) -> None:
        ui_on_scalar_cb_state_changed(self, state)

    def on_volume_CB_stateChanged(self, state: int) -> None:
        ui_on_volume_cb_state_changed(self, state)

    def on_vector_CB_stateChanged(self, state: int) -> None:
        ui_on_vector_cb_state_changed(self, state)

    def on_vectorGlyph_CB_stateChanged(self, state: int) -> None:
        ui_on_vector_glyph_cb_state_changed(self, state)

    def on_vectorRange_CB_stateChanged(self, state: int) -> None:
        ui_on_vector_range_cb_state_changed(self, state)

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
        ui_on_streamline_cb_state_changed(self, state)

    def on_extract_CB_stateChanged(self, state: int) -> None:
        ui_on_extract_cb_state_changed(self, state)

    def _refresh_after_extraction_edit(self) -> None:
        ui_refresh_after_extraction_edit(self)

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
        ui_on_scalar_range_cb_state_changed(self, state)

    def on_scalarLegendBar_CB_stateChanged(self, state: int) -> None:
        ui_on_scalar_legend_bar_cb_state_changed(self, state)

    def on_vectorLegendBar_CB_stateChanged(self, state: int) -> None:
        ui_on_vector_legend_bar_cb_state_changed(self, state)

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

    def on_domain_Combo_currentIndexChanged(self, index) -> None:
        idx = index if isinstance(index, int) else self.domain_Combo.currentIndex()
        self.domain_stack.setCurrentIndex(idx)
        self.domainCriteria_Stack.setCurrentIndex(idx)

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
            threshold.SetInputConnection(readerDomain.GetOutputPort())
            threshold.AllScalarsOff()
            self._set_threshold_between(threshold, i - 0.5, i + 0.5)
            surface.SetInputConnection(threshold.GetOutputPort())
            surface.Update()
            has_data = (
                surface.GetOutput() is not None
                and surface.GetOutput().GetNumberOfPoints() > 0
                and surface.GetOutput().GetNumberOfCells() > 0
            )
            if has_data:
                smooth = vtk.vtkSmoothPolyDataFilter()
                normal = vtk.vtkPolyDataNormals()
                mapper = vtk.vtkDataSetMapper()
                smooth.SetInputConnection(surface.GetOutputPort())
                smooth.SetNumberOfIterations(30)
                smooth.SetRelaxationFactor(0.1)
                smooth.FeatureEdgeSmoothingOff()
                smooth.BoundarySmoothingOn()
                normal.SetInputConnection(smooth.GetOutputPort())
                normal.ComputePointNormalsOn()
                normal.ComputeCellNormalsOn()
                mapper.SetInputConnection(normal.GetOutputPort())
            else:
                mapper = vtk.vtkDataSetMapper()
                empty_poly = vtk.vtkPolyData()
                mapper.SetInputData(empty_poly)
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
            threshold.SetInputConnection(readerDomain.GetOutputPort())
            threshold.AllScalarsOff()
            self._set_threshold_between(threshold, i - 0.5, i + 0.5)
            surface.SetInputConnection(threshold.GetOutputPort())
            surface.Update()
            has_data = (
                surface.GetOutput() is not None
                and surface.GetOutput().GetNumberOfPoints() > 0
                and surface.GetOutput().GetNumberOfCells() > 0
            )
            if has_data:
                smooth = vtk.vtkSmoothPolyDataFilter()
                normal = vtk.vtkPolyDataNormals()
                mapper = vtk.vtkDataSetMapper()
                smooth.SetInputConnection(surface.GetOutputPort())
                smooth.SetNumberOfIterations(30)
                smooth.SetRelaxationFactor(0.1)
                smooth.FeatureEdgeSmoothingOff()
                smooth.BoundarySmoothingOn()
                normal.SetInputConnection(smooth.GetOutputPort())
                normal.ComputePointNormalsOn()
                normal.ComputeCellNormalsOn()
                mapper.SetInputConnection(normal.GetOutputPort())
            else:
                mapper = vtk.vtkDataSetMapper()
                empty_poly = vtk.vtkPolyData()
                mapper.SetInputData(empty_poly)
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
                    output_data[hold] = domain_type(
                        px,
                        py,
                        pz,
                        self.domainStandardValue,
                        self.domainStandardAngleRad,
                        self.domainOrth,
                    )
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
                    output_data[hold] = vo2_domain_type(
                        u1,
                        u2,
                        u3,
                        u4,
                        n1,
                        n2,
                        n3,
                        n4,
                        self.M1mod,
                        self.M2mod,
                        self.M1ang,
                        self.M2ang,
                    )
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
        export_save_image(self)

    def saveScene(self) -> None:
        export_save_scene(self)

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
        export_output_image(self, load)


    def _apply_png_dpi(self, path: str, dpi: int = 600) -> None:
        export_apply_png_dpi(path, dpi)

    def on_cameraSet_PB_released(self) -> None:
        export_on_camera_set_pb_released(self)

    def on_cameraGet_PB_released(self) -> None:
        export_on_camera_get_pb_released(self)

    def outputStatus(self, file_info: QtCore.QFileInfo) -> None:
        state_output_status(self, file_info)

    def slotOutputStatus(self) -> None:
        state_slot_output_status(self)

    def loadStatus(self, file_info: QtCore.QFileInfo) -> None:
        state_load_status(self, file_info)

    def slotLoadStatus(self) -> str:
        return state_slot_load_status(self)

    def slotBatch3D(self) -> None:
        dialog = Batch3D(self)
        dialog.show()

    def domainProcessing(self, filedir: str) -> int:
        return domain_processing(self, filedir)
