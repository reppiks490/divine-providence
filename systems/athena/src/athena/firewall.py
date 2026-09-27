from __future__ import annotations

from .contracts import DataPlane, Provenance


class PlaneViolation(ValueError):
    pass


def require_plane(provenance: Provenance, allowed: set[DataPlane]) -> None:
    if provenance.plane not in allowed:
        raise PlaneViolation(f"{provenance.plane.value} event not allowed; expected {sorted(x.value for x in allowed)}")


def forbid_research_to_production_direct(provenance: Provenance) -> None:
    if provenance.plane is DataPlane.RESEARCH:
        raise PlaneViolation("research-plane payload cannot directly authorize production behavior")
