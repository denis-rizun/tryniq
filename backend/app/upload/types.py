from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiarSegment:
    t_start: float
    t_end: float
    cluster_id: int
