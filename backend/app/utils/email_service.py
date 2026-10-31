"""Email service — real SMTP with a file-based dev-mode fallback."""
import os
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import config


def _dev_mode_send(subject: str, recipient: str, body: str) -> dict:
    """Write the email to a local JSON file instead of sending it."""
    outbox_dir = Path(__file__).parent.parent.parent / "dev_outbox"
    outbox_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = outbox_dir / f"{ts}_{recipient.replace('@','_at_')}.json"
    payload = {
        "to": recipient,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "mode": "dev",
    }
    filename.write_text(json.dumps(payload, indent=2))
    return {"status": "dev_mode", "file": str(filename)}


def send_email(recipient: str, subject: str, body: str) -> dict:
    """
    Send an email.  If MAIL_DEV_MODE=true (default for hackathon demo) the
    message is written to dev_outbox/ and never actually sent.
    """
    if config.MAIL_DEV_MODE:
        return _dev_mode_send(subject, recipient, body)

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.MAIL_DEFAULT_SENDER
        msg["To"] = recipient
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT) as server:
            if config.MAIL_USE_TLS:
                server.starttls()
            if config.MAIL_USERNAME:
                server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
            server.sendmail(config.MAIL_DEFAULT_SENDER, [recipient], msg.as_string())
        return {"status": "sent"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def send_password_reset(recipient: str, reset_token: str, frontend_url: str = None) -> dict:
    url = f"{frontend_url or config.FRONTEND_URL}/reset-password?token={reset_token}"
    subject = "SubscriptIQ — Password Reset"
    body = f"""
    <h2>Password Reset Request</h2>
    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
    <a href="{url}">{url}</a>
    <p>If you did not request this, please ignore this email.</p>
    """
    return send_email(recipient, subject, body)


def send_invoice_reminder(recipient: str, customer_name: str, invoice_number: str,
                          outstanding: str, due_date: str) -> dict:
    subject = f"Payment Reminder — Invoice {invoice_number}"
    body = f"""
    <h2>Payment Reminder</h2>
    <p>Dear {customer_name},</p>
    <p>Invoice <strong>{invoice_number}</strong> with an outstanding amount of
    <strong>₹{outstanding}</strong> was due on <strong>{due_date}</strong>.</p>
    <p>Please make the payment at your earliest convenience.</p>
    <p>— SubscriptIQ by Brightloop Software</p>
    """
    return send_email(recipient, subject, body)


def send_renewal_reminder(recipient: str, customer_name: str, subscription_number: str,
                          renewal_date: str, amount: str) -> dict:
    subject = f"Subscription Renewal Reminder — {subscription_number}"
    body = f"""
    <h2>Subscription Renewal</h2>
    <p>Dear {customer_name},</p>
    <p>Your subscription <strong>{subscription_number}</strong> renews on
    <strong>{renewal_date}</strong> for <strong>₹{amount}</strong>.</p>
    <p>— SubscriptIQ by Brightloop Software</p>
    """
    return send_email(recipient, subject, body)
