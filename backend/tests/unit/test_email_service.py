"""Tests for email_service — SMTP email sending."""

from unittest.mock import MagicMock, patch

import pytest  # noqa: F401

from app.services.email_service import build_email, send_email


class TestBuildEmail:
    def test_builds_multipart_alternative(self):
        msg = build_email(
            to_email="user@example.com",
            subject="Test Subject",
            html_body="<h1>Hello</h1>",
            text_body="Hello",
        )
        assert msg["To"] == "user@example.com"
        assert msg["Subject"] == "Test Subject"
        assert msg.get_content_type() == "multipart/alternative"

    def test_includes_from_header(self):
        msg = build_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hi</p>",
            text_body="Hi",
            from_email="sender@example.com",
            from_name="Stock Tracer",
        )
        assert "Stock Tracer" in msg["From"]
        assert "sender@example.com" in msg["From"]

    def test_contains_html_and_text_parts(self):
        msg = build_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="TEXT",
        )
        payloads = msg.get_payload()
        assert len(payloads) == 2
        assert payloads[0].get_content_type() == "text/plain"
        assert payloads[1].get_content_type() == "text/html"


class TestSendEmail:
    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_email_calls_smtp(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        ctx = mock_smtp_cls.return_value
        ctx.__enter__ = MagicMock(return_value=mock_smtp)
        ctx.__exit__ = MagicMock(return_value=False)

        msg = build_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hi</p>",
            text_body="Hi",
        )
        send_email(
            msg,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="app-password",
        )

        mock_smtp.starttls.assert_called_once()
        user, pwd = "sender@gmail.com", "app-password"
        mock_smtp.login.assert_called_once_with(user, pwd)
        mock_smtp.send_message.assert_called_once_with(msg)
