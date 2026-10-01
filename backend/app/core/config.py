"""
Application configuration.

Kept deliberately small for v1 — a single Settings object read from
environment variables, with sane local-dev defaults.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_SQLITE_PATH = Path(__file__).resolve().parent.parent.parent / "data_store" / "statscholar.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STATSCHOLAR_")

    app_name: str = "StatScholar"
    cors_origins: list[str] = [
	"http://localhost:5173",
	"http://127.0.0.1:5173",
	"http://statscholar.onrender.com",
]  # Vite dev server
    max_upload_mb: int = 25
    default_alpha: float = 0.05  # significance threshold used across all test modules

    # A SQLAlchemy connection string. Defaults to a local SQLite file — zero
    # setup for local development, matching how this app has always run.
    # Set STATSCHOLAR_DATABASE_URL to a real Postgres URL (e.g. from Render
    # or Neon) in production — same code, same schema, no code changes
    # needed, since SQLAlchemy abstracts the dialect difference.
    database_url: str = f"sqlite:///{_LOCAL_SQLITE_PATH}"

    # Base URL the frontend is served from — used to build verification and
    # password-reset links that get emailed out (e.g. f"{frontend_base_url}/reset-password?token=...").
    frontend_base_url: str = "http://localhost:5173"

    # SMTP — leave unset to use the dev-mode fallback (email content is
    # logged instead of sent). Set all three (host, username, password) via
    # environment variables (STATSCHOLAR_SMTP_HOST etc.) to send real email.
    #
    # NOTE: Render's free web services block outbound traffic on SMTP ports
    # 25/465/587 (a platform policy since Sept 2025, not fixable via
    # credentials) — SMTP here only works locally or on a paid Render plan.
    # For free-tier deployment, set STATSCHOLAR_BREVO_API_KEY instead (see
    # below) — it sends over HTTPS, which isn't blocked.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    # Brevo (brevo.com) transactional email API — sends over HTTPS, so it
    # works on Render's free tier where SMTP does not. Free forever, 300
    # emails/day, no card required. Takes priority over SMTP when set.
    brevo_api_key: str = ""
    brevo_sender_email: str = ""

    # JWT signing secret. This default is fine for local/single-machine use
    # (nobody else can reach this process to forge a token), but MUST be
    # overridden via STATSCHOLAR_SECRET_KEY before deploying anywhere
    # reachable by other people — anyone who read this source file would
    # otherwise be able to forge a valid session token for any user.
    secret_key: str = "statscholar-dev-secret-change-before-any-real-deployment"


settings = Settings()
