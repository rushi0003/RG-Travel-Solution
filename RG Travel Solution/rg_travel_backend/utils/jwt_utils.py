from __future__ import annotations

import jwt
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

try:
    from ..config.keys import get_secret_key, get_token_ttl_minutes
except ImportError:
    from config.keys import get_secret_key, get_token_ttl_minutes


def create_jwt(user_id: str, role: str, ttl_minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a JWT signed with HS256. Returns dict with token and expires_at ISO.
    """
    if ttl_minutes is None:
        ttl_minutes = int(get_token_ttl_minutes())

    iat = datetime.utcnow()
    exp = iat + timedelta(minutes=int(ttl_minutes))
    jti = "jwt_" + uuid.uuid4().hex

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
    }

    token = jwt.encode(payload, get_secret_key(), algorithm="HS256")
    # PyJWT returns str in v2+
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return {"token": token, "expires_at": exp.isoformat(), "jti": jti}


def decode_jwt(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT. Raises jwt exceptions on error."""
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=["HS256"])  # raises on error
        return payload
    except Exception:
        raise
