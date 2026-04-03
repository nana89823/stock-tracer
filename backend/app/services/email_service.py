"""Email sending service using SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def build_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str = "",
    from_name: str = "Stock Tracer",
) -> MIMEMultipart:
    """Build a multipart email with HTML and plaintext."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to_email
    msg["From"] = f"{from_name} <{from_email}>" if from_email else from_name

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_email(
    msg: MIMEMultipart,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
) -> None:
    """Send an email via SMTP with STARTTLS."""
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    logger.info("Email sent to %s", msg["To"])
