from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import requests

try:
    from db import get_db
except Exception:  # pragma: no cover - import fallback for scripts/tests
    get_db = None  # type: ignore


NOMINATIM_BASE_URL = str(os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")).strip().rstrip("/")
NOMINATIM_TIMEOUT_SEC = float(os.getenv("NOMINATIM_TIMEOUT_SEC", "6"))
NOMINATIM_USER_AGENT = str(
    os.getenv("NOMINATIM_USER_AGENT", "rg-travel-solution/1.0 (ops@rg-travel.local)")
).strip()
NOMINATIM_COUNTRY_CODES = str(os.getenv("NOMINATIM_COUNTRY_CODES", "in")).strip()
NOMINATIM_FALLBACK_REGION = str(os.getenv("NOMINATIM_FALLBACK_REGION", "Maharashtra, India")).strip()
NOMINATIM_FALLBACK_DISTRICT = str(os.getenv("NOMINATIM_FALLBACK_DISTRICT", "Pune, Maharashtra, India")).strip()


def _normalize_address_key(address: str) -> str:
    text = re.sub(r"\s+", " ", str(address or "").strip().lower())
    # keep commas but remove duplicate punctuation spacing
    text = re.sub(r"\s*,\s*", ", ", text)
    return text


def _normalize_locality_for_query(address: str) -> str:
    q = str(address or "").strip()
    q = re.sub(r"\bjunner\b", "junnar", q, flags=re.IGNORECASE)
    q = re.sub(r"\s*,\s*", ", ", q)
    return q


def ensure_geocode_cache_table(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS geocode_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address_key TEXT NOT NULL UNIQUE,
            original_address TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            provider TEXT NOT NULL DEFAULT 'nominatim',
            raw_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_geocode_cache_address_key ON geocode_cache(address_key)")


def _cached_geocode(conn: Any, address_key: str) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT lat, lng, original_address, provider, raw_json, updated_at
        FROM geocode_cache
        WHERE address_key = ?
        LIMIT 1
        """,
        (address_key,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "lat": float(row[0]),
        "lng": float(row[1]),
        "display_name": str(row[2] or ""),
        "provider": str(row[3] or "nominatim"),
        "updated_at": str(row[5] or ""),
        "raw_json": row[4],
        "from_cache": True,
    }


def _upsert_cache(conn: Any, address_key: str, address: str, lat: float, lng: float, raw_json: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO geocode_cache
        (address_key, original_address, lat, lng, provider, raw_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'nominatim', ?, ?, ?)
        ON CONFLICT(address_key) DO UPDATE SET
            original_address = excluded.original_address,
            lat = excluded.lat,
            lng = excluded.lng,
            provider = excluded.provider,
            raw_json = excluded.raw_json,
            updated_at = excluded.updated_at
        """,
        (address_key, address, lat, lng, json.dumps(raw_json, ensure_ascii=True), now, now),
    )


def geocode_address_nominatim(
    address: str,
    *,
    conn: Any = None,
    use_cache: bool = True,
    country_codes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Geocode address text using OpenStreetMap Nominatim.
    Step-1 foundation API for flow:
    Address text -> Geocoding -> lat/lng save -> Group create.
    """
    clean = str(address or "").strip()
    if not clean:
        return {"success": False, "message": "Address is required"}

    address_key = _normalize_address_key(clean)
    owns_conn = False
    db_conn = conn

    try:
        if db_conn is None and get_db is not None:
            db_conn = get_db()
            owns_conn = True

        if db_conn is not None:
            ensure_geocode_cache_table(db_conn)
            if use_cache:
                hit = _cached_geocode(db_conn, address_key)
                if hit:
                    return {"success": True, "data": hit}

        headers = {
            "User-Agent": NOMINATIM_USER_AGENT,
            "Accept": "application/json",
        }
        cc = str(country_codes if country_codes is not None else NOMINATIM_COUNTRY_CODES).strip()
        fallback_region = NOMINATIM_FALLBACK_REGION
        fallback_district = NOMINATIM_FALLBACK_DISTRICT
        normalized = _normalize_locality_for_query(clean)
        queries = [clean, normalized]
        if fallback_region:
            queries.append(f"{clean}, {fallback_region}")
            queries.append(f"{normalized}, {fallback_region}")
        if fallback_district:
            queries.append(f"{clean}, {fallback_district}")
            queries.append(f"{normalized}, {fallback_district}")
        if "india" not in clean.lower():
            queries.append(f"{clean}, India")
            queries.append(f"{normalized}, India")

        # de-duplicate while preserving order
        seen = set()
        deduped_queries = []
        for q in queries:
            key = q.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped_queries.append(q)

        top = None
        url = f"{NOMINATIM_BASE_URL}/search"
        for q in deduped_queries:
            params = {
                "q": q,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
            }
            if cc:
                params["countrycodes"] = cc
            resp = requests.get(url, params=params, headers=headers, timeout=NOMINATIM_TIMEOUT_SEC)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                top = data[0]
                break
        if top is None:
            return {"success": False, "message": "No geocode result found", "provider": "nominatim"}

        lat = float(top.get("lat"))
        lng = float(top.get("lon"))
        result = {
            "lat": lat,
            "lng": lng,
            "display_name": str(top.get("display_name") or clean),
            "provider": "nominatim",
            "from_cache": False,
            "raw_json": top,
        }

        if db_conn is not None:
            _upsert_cache(db_conn, address_key, clean, lat, lng, top)
            db_conn.commit()

        return {"success": True, "data": result}
    except Exception as exc:
        return {"success": False, "message": f"Nominatim geocode failed: {exc}", "provider": "nominatim"}
    finally:
        if owns_conn and db_conn is not None:
            try:
                db_conn.close()
            except Exception:
                pass


def probe_nominatim_provider(timeout_sec: float = 2.0) -> Dict[str, Any]:
    """
    Runtime probe for geocoding readiness.
    Uses a short known query and reports diagnostic payload.
    """
    sample_query = str(os.getenv("NOMINATIM_PROBE_QUERY", "Mumbai, India")).strip() or "Mumbai, India"
    try:
        headers = {"User-Agent": NOMINATIM_USER_AGENT, "Accept": "application/json"}
        params = {"q": sample_query, "format": "jsonv2", "limit": 1}
        cc = str(NOMINATIM_COUNTRY_CODES or "").strip()
        if cc:
            params["countrycodes"] = cc
        url = f"{NOMINATIM_BASE_URL}/search"
        resp = requests.get(url, params=params, headers=headers, timeout=float(timeout_sec))
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            top = data[0]
            return {
                "ready": True,
                "provider": "nominatim",
                "base_url": NOMINATIM_BASE_URL,
                "query": sample_query,
                "sample_lat": float(top.get("lat")),
                "sample_lng": float(top.get("lon")),
                "timeout_sec": float(timeout_sec),
            }
        return {
            "ready": False,
            "provider": "nominatim",
            "base_url": NOMINATIM_BASE_URL,
            "query": sample_query,
            "timeout_sec": float(timeout_sec),
            "error": "Empty geocode response",
        }
    except Exception as exc:
        return {
            "ready": False,
            "provider": "nominatim",
            "base_url": NOMINATIM_BASE_URL,
            "query": sample_query,
            "timeout_sec": float(timeout_sec),
            "error": str(exc),
        }
