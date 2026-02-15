from __future__ import annotations

import math
from typing import Optional

from PyQt5 import QtWidgets
import vtk


def update_coordinate_ruler(
    view,
    renderer: Optional[vtk.vtkRenderer],
    extent: Optional[tuple[int, int, int, int, int, int]],
) -> None:
    if renderer is None:
        return
    if not renderer.HasViewProp(view.coordRulerActor):
        renderer.AddActor(view.coordRulerActor)

    enabled = (
        view.stackedWidget.currentIndex() == 0
        and view.coordRuler_CB is not None
        and view.coordRuler_CB.isChecked()
        and extent is not None
    )
    if not enabled:
        view.coordRulerActor.VisibilityOff()
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

    sx = _safe_positive_spacing(view.rescaleX_LE)
    sy = _safe_positive_spacing(view.rescaleY_LE)
    sz = _safe_positive_spacing(view.rescaleZ_LE)

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

    view.coordRulerActor.SetBounds(
        float(x0) * sx,
        float(x1_raw) * sx,
        float(y0) * sy,
        float(y1_raw) * sy,
        float(z0) * sz,
        float(z1_raw) * sz,
    )
    view.coordRulerActor.SetXAxisRange(x1, x2)
    view.coordRulerActor.SetYAxisRange(y1, y2)
    view.coordRulerActor.SetZAxisRange(z1, z2)
    view.coordRulerActor.SetCamera(renderer.GetActiveCamera())
    view.coordRulerActor.VisibilityOn()
