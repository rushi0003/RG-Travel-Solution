# backend/db/__init__.py
"""
RG Travel Solution - DB Package (SQLite)

✅ Path: backend/db/__init__.py
✅ Structure: backend/db/

This module provides:
1) get_db()                     -> sqlite connection with foreign_keys ON
2) init_db()                    -> creates tables from backend/db/schema.sql
3) reset_db()                   -> drops all tables (dev only) then init_db()
4) register_db_routes(app)      -> optional API endpoints for DB health/init/reset

✅ Optional API endpoints (if you register routes):
- GET  /api/db/health
- POST /api/db/init
- POST /api/db/reset          (DANGER, dev only)
- GET  /api/db/tables

Important:
- Your seeds create tables if missing, but init_db() is the clean way.
- Uses schema file: backend/db/schema.sql (NOT schema.sqly)

Works with your existing pattern:
- You already use get_db() in many modules.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, request, jsonify, current_app
from db.schema_guard import ensure_group_flow_schema

# ---------------------------
# Config / paths
# ---------------------------
DEFAULT_DB_FILENAME = "rg_travel.db"


def _project_root() -> str:
    """
    Returns backend/ folder absolute path.
    This file is backend/db/__init__.py -> backend = parent of db folder.
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _default_db_path() -> str:
    """
    Default DB path: backend/rg_travel.db
    """
    return os.path.join(_project_root(), DEFAULT_DB_FILENAME)


def _schema_path() -> str:
    """
    Schema path: backend/db/schema.sql
    """
    return os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db_path() -> str:
    """
    Priority:
    1) Flask app config: DATABASE
    2) Env var: RG_DB_PATH
    3) default: backend/rg_travel.db
    """
    try:
        cfg = current_app.config.get("DATABASE")  # type: ignore
        if cfg:
            return str(cfg)
    except Exception:
        pass

    env = os.getenv("RG_DB_PATH")
    if env:
        return env

    return _default_db_path()


# ---------------------------
# Connection
# ---------------------------
def get_db() -> sqlite3.Connection:
    """
    Returns sqlite3 connection:
    - row_factory = sqlite3.Row (so dict(row) works)
    - foreign_keys ON
    """
    db_path = get_db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # IMPORTANT: enforce FK constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ---------------------------
# Schema / init
# ---------------------------
def _read_schema_sql() -> str:
    path = _schema_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Schema file not found at: {path}. "
            f"Expected backend/db/schema.sql"
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def init_db() -> Dict[str, Any]:
    """
    Creates tables by executing backend/db/schema.sql
    """
    schema_sql = _read_schema_sql()

    conn = get_db()
    try:
        conn.executescript(schema_sql)
        ensure_group_flow_schema(conn)
        conn.commit()
    finally:
        conn.close()

    return {"db_path": get_db_path(), "initialized": True}


def list_tables() -> List[str]:
    """
    Returns list of user tables.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        rows = cur.fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def reset_db() -> Dict[str, Any]:
    """
    DANGER (dev only):
    Drops all user tables then re-runs schema.sql
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            """
        )
        tables = [r["name"] for r in cur.fetchall()]

        for t in tables:
            cur.execute(f'DROP TABLE IF EXISTS "{t}"')

        conn.commit()
    finally:
        conn.close()

    # re-init
    init_db()
    return {"db_path": get_db_path(), "reset": True, "dropped_tables": tables}


def db_health() -> Dict[str, Any]:
    """
    Checks DB is reachable and foreign_keys are enabled.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys;")
        fk = cur.fetchone()[0]
        cur.execute("SELECT 1;")
        _ = cur.fetchone()
    finally:
        conn.close()

    return {
        "db_path": get_db_path(),
        "ok": True,
        "foreign_keys": int(fk),
    }


# ---------------------------
# Optional DB API endpoints
# ---------------------------
db_bp = Blueprint("db", __name__, url_prefix="/api/db")


def _success(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _error(message="Error", status=400, code="ERROR", data=None):
    return jsonify({"success": False, "message": message, "error": {"code": code}, "data": data}), status


@db_bp.route("/health", methods=["GET"])
def api_health():
    try:
        return _success(db_health(), "DB healthy")
    except Exception as e:
        return _error(str(e), 500, "DB_ERROR")


@db_bp.route("/tables", methods=["GET"])
def api_tables():
    try:
        return _success({"tables": list_tables()}, "OK")
    except Exception as e:
        return _error(str(e), 500, "DB_ERROR")


@db_bp.route("/init", methods=["POST"])
def api_init():
    """
    Initializes schema (safe to call multiple times).
    """
    try:
        res = init_db()
        return _success(res, "DB initialized")
    except FileNotFoundError as fe:
        return _error(str(fe), 404, "SCHEMA_NOT_FOUND")
    except Exception as e:
        return _error(str(e), 500, "DB_INIT_FAILED")


@db_bp.route("/reset", methods=["POST"])
def api_reset():
    """
    DANGER (dev): drops all tables and re-creates schema.
    You can protect this with an env flag if needed.
    """
    try:
        allow = os.getenv("RG_ALLOW_DB_RESET", "0") == "1"
        if not allow:
            return _error(
                "DB reset is disabled. Set RG_ALLOW_DB_RESET=1 to enable.",
                403,
                "RESET_DISABLED",
            )
        res = reset_db()
        return _success(res, "DB reset complete")
    except FileNotFoundError as fe:
        return _error(str(fe), 404, "SCHEMA_NOT_FOUND")
    except Exception as e:
        return _error(str(e), 500, "DB_RESET_FAILED")


def register_db_routes(app: Any) -> None:
    """
    Register /api/db endpoints from app.py:

        from db import register_db_routes
        register_db_routes(app)
    """
    app.register_blueprint(db_bp)


__all__ = [
    "get_db",
    "get_db_path",
    "init_db",
    "reset_db",
    "list_tables",
    "db_health",
    "register_db_routes",
]
