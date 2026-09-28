"""
Email sending — for verification links and password resets.

Sends real email via SMTP when credentials are configured (see
core/config.py: SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD). Without them,
falls back to logging the email's content instead of sending it — this
lets the whole verification/reset flow be built, tested, and used locally
without needing a real mailbox connected. Swap in real SMTP credentials
(e.g. a Gmail account with an app password) whenever you're ready.
"""
import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password)


def send_email(to_email: str, subject: str, body: str) -> None:
    if not is_smtp_configured():
        message = (
            f"SMTP not configured — email not actually sent. "
            f"Would have sent to={to_email} subject={subject!r}\n--- body ---\n{body}\n--- end body ---"
        )
        # Both a log record (for tests, and for anyone with real logging
        # configured) AND a direct print — Python's default logging level
        # is WARNING, so a plain logger.info() call is silently swallowed
        # in an actual `uvicorn` run unless something has configured
        # logging to show INFO. Since this print is the *only* way to
        # actually get your verification/reset link without real SMTP
        # set up, it can't depend on logging configuration to be visible.
        logger.info(message)
        print(message)
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_username
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(msg["From"], [to_email], msg.as_string())
