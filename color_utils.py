from __future__ import annotations

import math
from typing import Sequence

from constants import PI_VALUE


def convert_hsl_to_rgb(hue: float, saturation: float, lightness: float) -> list[float]:
    if saturation <= 1.0e-6:
        return [lightness * 255, lightness * 255, lightness * 255]
    if lightness < 0.5:
        v2 = lightness * (1 + saturation)
    else:
        v2 = (lightness + saturation) - (saturation * lightness)
    v1 = 2 * lightness - v2

    def hue_to_rgb(v1_: float, v2_: float, vh: float) -> float:
        if vh < 0:
            vh += 1
        if vh > 1:
            vh -= 1
        if (6 * vh) < 1:
            return v1_ + (v2_ - v1_) * 6 * vh
        if (2 * vh) < 1:
            return v2_
        if (3 * vh) < 2:
            return v1_ + (v2_ - v1_) * ((2 / 3.0) - vh) * 6
        return v1_

    return [
        255 * hue_to_rgb(v1, v2, hue / 360.0 + (1 / 3.0)),
        255 * hue_to_rgb(v1, v2, hue / 360.0),
        255 * hue_to_rgb(v1, v2, hue / 360.0 - (1 / 3.0)),
    ]


def rescale(value: float, value_range: Sequence[float]) -> float:
    if value_range[1] - value_range[0] < 1.0e-6:
        return 0.5
    if value <= value_range[0]:
        return 0.0
    if value >= value_range[1]:
        return 1.0
    return (value - value_range[0]) / (value_range[1] - value_range[0])


def get_rgb(
    px: float,
    py: float,
    pz: float,
    magnitude_range: Sequence[float],
    z_range: Sequence[float],
) -> list[float]:
    xy_magnitude = math.sqrt(px * px + py * py)
    if xy_magnitude < 1.0e-6:
        hue = 0.0
        saturation = 0.0
        lightness = rescale(pz, z_range)
    else:
        if py >= 0:
            hue = math.acos(px / xy_magnitude) / PI_VALUE * 180
        else:
            hue = 360 - (math.acos(px / xy_magnitude) / PI_VALUE * 180)
        magnitude = math.sqrt(px * px + py * py + pz * pz)
        saturation = rescale(magnitude, magnitude_range)
        lightness = (pz / magnitude + 1) / 2.0 if magnitude != 0 else 0.5
    return convert_hsl_to_rgb(hue, saturation, lightness)
