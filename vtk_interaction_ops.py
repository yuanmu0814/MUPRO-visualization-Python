from __future__ import annotations

import math
from typing import Optional


def normalized_vector(x: float, y: float, z: float) -> Optional[tuple[float, float, float]]:
    length = math.sqrt(x * x + y * y + z * z)
    if not math.isfinite(length) or length <= 1.0e-12:
        return None
    return (x / length, y / length, z / length)


def on_vtk_middle_button_press(view, _obj, _event) -> None:
    clear_middle_pan_state(view)
    if view.stackedWidget.currentIndex() != 0:
        return
    renderers = view.qvtkWidget.GetRenderWindow().GetRenderers()
    if renderers.GetNumberOfItems() == 0:
        return
    renderer = renderers.GetFirstRenderer()
    camera = renderer.GetActiveCamera()
    if camera is None:
        return

    position = camera.GetPosition()
    focal = camera.GetFocalPoint()
    view_up = camera.GetViewUp()
    view_direction = normalized_vector(
        focal[0] - position[0], focal[1] - position[1], focal[2] - position[2]
    )
    normalized_up = normalized_vector(view_up[0], view_up[1], view_up[2])
    if view_direction is None or normalized_up is None:
        return

    view._middlePanActive = True
    view._middlePanCamera = camera
    view._middlePanViewDirection = view_direction
    view._middlePanViewUp = normalized_up


def clear_middle_pan_state(view) -> None:
    view._middlePanActive = False
    view._middlePanCamera = None
    view._middlePanViewDirection = None
    view._middlePanViewUp = None


def is_middle_button_down(view) -> bool:
    interactor = view.qvtkWidget.GetRenderWindow().GetInteractor()
    if interactor is None or not hasattr(interactor, "GetMiddleButton"):
        return view._middlePanActive
    try:
        return bool(interactor.GetMiddleButton())
    except Exception:
        return view._middlePanActive


def on_vtk_middle_button_release(view, _obj, _event) -> None:
    clear_middle_pan_state(view)


def on_vtk_mouse_move_lock_pan(view, _obj, _event) -> None:
    if not view._middlePanActive:
        return
    if not is_middle_button_down(view):
        clear_middle_pan_state(view)
        return
    camera = view._middlePanCamera
    direction = view._middlePanViewDirection
    view_up = view._middlePanViewUp
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


def on_vtk_left_button_press(view, _obj, _event) -> None:
    def _forward_to_default_left_button() -> None:
        if hasattr(_obj, "OnLeftButtonDown"):
            _obj.OnLeftButtonDown()
            return
        interactor = view.qvtkWidget.GetRenderWindow().GetInteractor()
        style = interactor.GetInteractorStyle() if interactor is not None else None
        if style is not None and hasattr(style, "OnLeftButtonDown"):
            style.OnLeftButtonDown()

    if view.pointProbe_CB is None or not view.pointProbe_CB.isChecked():
        _forward_to_default_left_button()
        return
    if view.stackedWidget.currentIndex() != 0:
        _forward_to_default_left_button()
        return

    renderers = view.qvtkWidget.GetRenderWindow().GetRenderers()
    if renderers.GetNumberOfItems() == 0:
        _forward_to_default_left_button()
        return
    renderer = renderers.GetFirstRenderer()

    interactor = view.qvtkWidget.GetRenderWindow().GetInteractor()
    click_x, click_y = interactor.GetEventPosition()
    world = view._pick_world_position(renderer, click_x, click_y)
    if world is None:
        view._set_point_probe_label(view.pointProbeCoordValue_LB, "-")
        view._set_point_probe_label(view.pointProbeIndexValue_LB, "-")
        view._set_point_probe_label(view.pointProbeDataValue_LB, "No point picked.")
        return

    view._set_point_probe_label(
        view.pointProbeCoordValue_LB,
        f"x: {world[0]:.6g}\n"
        f"y: {world[1]:.6g}\n"
        f"z: {world[2]:.6g}",
    )

    mode = view._current_point_probe_mode()
    if mode == "vector":
        index_ijk, vector_value, magnitude = view._sample_vector_value_at_world(world)
        if index_ijk is None:
            view._set_point_probe_label(view.pointProbeIndexValue_LB, "-")
            if view._pointProbeVectorOutput is None:
                view._set_point_probe_label(view.pointProbeDataValue_LB, "No vector field loaded.")
            else:
                view._set_point_probe_label(view.pointProbeDataValue_LB, "Point is outside vector data.")
            return

        view._set_point_probe_label(
            view.pointProbeIndexValue_LB,
            f"x: {index_ijk[0] + 1}\n"
            f"y: {index_ijk[1] + 1}\n"
            f"z: {index_ijk[2] + 1}",
        )
        view._set_point_probe_label(
            view.pointProbeDataValue_LB,
            view._format_vector_probe_text(vector_value, magnitude),
        )
        return

    if mode == "scalar":
        index_ijk, scalar_value = view._sample_scalar_value_at_world(world)
        if index_ijk is None:
            view._set_point_probe_label(view.pointProbeIndexValue_LB, "-")
            if view._pointProbeScalarOutput is None:
                view._set_point_probe_label(view.pointProbeDataValue_LB, "No scalar field loaded.")
            else:
                view._set_point_probe_label(view.pointProbeDataValue_LB, "Point is outside scalar data.")
            return

        view._set_point_probe_label(
            view.pointProbeIndexValue_LB,
            f"x: {index_ijk[0] + 1}\n"
            f"y: {index_ijk[1] + 1}\n"
            f"z: {index_ijk[2] + 1}",
        )
        if scalar_value is None:
            view._set_point_probe_label(view.pointProbeDataValue_LB, "Scalar value unavailable.")
        else:
            view._set_point_probe_label(view.pointProbeDataValue_LB, f"{scalar_value:.8g}")
        return

    view._set_point_probe_label(view.pointProbeIndexValue_LB, "-")
    view._set_point_probe_label(view.pointProbeDataValue_LB, "No probe data loaded.")
    _forward_to_default_left_button()
