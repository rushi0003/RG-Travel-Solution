# Tracking UI Sign-off (Driver/Admin/Employee)

Date: `2026-03-03`  
Build/Branch: `________________`  
Tester: `________________`

## Pre-check (must pass before UI sign-off)
- [ ] `powershell -ExecutionPolicy Bypass -File .\run_tracking_release_gate.ps1 -CheckSocket` passed
- [ ] Backend reachable at `http://127.0.0.1:5000/api/health`
- [ ] Flutter app launched in Chrome

## A) Driver Dashboard Tracking Health
- [ ] Open driver dashboard and enable tracking
- [ ] Initial state shows waiting message
- [ ] First sync shows `Last sync ... ago`
- [ ] HTTP chip appears (for example `HTTP 200`)
- [ ] `Retry now` updates health state immediately
- [ ] Offline simulation shows warning/retry behavior
- [ ] Recovery after online restore works

Evidence:
- [ ] `screenshots/driver_health_waiting.png`
- [ ] `screenshots/driver_health_synced.png`
- [ ] `screenshots/driver_health_offline.png`

## B) Admin Live Tracking (OSM)
- [ ] Open admin live tracking for active route
- [ ] OSM tiles render
- [ ] Driver marker updates with latest location
- [ ] Route polyline is visible
- [ ] Stale/offline banner appears during disconnect
- [ ] Retry action recovers tracking

Evidence:
- [ ] `screenshots/admin_live_map_ok.png`
- [ ] `screenshots/admin_live_map_stale.png`

## C) Employee Live Tracking (OSM)
- [ ] Open employee live tracking for same route
- [ ] OSM tiles render
- [ ] Marker location is consistent with admin view
- [ ] Stale/offline state and retry behavior works

Evidence:
- [ ] `screenshots/employee_live_map_ok.png`
- [ ] `screenshots/employee_live_map_stale.png`

## Defects Found
- [ ] None
- Notes:
  - `________________________________________`
  - `________________________________________`

## Final Decision
- [ ] PASS (ready for rollout)
- [ ] FAIL (fixes required)

Sign-off:
- Tester: `________________`
- Date/Time: `________________`
