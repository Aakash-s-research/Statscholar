"""
Shared SQLAlchemy engine and table definitions — one schema for the whole
app, used by both auth_service.py (users, tokens) and data_service.py
(datasets).

Tables are defined with SQLAlchemy's Core schema API (not raw CREATE
TABLE strings) specifically so the DDL — auto-increment syntax, boolean
types, etc. — is generated correctly for whichever database is actually
in use. Works against SQLite locally (zero setup, matching how this app
has always run) and PostgreSQL in production (set
STATSCHOLAR_DATABASE_URL) with the exact same code.
"""
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)

from app.core.config import settings

_data_dir = Path(__file__).resolve().parent.parent.parent / "data_store"
_data_dir.mkdir(exist_ok=True)

# SQLite needs this flag for a multi-threaded server (FastAPI/uvicorn runs
# request handlers on different threads); Postgres doesn't use or need it,
# so it's only passed when the URL is actually a SQLite one.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)
metadata = MetaData()

users_table = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("password_hash", String, nullable=False),
    Column("created_at", Float, nullable=False),
    Column("is_verified", Boolean, nullable=False, default=False),
    Column("password_changed_at", Float, nullable=False, default=0),
)

email_verification_tokens_table = Table(
    "email_verification_tokens", metadata,
    Column("token", String, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("expires_at", Float, nullable=False),
)

password_reset_tokens_table = Table(
    "password_reset_tokens", metadata,
    Column("token", String, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("expires_at", Float, nullable=False),
    Column("used", Boolean, nullable=False, default=False),
)

# Datasets are stored with their CSV content directly in the database
# (as text) rather than as separate files on disk — this is what actually
# makes them survive on hosting platforms with an ephemeral filesystem
# (the whole reason for this migration). Fine for this app's file-size
# scope (25 MB cap); a much larger-scale version of this app would use
# dedicated object storage (S3/R2) instead of a text column.
datasets_table = Table(
    "datasets", metadata,
    Column("id", String, primary_key=True),
    Column("owner_id", Integer, nullable=False),
    Column("filename", String, nullable=False),
    Column("csv_content", Text, nullable=False),
    Column("created_at", Float, nullable=False),
)

metadata.create_all(engine)
