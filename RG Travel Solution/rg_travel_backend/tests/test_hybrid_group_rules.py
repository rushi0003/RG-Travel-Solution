from __future__ import annotations

import pytest

from services.hybrid_group_planner import (
    EmployeeNode,
    HybridDistance,
    VehicleNode,
    plan_groups_hybrid,
)


def _mk_emp(emp_id: int, lat: float, lng: float) -> EmployeeNode:
    return EmployeeNode(
        id=emp_id,
        name=f"E{emp_id}",
        mobile=f"9{emp_id:09d}",
        address=f"A{emp_id}",
        lat=lat,
        lng=lng,
    )


def test_partial_last_vehicle_is_allowed_for_4_plus_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: 1.0)

    employees = [
        _mk_emp(1, 19.1000, 72.9000),
        _mk_emp(2, 19.1010, 72.9010),
        _mk_emp(3, 19.1020, 72.9020),
        _mk_emp(4, 19.1030, 72.9030),
        _mk_emp(5, 19.1040, 72.9040),
        _mk_emp(6, 19.1050, 72.9050),
    ]
    vehicles = [
        VehicleNode("d1", "D1", "CAB1", 4, False, 0.0, 0.0),
        VehicleNode("d2", "D2", "CAB2", 4, False, 0.0, 0.0),
    ]

    plan = plan_groups_hybrid(
        employees=employees,
        vehicles=vehicles,
        office=(19.0760, 72.8777),
        prioritize_6_when_mixed=True,
        strict_hybrid=True,
    )

    sizes = [int(g["group_size"]) for g in plan["groups"]]
    assert sizes == [4, 2]
    assert len(plan["unassigned_employees"]) == 0
    assert len(plan["unassigned_vehicles"]) == 0


def test_go_home_vehicle_gets_first_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: 1.0)

    employees = [
        _mk_emp(1, 19.1000, 72.9000),
        _mk_emp(2, 19.1010, 72.9010),
        _mk_emp(3, 19.1020, 72.9020),
        _mk_emp(4, 19.1030, 72.9030),
        _mk_emp(5, 19.1040, 72.9040),
        _mk_emp(6, 19.1050, 72.9050),
    ]
    vehicles = [
        VehicleNode("d4", "D4", "CAB4", 4, False, 0.0, 0.0),
        VehicleNode("d6", "D6", "CAB6", 6, True, 19.1010, 72.9010),
    ]

    plan = plan_groups_hybrid(
        employees=employees,
        vehicles=vehicles,
        office=(19.0760, 72.8777),
        prioritize_6_when_mixed=True,
        strict_hybrid=True,
    )

    assert len(plan["groups"]) == 1
    assert str(plan["groups"][0]["driver_id"]) == "d6"
    assert int(plan["groups"][0]["vehicle_type"]) == 6
    assert int(plan["groups"][0]["group_size"]) == 6
    assert len(plan["unassigned_vehicles"]) == 1
    assert plan["unassigned_vehicles"][0]["driver_id"] == "d4"
    assert plan["unassigned_vehicles"][0]["eligible_for_next_group_creation"] is True


def test_extra_vehicles_remain_unassigned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: 1.0)

    employees = [
        _mk_emp(1, 19.1000, 72.9000),
        _mk_emp(2, 19.1010, 72.9010),
    ]
    vehicles = [
        VehicleNode("d1", "D1", "CAB1", 4, False, 0.0, 0.0),
        VehicleNode("d2", "D2", "CAB2", 4, False, 0.0, 0.0),
        VehicleNode("d3", "D3", "CAB3", 4, False, 0.0, 0.0),
    ]

    plan = plan_groups_hybrid(
        employees=employees,
        vehicles=vehicles,
        office=(19.0760, 72.8777),
        prioritize_6_when_mixed=True,
        strict_hybrid=True,
    )

    assert len(plan["groups"]) == 1
    assert [int(g["group_size"]) for g in plan["groups"]] == [2]
    assert len(plan["unassigned_vehicles"]) == 2
    assert all(v.get("eligible_for_next_group_creation") is True for v in plan["unassigned_vehicles"])
    assert len(plan["unassigned_employees"]) == 0


def test_extra_employees_remain_eligible_for_next_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: 1.0)

    employees = [_mk_emp(i, 19.1000 + (i * 0.0001), 72.9000 + (i * 0.0001)) for i in range(1, 11)]
    vehicles = [
        VehicleNode("d6", "D6", "CAB6", 6, False, 0.0, 0.0),
    ]

    plan = plan_groups_hybrid(
        employees=employees,
        vehicles=vehicles,
        office=(19.0760, 72.8777),
        prioritize_6_when_mixed=True,
        strict_hybrid=True,
    )

    assert len(plan["groups"]) == 1
    assert int(plan["groups"][0]["group_size"]) == 6
    assert len(plan["unassigned_employees"]) == 4
    assert all(e.get("eligible_for_next_trip") is True for e in plan["unassigned_employees"])
    assert all(e.get("reason") == "insufficient_vehicles_or_capacity" for e in plan["unassigned_employees"])


def test_plan_falls_back_to_haversine_when_strict_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: None)

    employees = [
        _mk_emp(1, 19.1000, 72.9000),
        _mk_emp(2, 19.1010, 72.9010),
    ]
    vehicles = [
        VehicleNode("d1", "D1", "CAB1", 4, False, 0.0, 0.0),
    ]

    plan = plan_groups_hybrid(
        employees=employees,
        vehicles=vehicles,
        office=(19.0760, 72.8777),
        prioritize_6_when_mixed=True,
        strict_hybrid=True,
    )

    assert len(plan["groups"]) == 1
    assert plan["hybrid_fallback_used"] is True
    assert plan["hybrid_strict"] is False
    assert isinstance(plan["hybrid_fallback_reason"], str) and plan["hybrid_fallback_reason"]


def test_plan_supports_vehicle_batching_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTE_PROVIDER", "osrm")
    monkeypatch.setattr(HybridDistance, "_road_km_osrm", lambda self, a, b: 1.0)

    employees = [_mk_emp(i, 19.1000 + (i * 0.0001), 72.9000 + (i * 0.0001)) for i in range(1, 13)]
    vehicles = [
        VehicleNode("d1", "D1", "CAB1", 4, False, 0.0, 0.0),
        VehicleNode("d2", "D2", "CAB2", 4, False, 0.0, 0.0),
        VehicleNode("d3", "D3", "CAB3", 4, False, 0.0, 0.0),
    ]

    plan = plan_groups_hybrid(
        employees=employees,
        vehicles=vehicles,
        office=(19.0760, 72.8777),
        prioritize_6_when_mixed=True,
        strict_hybrid=True,
        vehicle_batch_size=2,
    )

    assert len(plan["groups"]) == 3
    assert int(plan["vehicle_batches"]) == 2
    assert int(plan["vehicle_batch_size"]) == 2
