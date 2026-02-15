from __future__ import annotations

import math
from typing import Optional

from PyQt5 import QtWidgets
import vtk


def set_point_probe_label(view, label: Optional[QtWidgets.QLabel], text: str) -> None:
    if label is not None:
        label.setText(text)


def reset_point_probe_display(view) -> None:
    set_point_probe_label(view, view.pointProbeCoordValue_LB, "-")
    set_point_probe_label(view, view.pointProbeIndexValue_LB, "-")
    if view.pointProbe_CB is not None and view.pointProbe_CB.isChecked():
        set_point_probe_hint(view)
    else:
        set_point_probe_label(view, view.pointProbeDataValue_LB, "Point probe is disabled.")


def current_point_probe_mode(view) -> str:
    if view.vector_CB.isChecked() and view._pointProbeVectorOutput is not None:
        return "vector"
    if view.scalar_CB.isChecked() and view._pointProbeScalarOutput is not None:
        return "scalar"
    if view._pointProbeVectorOutput is not None and view._pointProbeScalarOutput is None:
        return "vector"
    if view._pointProbeScalarOutput is not None:
        return "scalar"
    return "none"


def set_point_probe_hint(view) -> None:
    mode = current_point_probe_mode(view)
    if mode == "vector":
        set_point_probe_label(view, view.pointProbeDataValue_LB, "Click a point to view magnitude and X/Y/Z angles.")
    elif mode == "scalar":
        set_point_probe_label(view, view.pointProbeDataValue_LB, "Click a point to view original scalar value.")
    elif view.vector_CB.isChecked():
        set_point_probe_label(view, view.pointProbeDataValue_LB, "No vector field loaded.")
    elif view.scalar_CB.isChecked():
        set_point_probe_label(view, view.pointProbeDataValue_LB, "No scalar field loaded.")
    else:
        set_point_probe_label(view, view.pointProbeDataValue_LB, "No probe data loaded.")


def refresh_point_probe_source(view) -> None:
    mode = current_point_probe_mode(view)
    if mode == "vector":
        if view._pointProbeVectorColumns:
            set_point_probe_label(
                view, view.pointProbeSourceValue_LB, f"Vector columns:\n{view._pointProbeVectorColumns}"
            )
        else:
            set_point_probe_label(view, view.pointProbeSourceValue_LB, "Vector columns unknown.")
        return
    if mode == "scalar":
        if view._pointProbeScalarColumn is None:
            set_point_probe_label(view, view.pointProbeSourceValue_LB, "Scalar column unknown.")
        else:
            set_point_probe_label(view, view.pointProbeSourceValue_LB, f"Scalar column:\n{view._pointProbeScalarColumn}")
        return
    if view.vector_CB.isChecked():
        set_point_probe_label(view, view.pointProbeSourceValue_LB, "No vector field loaded.")
    elif view.scalar_CB.isChecked():
        set_point_probe_label(view, view.pointProbeSourceValue_LB, "No scalar field loaded.")
    else:
        set_point_probe_label(view, view.pointProbeSourceValue_LB, "No probe data loaded.")


def sample_grid_index_and_point_id(
    view, image: Optional[vtk.vtkImageData], world_pos: tuple[float, float, float]
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

        def _coord_to_index(coord: float, axis_origin: float, axis_spacing: float, low: int, high: int) -> int:
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


def sample_scalar_value_at_world(
    view, world_pos: tuple[float, float, float]
) -> tuple[Optional[tuple[int, int, int]], Optional[float]]:
    image = view._pointProbeScalarOutput
    index_ijk, point_id = sample_grid_index_and_point_id(view, image, world_pos)
    if index_ijk is None:
        return None, None
    if point_id < 0:
        return index_ijk, None

    scalars = image.GetPointData().GetScalars()
    if scalars is None or point_id >= scalars.GetNumberOfTuples():
        return index_ijk, None

    return index_ijk, float(scalars.GetTuple1(point_id))


def sample_vector_value_at_world(
    view, world_pos: tuple[float, float, float]
) -> tuple[Optional[tuple[int, int, int]], Optional[tuple[float, float, float]], Optional[float]]:
    image = view._pointProbeVectorOutput
    index_ijk, point_id = sample_grid_index_and_point_id(view, image, world_pos)
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


def format_vector_probe_text(
    vector_value: Optional[tuple[float, float, float]], magnitude: Optional[float]
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


def pick_world_position(
    view, renderer: vtk.vtkRenderer, click_x: int, click_y: int
) -> Optional[tuple[float, float, float]]:
    picked = view._pointProbePicker.Pick(float(click_x), float(click_y), 0.0, renderer)
    if picked > 0:
        picked_pos = view._pointProbePicker.GetPickPosition()
        if all(math.isfinite(v) for v in picked_pos):
            return (float(picked_pos[0]), float(picked_pos[1]), float(picked_pos[2]))

    world_picked = view._pointProbeWorldPicker.Pick(float(click_x), float(click_y), 0.0, renderer)
    if world_picked > 0:
        picked_pos = view._pointProbeWorldPicker.GetPickPosition()
        if all(math.isfinite(v) for v in picked_pos):
            return (float(picked_pos[0]), float(picked_pos[1]), float(picked_pos[2]))
    return None


def update_point_probe_vector_dataset(
    view,
    vector_voi: tuple[int, int, int, int, int, int],
) -> None:
    probe_extractor = vtk.vtkExtractVOI()
    probe_extractor.SetInputConnection(view.readerVectorOrigin.GetOutputPort())
    probe_extractor.SetVOI(*vector_voi)
    probe_extractor.SetSampleRate(1, 1, 1)
    probe_extractor.Update()
    view._pointProbeVectorExtractor = probe_extractor
    view._pointProbeVectorOutput = probe_extractor.GetOutput()

    choice_text = view.vectorChoice.currentText().strip() if view.vectorChoice.count() else ""
    view._pointProbeVectorColumns = choice_text or "123"


def clear_point_probe_vector_dataset(view) -> None:
    view._pointProbeVectorExtractor = None
    view._pointProbeVectorOutput = None
    view._pointProbeVectorColumns = None
