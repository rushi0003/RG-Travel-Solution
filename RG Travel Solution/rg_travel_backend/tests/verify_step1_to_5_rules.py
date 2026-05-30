"""
Verify Step 1-5 group creation business rules without pytest dependency.

Run:
  python rg_travel_backend/tests/verify_step1_to_5_rules.py
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.hybrid_group_planner import EmployeeNode, HybridDistance, VehicleNode, plan_groups_hybrid


def _mk_emp(emp_id: int, lat: float, lng: float) -> EmployeeNode:
    return EmployeeNode(
        id=emp_id,
        name=f"E{emp_id}",
        mobile=f"9{emp_id:09d}",
        address=f"A{emp_id}",
        lat=lat,
        lng=lng,
    )


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _run_plan(employees: List[EmployeeNode], vehicles: List[VehicleNode], prioritize_6: bool = True) -> Dict[str, Any]:
    # Stable tests: avoid external road provider dependency.
    original = HybridDistance._road_km_osrm
    HybridDistance._road_km_osrm = lambda self, a, b: 1.0  # type: ignore[assignment]
    try:
        return plan_groups_hybrid(
            employees=employees,
            vehicles=vehicles,
            office=(19.0760, 72.8777),
            prioritize_6_when_mixed=prioritize_6,
            strict_hybrid=True,
        )
    finally:
        HybridDistance._road_km_osrm = original  # type: ignore[assignment]


def verify_step_1_vehicle_type_groups() -> None:
    employees = [_mk_emp(i, 19.1 + i * 0.0001, 72.9 + i * 0.0001) for i in range(1, 11)]
    vehicles = [
        VehicleNode("d6", "D6", "CAB6", 6, False, 0.0, 0.0),
        VehicleNode("d4", "D4", "CAB4", 4, False, 0.0, 0.0),
    ]
    plan = _run_plan(employees, vehicles, prioritize_6=True)
    group_types = [int(g["vehicle_type"]) for g in plan["groups"]]
    _require(all(vt in (4, 6) for vt in group_types), "Step1 failed: non 4/6 group type produced")


def verify_step_2_go_home_then_6_priority() -> None:
    employees = [_mk_emp(i, 19.1 + i * 0.0001, 72.9 + i * 0.0001) for i in range(1, 7)]
    vehicles = [
        VehicleNode("d4", "D4", "CAB4", 4, False, 0.0, 0.0),
        VehicleNode("d6_go", "D6GO", "CAB6", 6, True, 19.101, 72.901),
    ]
    plan = _run_plan(employees, vehicles, prioritize_6=True)
    _require(len(plan["groups"]) >= 1, "Step2 failed: no groups created")
    first = plan["groups"][0]
    _require(str(first["driver_id"]) == "d6_go", "Step2 failed: go-home driver not prioritized first")
    _require(int(first["vehicle_type"]) == 6, "Step2 failed: expected 6-seater first in mixed selection")


def verify_step_3_extra_vehicles_next_eligible() -> None:
    employees = [_mk_emp(1, 19.1, 72.9), _mk_emp(2, 19.1001, 72.9001)]
    vehicles = [
        VehicleNode("d1", "D1", "CAB1", 4, False, 0.0, 0.0),
        VehicleNode("d2", "D2", "CAB2", 4, False, 0.0, 0.0),
        VehicleNode("d3", "D3", "CAB3", 4, False, 0.0, 0.0),
    ]
    plan = _run_plan(employees, vehicles, prioritize_6=False)
    _require(len(plan["unassigned_vehicles"]) == 2, "Step3 failed: expected 2 unassigned vehicles")
    _require(
        all(bool(v.get("eligible_for_next_group_creation")) for v in plan["unassigned_vehicles"]),
        "Step3 failed: unassigned vehicles are not marked next-group eligible",
    )


def verify_step_4_extra_employees_next_trip_eligible() -> None:
    employees = [_mk_emp(i, 19.1 + i * 0.0001, 72.9 + i * 0.0001) for i in range(1, 11)]
    vehicles = [VehicleNode("d6", "D6", "CAB6", 6, False, 0.0, 0.0)]
    plan = _run_plan(employees, vehicles, prioritize_6=True)
    _require(len(plan["unassigned_employees"]) == 4, "Step4 failed: expected 4 unassigned employees")
    _require(
        all(bool(e.get("eligible_for_next_trip")) for e in plan["unassigned_employees"]),
        "Step4 failed: unassigned employees not marked next-trip eligible",
    )


def verify_step_5_capacity_fill_then_last_partial() -> None:
    employees = [_mk_emp(i, 19.1 + i * 0.0001, 72.9 + i * 0.0001) for i in range(1, 7)]
    vehicles = [
        VehicleNode("d1", "D1", "CAB1", 4, False, 0.0, 0.0),
        VehicleNode("d2", "D2", "CAB2", 4, False, 0.0, 0.0),
    ]
    plan = _run_plan(employees, vehicles, prioritize_6=False)
    sizes = [int(g["group_size"]) for g in plan["groups"]]
    _require(sizes == [4, 2], f"Step5 failed: expected [4, 2], got {sizes}")
    _require(int(plan["groups"][0]["vehicle_type"]) == 4, "Step5 failed: first group capacity should be 4")


def main() -> int:
    print("=== verify_step1_to_5_rules ===")
    verify_step_1_vehicle_type_groups()
    print("Step 1: PASS")
    verify_step_2_go_home_then_6_priority()
    print("Step 2: PASS")
    verify_step_3_extra_vehicles_next_eligible()
    print("Step 3: PASS")
    verify_step_4_extra_employees_next_trip_eligible()
    print("Step 4: PASS")
    verify_step_5_capacity_fill_then_last_partial()
    print("Step 5: PASS")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESULT: FAIL - {exc}")
        raise SystemExit(1)
