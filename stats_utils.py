from typing import Sequence


def get_min(values: Sequence[float]) -> float:
    return min(values) if values else 0.0


def get_max(values: Sequence[float]) -> float:
    return max(values) if values else 0.0


def get_avg(values: Sequence[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0
