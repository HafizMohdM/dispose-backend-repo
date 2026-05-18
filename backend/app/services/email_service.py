"""
Email Service for sending notification emails via SMTP.
Provides HTML-templated transactional emails.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_USE_TLS,
)

logger = logging.getLogger(__name__)


def build_notification_html(title: str, message: str, severity: str, category: str) -> str:
    """Build a branded HTML email template for notification delivery."""
    severity_colors = {
        "CRITICAL": "#EF4444",
        "WARNING": "#F59E0B",
        "SUCCESS": "#10B981",
        "INFO": "#3B82F6",
    }
    color = severity_colors.get(severity, "#3B82F6")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#f4f4f7; font-family:'Segoe UI', Tahoma, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7; padding:40px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #0f172a, #1e293b); padding:24px 32px;">
                                <h1 style="margin:0; color:#ffffff; font-size:20px; font-weight:600;">
                                    🔔 Dispose Platform
                                </h1>
                            </td>
                        </tr>
                        <!-- Severity Badge -->
                        <tr>
                            <td style="padding:24px 32px 0;">
                                <span style="display:inline-block; background-color:{color}; color:#ffffff; padding:4px 12px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:0.5px; text-transform:uppercase;">
                                    {severity} • {category}
                                </span>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding:16px 32px 32px;">
                                <h2 style="margin:0 0 12px; color:#1e293b; font-size:18px; font-weight:600;">
                                    {title}
                                </h2>
                                <p style="margin:0; color:#475569; font-size:14px; line-height:1.6;">
                                    {message}
                                </p>
                            </td>
                        </tr>
                        <!-- CTA -->
                        <tr>
                            <td style="padding:0 32px 32px;">
                                <a href="#" style="display:inline-block; background-color:#3B82F6; color:#ffffff; padding:10px 24px; border-radius:6px; text-decoration:none; font-size:14px; font-weight:600;">
                                    View in Dashboard →
                                </a>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color:#f8fafc; padding:16px 32px; border-top:1px solid #e2e8f0;">
                                <p style="margin:0; color:#94a3b8; font-size:12px;">
                                    You're receiving this because you have email notifications enabled.
                                    <br>Manage preferences in your Dispose dashboard settings.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def send_notification_email(
    to_email: str,
    title: str,
    message: str,
    severity: str = "INFO",
    category: str = "SYSTEM",
) -> dict:
    """
    Send a notification email via SMTP.
    Returns dict with status and any error details.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Skipping email delivery.")
        return {
            "success": False,
            "error": "SMTP credentials not configured",
            "provider": "SMTP",
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Dispose] {title}"
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Plain text fallback
        plain_text = f"{title}\n\n{message}\n\nSeverity: {severity} | Category: {category}"
        msg.attach(MIMEText(plain_text, "plain"))

        # HTML version
        html_content = build_notification_html(title, message, severity, category)
        msg.attach(MIMEText(html_content, "html"))

        # Connect and send
        if SMTP_USE_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)

        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.quit()

        logger.info(f"Email notification sent to {to_email}: {title}")
        return {
            "success": True,
            "provider": "SMTP",
        }

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
        return {"success": False, "error": f"SMTP Authentication failed: {str(e)}", "provider": "SMTP"}
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        return {"success": False, "error": f"SMTP error: {str(e)}", "provider": "SMTP"}
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        return {"success": False, "error": str(e), "provider": "SMTP"}
