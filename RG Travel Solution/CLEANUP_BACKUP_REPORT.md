# RG Travel Solution Cleanup Backup Report

Generated before cleanup.

Project root: `C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution`

Scope: delete only high-confidence generated artifacts requested by the user:

- Python cache: `__pycache__/`, `.pytest_cache/`, `.venv/`, `venv/`
- Flutter cache: `.dart_tool/`, `build/`
- Test databases: `test_sos_*.db`
- Runtime logs: `*.log`, `run_stdout.log`, `run_stderr.log`, `server.log`, `backend_test.log`, `app_log.txt`
- Analyzer outputs: `analysis*.txt`, `analyze*.txt`, `all_errors*.txt`, `flutter_errors.txt`

Protected and not targeted:

- Source code
- Flutter assets
- Database schema files
- Migration files
- API files
- Documentation files
- README files
- `requirements.txt`
- `pubspec.yaml`
- `rg_travel_backend/rg_travel.db`

Expected recovered space from target scan: 249,156,436 bytes / 237.61 MB.

## Targeted Folders

| Path | Size |
|---|---:|
| `.pytest_cache` | 5,276 B |
| `.venv` | 19,270,162 B |
| `__pycache__` | 91,194 B |
| `rg_backend_operations_app/.dart_tool` | 2,765,934 B |
| `rg_backend_operations_app/build` | 105,845,108 B |
| `rg_travel_backend/.pytest_cache` | 542 B |
| `rg_travel_backend/__pycache__` | 199,967 B |
| `rg_travel_backend/config/__pycache__` | 22,231 B |
| `rg_travel_backend/db/__pycache__` | 66,958 B |
| `rg_travel_backend/repositories/__pycache__` | 120,302 B |
| `rg_travel_backend/routes/__pycache__` | 646,851 B |
| `rg_travel_backend/seeds/__pycache__` | 51,626 B |
| `rg_travel_backend/services/__pycache__` | 520,072 B |
| `rg_travel_backend/tests/__pycache__` | 314,098 B |
| `rg_travel_backend/tools/__pycache__` | 52,618 B |
| `rg_travel_backend/utils/__pycache__` | 56,701 B |
| `rg_travel_backend/venv` | 27,210,463 B |
| `rg_travel_flutter/.dart_tool` | 11,086,872 B |
| `rg_travel_flutter/build` | 69,030,008 B |

## Targeted Files

| Path | Size |
|---|---:|
| `rg_backend_operations_app/flutter_web_stderr.log` | 0 B |
| `rg_backend_operations_app/flutter_web_stdout.log` | 578 B |
| `rg_travel_backend/app_log.txt` | 5,768 B |
| `rg_travel_backend/backend_test.log` | 2,310 B |
| `rg_travel_backend/debug_verify.log` | 215 B |
| `rg_travel_backend/logs/tracking_audit.log` | 416,435 B |
| `rg_travel_backend/run_stderr.log` | 1,371 B |
| `rg_travel_backend/run_stdout.log` | 0 B |
| `rg_travel_backend/server.log` | 1,930 B |
| `rg_travel_backend/test_sos_7e481c1c.db` | 417,792 B |
| `rg_travel_backend/test_sos_c123bc62.db` | 417,792 B |
| `rg_travel_backend/test_sos_eb326872.db` | 417,792 B |
| `rg_travel_backend/test_sos_f9d622c8.db` | 417,792 B |
| `rg_travel_backend/test_sos_fb07464a.db` | 417,792 B |
| `rg_travel_backend/test_sos_rating_simple.db` | 417,792 B |
| `rg_travel_flutter/all_errors.txt` | 1,008,146 B |
| `rg_travel_flutter/all_errors_updated.txt` | 1,008,146 B |
| `rg_travel_flutter/all_errors_utf8.txt` | 504,075 B |
| `rg_travel_flutter/analysis.txt` | 516,997 B |
| `rg_travel_flutter/analysis_output.txt` | 31,530 B |
| `rg_travel_flutter/analysis_output_2.txt` | 69,664 B |
| `rg_travel_flutter/analyze_output.txt` | 1,100,884 B |
| `rg_travel_flutter/analyze_output_2.txt` | 1,024,228 B |
| `rg_travel_flutter/analyze_output_3.txt` | 1,022,706 B |
| `rg_travel_flutter/analyze_output_4.txt` | 1,020,786 B |
| `rg_travel_flutter/analyze_output_5.txt` | 1,016,940 B |
| `rg_travel_flutter/flutter_01.log` | 2,654 B |
| `rg_travel_flutter/flutter_errors.txt` | 521,287 B |
| `rg_travel_flutter/flutter_web_stderr.log` | 0 B |
| `rg_travel_flutter/flutter_web_stdout.log` | 578 B |
| `rg_travel_flutter/run_stderr.log` | 163 B |
| `rg_travel_flutter/run_stdout.log` | 52 B |
| `rg_travel_flutter/run_web_stderr.log` | 0 B |
| `rg_travel_flutter/run_web_stdout.log` | 0 B |
| `test_debug.log` | 6,370 B |
| `test_result.log` | 8,888 B |
