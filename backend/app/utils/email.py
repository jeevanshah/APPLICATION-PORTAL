"""
Email utility functions for sending notifications.
Supports both Azure Communication Services and SMTP.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(
    email: str,
    token: str,
    user_name: str
) -> bool:
    """
    Send password reset email with token.
    
    Args:
        email: Recipient email address
        token: Password reset token
        user_name: User's name for personalization
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Construct reset link
    # In production, this should be the frontend URL
    reset_link = f"http://localhost:3000/reset-password?token={token}"
    
    # Email content
    subject = f"{settings.APP_NAME} - Password Reset Request"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background: #ffffff;
                padding: 30px;
                border: 1px solid #e0e0e0;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 20px 0;
                font-weight: 600;
            }}
            .footer {{
                background: #f5f5f5;
                padding: 20px;
                text-align: center;
                border-radius: 0 0 8px 8px;
                font-size: 14px;
                color: #666;
            }}
            .warning {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello {user_name},</p>
            
            <p>We received a request to reset your password for your {settings.APP_NAME} account.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <div style="text-align: center;">
                <a href="{reset_link}" class="button">Reset Password</a>
            </div>
            
            <p>Or copy and paste this link into your browser:</p>
            <p style="background: #f5f5f5; padding: 10px; border-radius: 4px; word-break: break-all;">
                {reset_link}
            </p>
            
            <div class="warning">
                <strong>⚠️ Important:</strong>
                <ul>
                    <li>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes</li>
                    <li>If you didn't request this reset, please ignore this email</li>
                    <li>Your password won't change until you click the link and set a new one</li>
                </ul>
            </div>
            
            <p>If you have any questions, please contact our support team.</p>
            
            <p>Best regards,<br>
            <strong>{settings.APP_NAME} Team</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
            <p>&copy; 2025 {settings.APP_NAME}. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    Password Reset Request
    
    Hello {user_name},
    
    We received a request to reset your password for your {settings.APP_NAME} account.
    
    Click the link below to reset your password:
    {reset_link}
    
    This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
    
    If you didn't request this reset, please ignore this email. Your password won't change until you click the link and set a new one.
    
    Best regards,
    {settings.APP_NAME} Team
    """
    
    try:
        # Try Azure Communication Services first if configured
        if settings.AZURE_COMMUNICATION_CONNECTION_STRING:
            return send_email_azure(email, subject, html_body, text_body)
        # Fallback to SMTP if configured
        elif settings.SMTP_HOST:
            return send_email_smtp(email, subject, html_body, text_body)
        else:
            # No email service configured - log to console for development
            logger.warning("No email service configured. Logging reset link to console.")
            logger.info(f"Password reset link for {email}: {reset_link}")
            logger.info(f"Reset token: {token}")
            print(f"\n{'='*80}")
            print(f"PASSWORD RESET EMAIL")
            print(f"{'='*80}")
            print(f"To: {email}")
            print(f"Subject: {subject}")
            print(f"Reset Link: {reset_link}")
            print(f"Token (for testing): {token}")
            print(f"{'='*80}\n")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        raise


def send_email_azure(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str
) -> bool:
    """
    Send email using Azure Communication Services.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_body: HTML content
        text_body: Plain text content
    
    Returns:
        True if sent successfully
    """
    try:
        from azure.communication.email import EmailClient
        
        client = EmailClient.from_connection_string(
            settings.AZURE_COMMUNICATION_CONNECTION_STRING
        )
        
        message = {
            "senderAddress": settings.EMAILS_FROM_EMAIL,
            "recipients": {
                "to": [{"address": to_email}]
            },
            "content": {
                "subject": subject,
                "plainText": text_body,
                "html": html_body
            }
        }
        
        poller = client.begin_send(message)
        result = poller.result()
        
        logger.info(f"Email sent successfully to {to_email} via Azure. Message ID: {result.message_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email via Azure: {e}")
        raise


def send_email_smtp(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str
) -> bool:
    """
    Send email using SMTP.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_body: HTML content
        text_body: Plain text content
    
    Returns:
        True if sent successfully
    """
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg['To'] = to_email
        
        # Attach parts
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email} via SMTP")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {e}")
        raise


def send_application_status_email(
    to_email: str,
    applicant_name: str,
    application_id: str,
    new_status: str,
    message: Optional[str] = None
) -> bool:
    """
    Send application status update notification.
    
    Args:
        to_email: Applicant email
        applicant_name: Applicant's name
        application_id: Application ID
        new_status: New application status
        message: Optional custom message
    
    Returns:
        True if sent successfully
    """
    subject = f"{settings.APP_NAME} - Application Status Update"
    
    status_emoji = {
        "SUBMITTED": "📝",
        "STAFF_REVIEW": "👀",
        "AWAITING_DOCUMENTS": "📄",
        "GS_ASSESSMENT": "🔍",
        "OFFER_GENERATED": "🎉",
        "OFFER_ACCEPTED": "✅",
        "ENROLLED": "🎓",
        "REJECTED": "❌",
        "WITHDRAWN": "🚫"
    }.get(new_status, "📋")
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>{status_emoji} Application Status Update</h2>
        <p>Hello {applicant_name},</p>
        <p>Your application (ID: <strong>{application_id}</strong>) status has been updated to:</p>
        <div style="background: #f0f4ff; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
            <h3 style="margin: 0;">{new_status.replace('_', ' ').title()}</h3>
        </div>
        {f'<p>{message}</p>' if message else ''}
        <p>You can view your application details by logging into your account.</p>
        <p>Best regards,<br>{settings.APP_NAME} Team</p>
    </body>
    </html>
    """
    
    text_body = f"""
    Application Status Update
    
    Hello {applicant_name},
    
    Your application (ID: {application_id}) status has been updated to: {new_status.replace('_', ' ').title()}
    
    {message if message else ''}
    
    You can view your application details by logging into your account.
    
    Best regards,
    {settings.APP_NAME} Team
    """
    
    try:
        if settings.AZURE_COMMUNICATION_CONNECTION_STRING:
            return send_email_azure(to_email, subject, html_body, text_body)
        elif settings.SMTP_HOST:
            return send_email_smtp(to_email, subject, html_body, text_body)
        else:
            logger.info(f"Application status email for {to_email}: {new_status}")
            print(f"Status Update Email: {to_email} -> {new_status}")
            return True
    except Exception as e:
        logger.error(f"Failed to send status email: {e}")
        return False
