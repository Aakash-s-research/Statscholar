"""
Email sending — for verification links and password resets.

Tries, in order:
  1. Brevo's HTTP API, if STATSCHOLAR_BREVO_API_KEY is set — sends over
     HTTPS, so it works on Render's free tier, where outbound SMTP is
     blocked at the network level (a platform policy since Sept 2025;
     no SMTP credentials, however correct, can get past it there).
  2. SMTP, if STATSCHOLAR_SMTP_HOST/USERNAME/PASSWORD are set — works
     locally, or on a paid Render plan, or any host that doesn't block
     outbound SMTP.
  3. A dev-mode fallback that logs (and prints) the email's content
     instead of sending it — lets the whole verification/reset flow be
     built, tested, and used locally with zero email setup at all.
"""
import logging
import smtplib
from email.mime.text import MIMEText

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

_BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


def is_brevo_configured() -> bool:
    return bool(settings.brevo_api_key)


def is_smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password)


def _send_via_brevo(to_email: str, subject: str, body: str) -> None:
    sender = settings.brevo_sender_email or settings.smtp_username or "no-reply@statscholar.app"
    payload = {
        "sender": {"email": sender},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }
    headers = {"api-key": settings.brevo_api_key, "Content-Type": "application/json"}
    resp = requests.post(_BREVO_SEND_URL, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()  # non-2xx raises — caller decides whether to fall back


def _send_via_smtp(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_username
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(msg["From"], [to_email], msg.as_string())


def send_email(to_email: str, subject: str, body: str) -> None:
    if is_brevo_configured():
        try:
            _send_via_brevo(to_email, subject, body)
            return
        except Exception:
            logger.exception("Brevo send failed for to=%s — falling back to dev-mode logging", to_email)
            # fall through to dev-mode logging below, rather than raising
            # and breaking the signup/reset request that triggered this

    elif is_smtp_configured():
        try:
            _send_via_smtp(to_email, subject, body)
            return
        except Exception:
            logger.exception("SMTP send failed for to=%s — falling back to dev-mode logging", to_email)

    message = (
        f"Email not actually sent (no working email backend configured or send failed). "
        f"Would have sent to={to_email} subject={subject!r}\n--- body ---\n{body}\n--- end body ---"
    )
    # Both a log record (for tests, and for anyone with real logging
    # configured) AND a direct print — Python's default logging level is
    # WARNING, so a plain logger.info() call is silently swallowed in an
    # actual `uvicorn` run unless something has configured logging to show
    # INFO. Since this print is the *only* way to actually get your
    # verification/reset link without a working email backend, it can't
    # depend on logging configuration to be visible.
    logger.info(message)
    print(message)
