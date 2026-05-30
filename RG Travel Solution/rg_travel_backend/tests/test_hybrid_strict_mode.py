from __future__ import annotations

import pytest

from services.hybrid_group_planner import (
    HybridDistance,
    HybridProviderUnavailable,
    probe_hybrid_provider,
)


def test_hybrid_strict_raises_when_road_distance_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: None)

    dist = HybridDistance(strict_required=True)

    with pytest.raises(HybridProviderUnavailable):
        dist.km((19.0760, 72.8777), (19.0820, 72.8850))

    assert dist.degraded_edges == 1


def test_hybrid_non_strict_falls_back_to_haversine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: None)

    dist = HybridDistance(strict_required=False)
    km = dist.km((19.0760, 72.8777), (19.0820, 72.8850))

    assert km > 0
    assert dist.degraded_edges == 1


def test_probe_reports_not_ready_when_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: None)

    diag = probe_hybrid_provider(timeout_sec=0.1)

    assert diag["ready"] is False
    assert diag["provider"] == "osrm"
    assert "error" in diag and diag["error"]
