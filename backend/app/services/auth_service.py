"""
Authentication — user accounts, password hashing, JWT session tokens, and
one-time tokens for email verification / password reset.

Backed by SQLAlchemy against whatever database core/config.py points to
(SQLite locally, Postgres in production) — see core/db.py for the table
definitions. Passwords are hashed with bcrypt directly (not via passlib,
which has a known incompatibility with recent bcrypt versions). Session
tokens are signed JWTs; verification/reset tokens are random strings
stored with an expiry, since they need to be single-use and revocable in
a way a stateless JWT isn't.
"""
import secrets
import time
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.db import email_verification_tokens_table, engine, password_reset_tokens_table, users_table

_ALGORITHM = "HS256"
_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

_VERIFICATION_TOKEN_TTL_SECONDS = 60 * 60 * 24  # 24 hours
_RESET_TOKEN_TTL_SECONDS = 60 * 60  # 1 hour


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class InvalidToken(Exception):
    pass


def register_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = time.time()

    try:
        with engine.begin() as conn:
            result = conn.execute(
                insert(users_table).values(
                    email=email, password_hash=password_hash, created_at=now,
                    is_verified=False, password_changed_at=now,
                )
            )
            user_id = result.inserted_primary_key[0]
        return {"id": user_id, "email": email, "is_verified": False}
    except IntegrityError:
        raise EmailAlreadyRegistered(f"An account with email '{email}' already exists")


def authenticate_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    with engine.connect() as conn:
        row = conn.execute(
            select(users_table.c.id, users_table.c.email, users_table.c.password_hash, users_table.c.is_verified)
            .where(users_table.c.email == email)
        ).fetchone()

    if row is None:
        raise InvalidCredentials("Incorrect email or password")
    user_id, user_email, password_hash, is_verified = row
    if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        raise InvalidCredentials("Incorrect email or password")
    return {"id": user_id, "email": user_email, "is_verified": bool(is_verified)}


def _get_password_changed_at(user_id: int) -> Optional[float]:
    with engine.connect() as conn:
        row = conn.execute(
            select(users_table.c.password_changed_at).where(users_table.c.id == user_id)
        ).fetchone()
    return row[0] if row else None


def create_access_token(user_id: int) -> str:
    pwd_ts = _get_password_changed_at(user_id) or 0
    payload = {"sub": str(user_id), "pwd_ts": pwd_ts, "exp": time.time() + _TOKEN_TTL_SECONDS}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Returns {"user_id": int, "pwd_ts": float}. `pwd_ts` is the
    password_changed_at value at the moment this token was issued — pass
    it to `token_still_valid` to check whether the password has since
    changed (which should invalidate the token even though it hasn't
    expired yet)."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        return {"user_id": int(payload["sub"]), "pwd_ts": payload.get("pwd_ts", 0)}
    except jwt.PyJWTError:
        raise InvalidToken("Invalid or expired token")


def token_still_valid(user_id: int, token_pwd_ts: float) -> bool:
    """False if the password has been changed since this token was issued
    — this is what makes a password reset actually invalidate any other
    logged-in session, rather than just changing the password while every
    existing JWT (stateless by nature) keeps working until it expires on
    its own, up to 7 days later."""
    current = _get_password_changed_at(user_id)
    if current is None:
        return False
    return abs(current - token_pwd_ts) < 0.001


def get_user_by_id(user_id: int) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            select(users_table.c.id, users_table.c.email, users_table.c.is_verified)
            .where(users_table.c.id == user_id)
        ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "is_verified": bool(row[2])}


def get_user_by_email(email: str) -> Optional[dict]:
    email = email.strip().lower()
    with engine.connect() as conn:
        row = conn.execute(
            select(users_table.c.id, users_table.c.email, users_table.c.is_verified)
            .where(users_table.c.email == email)
        ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "is_verified": bool(row[2])}


def list_users() -> list[dict]:
    """Never selects password_hash — this is deliberately the only shape
    this function can return, so a future caller can't accidentally leak
    hashes just by forgetting to strip a field."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(users_table.c.id, users_table.c.email, users_table.c.created_at, users_table.c.is_verified)
            .order_by(users_table.c.created_at)
        ).fetchall()
    return [{"id": r[0], "email": r[1], "created_at": r[2], "is_verified": bool(r[3])} for r in rows]


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

def create_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            insert(email_verification_tokens_table).values(
                token=token, user_id=user_id, expires_at=time.time() + _VERIFICATION_TOKEN_TTL_SECONDS,
            )
        )
    return token


def verify_email_token(token: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            select(email_verification_tokens_table.c.user_id, email_verification_tokens_table.c.expires_at)
            .where(email_verification_tokens_table.c.token == token)
        ).fetchone()
        if row is None:
            raise InvalidToken("Invalid verification link")
        user_id, expires_at = row
        if time.time() > expires_at:
            raise InvalidToken("This verification link has expired")

        conn.execute(update(users_table).where(users_table.c.id == user_id).values(is_verified=True))
        conn.execute(delete(email_verification_tokens_table).where(email_verification_tokens_table.c.token == token))

        user_row = conn.execute(
            select(users_table.c.id, users_table.c.email).where(users_table.c.id == user_id)
        ).fetchone()
    return {"id": user_row[0], "email": user_row[1], "is_verified": True}


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def create_password_reset_token(email: str) -> Optional[str]:
    """Returns None if no account has this email — callers should still
    report success to the caller either way, to avoid leaking which emails
    are registered (a classic account-enumeration issue)."""
    user = get_user_by_email(email)
    if user is None:
        return None

    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            insert(password_reset_tokens_table).values(
                token=token, user_id=user["id"], expires_at=time.time() + _RESET_TOKEN_TTL_SECONDS, used=False,
            )
        )
    return token


def reset_password(token: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters")

    with engine.begin() as conn:
        row = conn.execute(
            select(
                password_reset_tokens_table.c.user_id,
                password_reset_tokens_table.c.expires_at,
                password_reset_tokens_table.c.used,
            ).where(password_reset_tokens_table.c.token == token)
        ).fetchone()
        if row is None:
            raise InvalidToken("Invalid reset link")
        user_id, expires_at, used = row
        if used:
            raise InvalidToken("This reset link has already been used")
        if time.time() > expires_at:
            raise InvalidToken("This reset link has expired")

        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn.execute(
            update(users_table).where(users_table.c.id == user_id)
            .values(password_hash=password_hash, password_changed_at=time.time())
        )
        conn.execute(
            update(password_reset_tokens_table).where(password_reset_tokens_table.c.token == token).values(used=True)
        )
