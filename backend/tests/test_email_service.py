"""
Tests for email_service.py's three-tier sending logic (Brevo API -> SMTP
-> dev-mode logging fallback). These mock the network calls entirely — no
real Brevo/SMTP traffic — and restore the real settings after each test so
nothing leaks into the rest of the suite (which relies on the dev-mode
fallback being active for its own caplog-based token extraction).
"""
import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.core.config import settings
from app.services import email_service


@pytest.fixture(autouse=True)
def _reset_email_settings():
    """Every test in this file starts from a clean slate and restores the
    real values afterward — these tests mutate global settings, and this
    is what stops that from bleeding into every other test in the suite."""
    original = (settings.brevo_api_key, settings.brevo_sender_email,
                settings.smtp_host, settings.smtp_username, settings.smtp_password)
    yield
    (settings.brevo_api_key, settings.brevo_sender_email,
     settings.smtp_host, settings.smtp_username, settings.smtp_password) = original


def test_dev_mode_when_nothing_configured(capsys):
    settings.brevo_api_key = ""
    settings.smtp_host = ""
    settings.smtp_username = ""
    settings.smtp_password = ""

    email_service.send_email("someone@example.com", "Test Subject", "Test body")

    captured = capsys.readouterr()
    assert "Test Subject" in captured.out
    assert "Test body" in captured.out
    assert "someone@example.com" in captured.out


def test_brevo_used_when_configured():
    settings.brevo_api_key = "fake-key-123"
    settings.brevo_sender_email = "noreply@example.com"
    settings.smtp_host = ""

    with patch("app.services.email_service.requests.post") as mock_post:
        mock_post.return_value = MagicMock(raise_for_status=MagicMock())
        email_service.send_email("someone@example.com", "Subject", "Body")

    assert mock_post.called
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["api-key"] == "fake-key-123"
    assert kwargs["json"]["sender"] == {"email": "noreply@example.com"}
    assert kwargs["json"]["to"] == [{"email": "someone@example.com"}]
    assert kwargs["json"]["subject"] == "Subject"


def test_brevo_takes_priority_over_smtp_when_both_configured():
    settings.brevo_api_key = "fake-key-123"
    settings.brevo_sender_email = "noreply@example.com"
    settings.smtp_host = "smtp.gmail.com"
    settings.smtp_username = "someone@gmail.com"
    settings.smtp_password = "irrelevant"

    with patch("app.services.email_service.requests.post") as mock_post, \
         patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
        mock_post.return_value = MagicMock(raise_for_status=MagicMock())
        email_service.send_email("someone@example.com", "Subject", "Body")

    assert mock_post.called
    assert not mock_smtp.called


def test_brevo_failure_falls_back_to_dev_mode_without_raising(capsys, caplog):
    settings.brevo_api_key = "fake-key-123"
    settings.brevo_sender_email = "noreply@example.com"
    settings.smtp_host = ""

    with patch("app.services.email_service.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("simulated failure")
        with caplog.at_level(logging.ERROR):
            email_service.send_email("someone@example.com", "Subject", "Body")  # must not raise

    assert "Brevo send failed" in caplog.text
    captured = capsys.readouterr()
    assert "someone@example.com" in captured.out  # dev-mode fallback still ran


def test_smtp_used_when_brevo_not_configured():
    settings.brevo_api_key = ""
    settings.smtp_host = "smtp.gmail.com"
    settings.smtp_username = "someone@gmail.com"
    settings.smtp_password = "app-password"

    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        email_service.send_email("someone@example.com", "Subject", "Body")

    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("someone@gmail.com", "app-password")
    assert mock_server.sendmail.called


def test_smtp_failure_falls_back_to_dev_mode_without_raising(capsys, caplog):
    settings.brevo_api_key = ""
    settings.smtp_host = "smtp.gmail.com"
    settings.smtp_username = "someone@gmail.com"
    settings.smtp_password = "app-password"

    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = OSError("simulated network failure")
        with caplog.at_level(logging.ERROR):
            email_service.send_email("someone@example.com", "Subject", "Body")  # must not raise

    assert "SMTP send failed" in caplog.text
    captured = capsys.readouterr()
    assert "someone@example.com" in captured.out
