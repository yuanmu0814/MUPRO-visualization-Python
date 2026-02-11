from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class QCPScatterStyle:
    ssNone = "none"
    ssDot = "."
    ssCross = "x"
    ssPlus = "+"
    ssCircle = "o"
    ssDisc = "o"
    ssSquare = "s"
    ssDiamond = "D"
    ssStar = "*"
    ssTriangle = "^"
    ssTriangleInverted = "v"
    ssCrossSquare = "X"
    ssPlusSquare = "P"
    ssCrossCircle = "o"
    ssPlusCircle = "o"


@dataclass
class _AxisState:
    label: str = ""
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    auto_ticks: bool = True
    auto_tick_labels: bool = True
    tick_values: Optional[List[float]] = None
    tick_labels: Optional[List[str]] = None
    tick_labels_visible: bool = True
    visible: bool = True
    grid_visible: bool = False
    label_font: Optional[QtGui.QFont] = None
    tick_font: Optional[QtGui.QFont] = None
    tick_length: Optional[int] = None


def _qt_font_to_mpl(font: Optional[QtGui.QFont]) -> dict:
    if font is None:
        return {}
    return {
        "family": font.family(),
        "size": font.pointSize(),
        "weight": font.weight(),
    }


def _pen_to_mpl(pen: Optional[QtGui.QPen]) -> dict:
    if pen is None:
        return {}
    color = pen.color()
    color_tuple = (color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0)
    width = pen.widthF() if hasattr(pen, "widthF") else float(pen.width())
    style = pen.style()
    linestyle_map = {
        QtCore.Qt.SolidLine: "-",
        QtCore.Qt.DashLine: "--",
        QtCore.Qt.DotLine: ":",
        QtCore.Qt.DashDotLine: "-.",
        QtCore.Qt.DashDotDotLine: (0, (3, 1, 1, 1)),
    }
    linestyle = linestyle_map.get(style, "-")
    return {"color": color_tuple, "linewidth": width, "linestyle": linestyle}


class _GridCompat:
    def __init__(self, axis: "AxisCompat") -> None:
        self._axis = axis

    def setVisible(self, visible: bool) -> None:
        self._axis._state.grid_visible = bool(visible)


class AxisCompat:
    def __init__(self, plot: "QCustomPlot", which: str) -> None:
        self._plot = plot
        self._which = which
        self._state = _AxisState()

    def grid(self) -> _GridCompat:
        return _GridCompat(self)

    def setAutoTicks(self, enabled: bool) -> None:
        self._state.auto_ticks = bool(enabled)

    def setAutoTickLabels(self, enabled: bool) -> None:
        self._state.auto_tick_labels = bool(enabled)

    def setTickVector(self, values: List[float]) -> None:
        self._state.tick_values = list(values)

    def setTickVectorLabels(self, labels: List[str]) -> None:
        self._state.tick_labels = [str(label) for label in labels]

    def setTickLabels(self, enabled: bool) -> None:
        self._state.tick_labels_visible = bool(enabled)

    def setLabel(self, text: str) -> None:
        self._state.label = text

    def setRange(self, minimum: float, maximum: float) -> None:
        self._state.range_min = float(minimum)
        self._state.range_max = float(maximum)

    def setTickLength(self, _inner: int, outer: int) -> None:
        self._state.tick_length = int(outer)

    def setSubTickLength(self, _inner: int, _outer: int) -> None:
        return None

    def setVisible(self, visible: bool) -> None:
        self._state.visible = bool(visible)

    def setLabelFont(self, font: QtGui.QFont) -> None:
        self._state.label_font = font

    def setTickLabelFont(self, font: QtGui.QFont) -> None:
        self._state.tick_font = font


class _LegendCompat:
    def __init__(self, plot: "QCustomPlot") -> None:
        self._plot = plot
        self._visible = False
        self._font: Optional[QtGui.QFont] = None
        self._rect: Optional[Tuple[float, float, float, float]] = None

    def setVisible(self, visible: bool) -> None:
        self._visible = bool(visible)

    def setFont(self, font: QtGui.QFont) -> None:
        self._font = font

    def setOuterRect(self, rect: QtCore.QRect) -> None:
        self._rect = (rect.x(), rect.y(), rect.width(), rect.height())


class _InsetLayoutCompat:
    def __init__(self, legend: _LegendCompat) -> None:
        self._legend = legend
        self._rect: Optional[Tuple[float, float, float, float]] = None

    def elementCount(self) -> int:
        return 1

    def setInsetPlacement(self, _index: int, _placement: Any) -> None:
        return None

    def setInsetRect(self, _index: int, rect: QtCore.QRectF) -> None:
        self._rect = (rect.x(), rect.y(), rect.width(), rect.height())
        self._legend._rect = self._rect


class _AxisRectCompat:
    def __init__(self, legend: _LegendCompat) -> None:
        self._inset = _InsetLayoutCompat(legend)

    def insetLayout(self) -> _InsetLayoutCompat:
        return self._inset


class QCPPlotTitle:
    def __init__(self, plot: "QCustomPlot", text: str) -> None:
        self._plot = plot
        self._text = text
        self._font: Optional[QtGui.QFont] = None

    def setFont(self, font: QtGui.QFont) -> None:
        self._font = font


class _PlotLayoutCompat:
    def __init__(self, plot: "QCustomPlot") -> None:
        self._plot = plot
        self._title: Optional[QCPPlotTitle] = None

    def rowCount(self) -> int:
        return 1 if self._title is None else 2

    def insertRow(self, _row: int) -> None:
        return None

    def addElement(self, _row: int, _col: int, element: QCPPlotTitle) -> None:
        self._title = element

    def removeAt(self, _row: int) -> None:
        self._title = None

    def updateLayout(self) -> None:
        return None

    def simplify(self) -> None:
        return None

    def element(self, _row: int, _col: int) -> Optional[QCPPlotTitle]:
        return self._title


class _GraphCompat:
    def __init__(self, plot: "QCustomPlot", axis: str) -> None:
        self._plot = plot
        self._axis = axis
        self._x: List[float] = []
        self._y: List[float] = []
        self._pen: Optional[QtGui.QPen] = None
        self._scatter: Optional[str] = None
        self._name: str = ""

    def setData(self, x: List[float], y: List[float]) -> None:
        self._x = list(x)
        self._y = list(y)

    def setPen(self, pen: QtGui.QPen) -> None:
        self._pen = pen

    def setScatterStyle(self, scatter: Any) -> None:
        self._scatter = scatter

    def setName(self, name: str) -> None:
        self._name = name


class QCustomPlot(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._figure = Figure(figsize=(5, 4), dpi=100)
        self._canvas = FigureCanvas(self._figure)
        self._axis_main = self._figure.add_subplot(111)
        self._axis_overlay = self._figure.add_subplot(111, frameon=False)
        self._axis_overlay.patch.set_alpha(0.0)
        self._axis_overlay.xaxis.set_ticks_position("top")
        self._axis_overlay.yaxis.set_ticks_position("right")
        self._axis_overlay.xaxis.set_label_position("top")
        self._axis_overlay.yaxis.set_label_position("right")
        self._axis_overlay.tick_params(labelleft=False, labelbottom=False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._graphs: List[_GraphCompat] = []
        self.xAxis = AxisCompat(self, "x")
        self.yAxis = AxisCompat(self, "y")
        self.xAxis2 = AxisCompat(self, "x2")
        self.yAxis2 = AxisCompat(self, "y2")
        self.legend = _LegendCompat(self)
        self._axis_rect = _AxisRectCompat(self.legend)
        self._plot_layout = _PlotLayoutCompat(self)

    def addGraph(self, xAxis: Optional[AxisCompat] = None, yAxis: Optional[AxisCompat] = None) -> None:
        axis = "main"
        if xAxis is self.xAxis2 or yAxis is self.yAxis2:
            axis = "overlay"
        self._graphs.append(_GraphCompat(self, axis))

    def graph(self, index: int) -> _GraphCompat:
        return self._graphs[index]

    def clearGraphs(self) -> None:
        self._graphs = []
        self._axis_main.cla()
        self._axis_overlay.cla()

    def clearItems(self) -> None:
        return None

    def clearPlottables(self) -> None:
        return None

    def plotLayout(self) -> _PlotLayoutCompat:
        return self._plot_layout

    def axisRect(self) -> _AxisRectCompat:
        return self._axis_rect

    def savePng(self, path: str, width: int = 0, height: int = 0, dpi: int = 600) -> None:
        if width > 0 and height > 0 and dpi > 0:
            original_size = self._figure.get_size_inches()
            try:
                self._figure.set_size_inches(width / float(dpi), height / float(dpi))
                self._figure.savefig(path, dpi=dpi)
            finally:
                self._figure.set_size_inches(original_size)
        else:
            self._figure.savefig(path, dpi=max(1, int(dpi)))

    def _apply_axis_state(self, axis: AxisCompat, mpl_axis: Any, is_x: bool) -> None:
        state = axis._state
        if is_x:
            mpl_axis.set_xlabel(state.label, fontdict=_qt_font_to_mpl(state.label_font))
        else:
            mpl_axis.set_ylabel(state.label, fontdict=_qt_font_to_mpl(state.label_font))

        if state.range_min is not None and state.range_max is not None:
            if is_x:
                mpl_axis.set_xlim(state.range_min, state.range_max)
            else:
                mpl_axis.set_ylim(state.range_min, state.range_max)

        if state.tick_values is not None and not state.auto_ticks:
            if is_x:
                mpl_axis.set_xticks(state.tick_values)
            else:
                mpl_axis.set_yticks(state.tick_values)
            if state.tick_labels is not None and state.auto_tick_labels is False:
                if is_x:
                    mpl_axis.set_xticklabels(state.tick_labels)
                else:
                    mpl_axis.set_yticklabels(state.tick_labels)

        if state.tick_labels_visible is False:
            if is_x:
                mpl_axis.set_xticklabels([])
            else:
                mpl_axis.set_yticklabels([])

        if state.tick_font is not None:
            for tick in mpl_axis.get_xticklabels() if is_x else mpl_axis.get_yticklabels():
                tick.set_fontsize(state.tick_font.pointSize())
                tick.set_fontfamily(state.tick_font.family())

        mpl_axis.grid(state.grid_visible, axis="x" if is_x else "y")

        if state.tick_length is not None:
            mpl_axis.tick_params(axis="x" if is_x else "y", length=state.tick_length)

        if not state.visible:
            if is_x:
                mpl_axis.get_xaxis().set_visible(False)
            else:
                mpl_axis.get_yaxis().set_visible(False)
        else:
            if is_x:
                mpl_axis.get_xaxis().set_visible(True)
            else:
                mpl_axis.get_yaxis().set_visible(True)

    def _apply_plot_title(self) -> None:
        title = self._plot_layout.element(0, 0)
        if title is None:
            self._axis_main.set_title("")
            return
        font = _qt_font_to_mpl(title._font)
        self._axis_main.set_title(title._text, fontdict=font)

    def _apply_legend(self) -> None:
        if not self.legend._visible:
            self._axis_main.legend_.remove() if self._axis_main.legend_ else None
            return
        handles = []
        labels = []
        for axis in (self._axis_main, self._axis_overlay):
            h, l = axis.get_legend_handles_labels()
            handles.extend(h)
            labels.extend(l)
        if not handles:
            return
        font = _qt_font_to_mpl(self.legend._font)
        legend_kwargs = {}
        if self.legend._rect is not None:
            x, y, w, h = self.legend._rect
            legend_kwargs["bbox_to_anchor"] = (x, y, w, h)
            legend_kwargs["loc"] = "upper left"
        if font:
            legend_kwargs["prop"] = font
        self._axis_main.legend(handles, labels, **legend_kwargs)

    def replot(self) -> None:
        self._axis_main.cla()
        self._axis_overlay.cla()
        self._axis_overlay.patch.set_alpha(0.0)
        self._axis_overlay.xaxis.set_ticks_position("top")
        self._axis_overlay.yaxis.set_ticks_position("right")
        self._axis_overlay.xaxis.set_label_position("top")
        self._axis_overlay.yaxis.set_label_position("right")
        self._axis_overlay.tick_params(labelleft=False, labelbottom=False)

        for graph in self._graphs:
            if graph._axis == "overlay":
                axis = self._axis_overlay
            else:
                axis = self._axis_main
            if not graph._x or not graph._y:
                continue
            style = _pen_to_mpl(graph._pen)
            marker = None
            if graph._scatter and graph._scatter != QCPScatterStyle.ssNone:
                marker = graph._scatter
            axis.plot(
                graph._x,
                graph._y,
                label=graph._name,
                marker=marker,
                **style,
            )

        self._apply_axis_state(self.xAxis, self._axis_main, True)
        self._apply_axis_state(self.yAxis, self._axis_main, False)
        self._apply_axis_state(self.xAxis2, self._axis_overlay, True)
        self._apply_axis_state(self.yAxis2, self._axis_overlay, False)
        self._apply_plot_title()
        self._apply_legend()

        self._canvas.draw_idle()
