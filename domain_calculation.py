import math
from typing import Sequence

from constants import PI_VALUE


def domain_type(
    px: float,
    py: float,
    pz: float,
    domain_standard_value: float,
    domain_standard_angle_rad: float,
    domain_orth: Sequence[Sequence[float]],
) -> int:
    length = math.sqrt(px * px + py * py + pz * pz)
    if length <= domain_standard_value:
        return -1
    best_angle = PI_VALUE
    best_index = -1
    for i in range(1, 27):
        dot = px * domain_orth[i][0] + py * domain_orth[i][1] + pz * domain_orth[i][2]
        cos_value = dot / length
        if cos_value > 1:
            angle = 0
        elif cos_value < -1:
            angle = PI_VALUE
        else:
            angle = math.acos(cos_value)
        if angle < domain_standard_angle_rad and angle < best_angle:
            best_angle = angle
            best_index = i
    return best_index


def vo2_domain_type(
    u1: float,
    u2: float,
    u3: float,
    u4: float,
    n1: float,
    n2: float,
    n3: float,
    n4: float,
    m1_mod: float,
    m2_mod: float,
    m1_ang: float,
    m2_ang: float,
) -> int:
    u_mod = math.sqrt(u1 * u1 + u2 * u2 + u3 * u3 + u4 * u4)
    n_mod = math.sqrt(n1 * n1 + n2 * n2 + n3 * n3 + n4 * n4)
    if u_mod < m1_mod and n_mod < m1_mod:
        return 0
    if (
        u_mod > m1_mod
        and abs(u1 / math.sqrt(2) + u3 / math.sqrt(2)) / u_mod > math.cos(m1_ang)
        and n_mod > m1_mod
        and abs(n1 / math.sqrt(2) + n3 / math.sqrt(2)) / n_mod > math.cos(m1_ang)
    ):
        return 1
    if (
        u_mod > m1_mod
        and abs(u2 / math.sqrt(2) + u4 / math.sqrt(2)) / u_mod > math.cos(m1_ang)
        and n_mod > m1_mod
        and abs(n2 / math.sqrt(2) + n4 / math.sqrt(2)) / n_mod > math.cos(m1_ang)
    ):
        return 2
    if (
        u_mod > m1_mod
        and abs(u1 / math.sqrt(2) - u3 / math.sqrt(2)) / u_mod > math.cos(m1_ang)
        and n_mod > m1_mod
        and abs(n1 / math.sqrt(2) - n3 / math.sqrt(2)) / n_mod > math.cos(m1_ang)
    ):
        return 3
    if (
        u_mod > m1_mod
        and abs(u2 / math.sqrt(2) - u4 / math.sqrt(2)) / u_mod > math.cos(m1_ang)
        and n_mod > m1_mod
        and abs(n2 / math.sqrt(2) - n4 / math.sqrt(2)) / n_mod > math.cos(m1_ang)
    ):
        return 4
    if (
        u_mod > m2_mod
        and abs(u1) / u_mod > math.cos(m2_ang)
        and n_mod > m2_mod
        and abs(n1) / n_mod > math.cos(m2_ang)
    ):
        return 5
    if (
        u_mod > m2_mod
        and abs(u2) / u_mod > math.cos(m2_ang)
        and n_mod > m2_mod
        and abs(n2) / n_mod > math.cos(m2_ang)
    ):
        return 6
    if (
        u_mod > m2_mod
        and abs(u3) / u_mod > math.cos(m2_ang)
        and n_mod > m2_mod
        and abs(n3) / n_mod > math.cos(m2_ang)
    ):
        return 7
    if (
        u_mod > m2_mod
        and abs(u4) / u_mod > math.cos(m2_ang)
        and n_mod > m2_mod
        and abs(n4) / n_mod > math.cos(m2_ang)
    ):
        return 8
    return -1
