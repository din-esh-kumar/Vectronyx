import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.supabase_client import supabase

router = APIRouter()

_SCRYPT_PREFIX = "scrypt$"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64

_RATE_LIMIT_WINDOW_SECONDS = 60.0
_RATE_LIMIT_MAX_ATTEMPTS = 15
_auth_attempts: Dict[str, Deque[float]] = defaultdict(deque)


def hash_password(raw_password: str) -> str:
    """Derive a salted scrypt password hash."""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        raw_password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"{_SCRYPT_PREFIX}{salt.hex()}${derived.hex()}"


def verify_password(raw_password: str, stored_value: str) -> tuple[bool, bool]:
    """
    Verify a password in constant time.
    Returns (is_valid, needs_rehash).
    """
    if not stored_value:
        return False, False
    if stored_value.startswith(_SCRYPT_PREFIX):
        parts = stored_value.split("$")
        if len(parts) != 3:
            return False, False
        try:
            salt = bytes.fromhex(parts[1])
            expected = bytes.fromhex(parts[2])
        except ValueError:
            return False, False
        derived = hashlib.scrypt(
            raw_password.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=len(expected),
        )
        return hmac.compare_digest(derived, expected), False
    # Legacy unhashed record compatibility: constant-time compare + flag for immediate rehash
    matched = hmac.compare_digest(raw_password.encode("utf-8"), stored_value.encode("utf-8"))
    return matched, matched


def _enforce_rate_limit(request: Request) -> None:
    client_host = (request.client.host if request.client else None) or "unknown"
    now = time.monotonic()
    bucket = _auth_attempts[client_host]
    while bucket and (now - bucket[0]) > _RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please try again shortly.",
        )
    bucket.append(now)


class SignupUser(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)


class LoginUser(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


@router.post("/signup")
def signup(user: SignupUser, request: Request):
    _enforce_rate_limit(request)
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase client is not configured.")

    normalized_email = user.email.strip().lower()
    if "@" not in normalized_email or "." not in normalized_email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Valid email address is required.")

    existing = supabase.table("users").select("id").eq("email", normalized_email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    supabase.table("users").insert({
        "name": user.name.strip(),
        "email": normalized_email,
        "password": hash_password(user.password),
    }).execute()

    return {"message": "User created successfully"}


@router.post("/login")
def login(user: LoginUser, request: Request):
    _enforce_rate_limit(request)
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase client is not configured.")

    normalized_email = user.email.strip().lower()
    res = supabase.table("users").select("id, email, name, password").eq("email", normalized_email).execute()

    if not res.data:
        # Constant-time dummy work to reduce timing side-channel for email enumeration
        hashlib.scrypt(
            user.password.encode("utf-8"),
            salt=b"vectronyx-timing",
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_SCRYPT_DKLEN,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    raw_user = res.data[0]
    if not isinstance(raw_user, dict):
        raise HTTPException(status_code=500, detail="Invalid user record returned from database.")

    stored_password = str(raw_user.get("password") or "")
    is_valid, needs_rehash = verify_password(user.password, stored_password)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if needs_rehash and raw_user.get("id") is not None:
        try:
            supabase.table("users").update(
                {"password": hash_password(user.password)}
            ).eq("id", raw_user["id"]).execute()
        except Exception:
            pass

    return {
        "message": "Login successful",
        "user": {
            "email": raw_user.get("email"),
            "name": raw_user.get("name"),
        },
    }
