import smtplib
import os
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email(to_email, subject, html_content, text_content=None):
    """
    Send an email using SMTP from environment configuration

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text version of the email

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        # Get SMTP configuration from environment
        smtp_host = os.getenv('MAIL_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_PORT', 465))
        smtp_username = os.getenv('MAIL_USERNAME', '')
        smtp_password = os.getenv('MAIL_PASSWORD', '')
        from_email = os.getenv('MAIL_FROM_ADDRESS', smtp_username)
        from_name = os.getenv('MAIL_FROM_NAME', 'Service Connect Support')
        encryption = os.getenv('MAIL_ENCRYPTION', 'ssl')

        # Validate configuration
        if not smtp_username or not smtp_password:
            return {
                'success': False,
                'message': 'Email configuration is missing. Please check environment variables.'
            }

        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f'{from_name} <{from_email}>'
        message['To'] = to_email

        # Add plain text version (fallback)
        if text_content:
            part1 = MIMEText(text_content, 'plain')
            message.attach(part1)

        # Add HTML version
        part2 = MIMEText(html_content, 'html')
        message.attach(part2)

        # Send email based on encryption type
        if encryption.lower() == 'ssl':
            # Use SSL (port 465)
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_username, smtp_password)
                server.sendmail(from_email, to_email, message.as_string())
        else:
            # Use TLS/STARTTLS (port 587)
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(from_email, to_email, message.as_string())

        return {
            'success': True,
            'message': f'Email sent successfully to {to_email}'
        }

    except smtplib.SMTPAuthenticationError:
        return {
            'success': False,
            'message': 'SMTP authentication failed. Please check email credentials.'
        }
    except smtplib.SMTPException as e:
        return {
            'success': False,
            'message': f'SMTP error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send email: {str(e)}'
        }


def send_user_verification_email(user_email, user_name):
    """
    Send verification approval email to a user

    Args:
        user_email (str): User's email address
        user_name (str): User's full name

    Returns:
        dict: {'success': bool, 'message': str}
    """
    subject = "Welcome to Service Connect - Your Account is Verified!"

    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                padding: 30px 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px 20px;
                border-left: 1px solid #ddd;
                border-right: 1px solid #ddd;
            }}
            .footer {{
                background-color: #333;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                border-radius: 0 0 5px 5px;
            }}
            .button {{
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .highlight {{
                background-color: #fff;
                padding: 15px;
                border-left: 4px solid #4CAF50;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 Account Verified!</h1>
        </div>
        <div class="content">
            <p>Dear {user_name},</p>

            <p>Great news! Your Service Connect account has been successfully verified and approved by our team.</p>

            <div class="highlight">
                <p><strong>You can now:</strong></p>
                <ul>
                    <li>Browse and search for service providers</li>
                    <li>Book services from verified providers</li>
                    <li>Manage your bookings and appointments</li>
                    <li>Rate and review service providers</li>
                    <li>Contact providers directly through our platform</li>
                </ul>
            </div>

            <p>Your account is now active and you can log in using your registered email address.</p>

            <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>

            <p>Welcome to the Service Connect community!</p>

            <p>Best regards,<br>
            <strong>The Service Connect Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Service Connect. All rights reserved.</p>
            <p>This is an automated message, please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Dear {user_name},

    Great news! Your Service Connect account has been successfully verified and approved by our team.

    You can now:
    - Browse and search for service providers
    - Book services from verified providers
    - Manage your bookings and appointments
    - Rate and review service providers
    - Contact providers directly through our platform

    Your account is now active and you can log in using your registered email address.

    If you have any questions or need assistance, please don't hesitate to contact our support team.

    Welcome to the Service Connect community!

    Best regards,
    The Service Connect Team

    © {datetime.now().year} Service Connect. All rights reserved.
    This is an automated message, please do not reply to this email.
    """

    return send_email(user_email, subject, html_content, text_content)


def send_provider_verification_email(provider_email, provider_name, business_name=None):
    """
    Send verification approval email to a service provider

    Args:
        provider_email (str): Provider's email address
        provider_name (str): Provider's full name
        business_name (str, optional): Provider's business name

    Returns:
        dict: {'success': bool, 'message': str}
    """
    subject = "Congratulations! Your Service Provider Account is Verified"

    business_display = business_name if business_name else provider_name

    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2196F3;
                color: white;
                padding: 30px 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px 20px;
                border-left: 1px solid #ddd;
                border-right: 1px solid #ddd;
            }}
            .footer {{
                background-color: #333;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                border-radius: 0 0 5px 5px;
            }}
            .highlight {{
                background-color: #fff;
                padding: 15px;
                border-left: 4px solid #2196F3;
                margin: 20px 0;
            }}
            .success-badge {{
                background-color: #4CAF50;
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                display: inline-block;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 Provider Account Verified!</h1>
            <div class="success-badge">✓ Verified Provider</div>
        </div>
        <div class="content">
            <p>Dear {provider_name},</p>

            <p>Congratulations! Your service provider account for <strong>{business_display}</strong> has been successfully verified and approved by our team.</p>

            <div class="highlight">
                <p><strong>You can now start offering your services:</strong></p>
                <ul>
                    <li>Create and manage your service listings</li>
                    <li>Set your availability and schedules</li>
                    <li>Receive booking requests from customers</li>
                    <li>Manage appointments and bookings</li>
                    <li>Communicate with customers directly</li>
                    <li>Build your reputation with customer reviews</li>
                    <li>Track your earnings and sales reports</li>
                </ul>
            </div>

            <p><strong>Next Steps:</strong></p>
            <ol>
                <li>Log in to your provider account</li>
                <li>Complete your business profile</li>
                <li>Add your services and set pricing</li>
                <li>Upload service photos (recommended)</li>
                <li>Set your availability schedule</li>
                <li>Start accepting bookings!</li>
            </ol>

            <p>Your verified badge will be displayed on your profile, helping customers trust and choose your services.</p>

            <p>If you need any assistance getting started or have questions about managing your provider account, our support team is here to help.</p>

            <p>We're excited to have you as part of the Service Connect provider community!</p>

            <p>Best regards,<br>
            <strong>The Service Connect Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Service Connect. All rights reserved.</p>
            <p>This is an automated message, please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Dear {provider_name},

    Congratulations! Your service provider account for {business_display} has been successfully verified and approved by our team.

    You can now start offering your services:
    - Create and manage your service listings
    - Set your availability and schedules
    - Receive booking requests from customers
    - Manage appointments and bookings
    - Communicate with customers directly
    - Build your reputation with customer reviews
    - Track your earnings and sales reports

    Next Steps:
    1. Log in to your provider account
    2. Complete your business profile
    3. Add your services and set pricing
    4. Upload service photos (recommended)
    5. Set your availability schedule
    6. Start accepting bookings!

    Your verified badge will be displayed on your profile, helping customers trust and choose your services.

    If you need any assistance getting started or have questions about managing your provider account, our support team is here to help.

    We're excited to have you as part of the Service Connect provider community!

    Best regards,
    The Service Connect Team

    © {datetime.now().year} Service Connect. All rights reserved.
    This is an automated message, please do not reply to this email.
    """

    return send_email(provider_email, subject, html_content, text_content)


def send_account_status_change_email(email, name, new_status, account_type='user', business_name=None):
    """
    Send account status change notification email

    Args:
        email (str): Account email address
        name (str): Account holder's full name
        new_status (str): New status (active, inactive, suspended)
        account_type (str): 'user' or 'provider'
        business_name (str, optional): Business name for providers

    Returns:
        dict: {'success': bool, 'message': str}
    """
    is_provider = account_type == 'provider'
    business_display = business_name if business_name else name

    # Configure email based on status
    if new_status == 'suspended':
        subject = "Important: Your Service Connect Account Has Been Suspended"
        header_color = "#f44336"  # Red
        icon = "⚠️"
        title = "Account Suspended"

        if is_provider:
            message = f"Your service provider account for <strong>{business_display}</strong> has been suspended by our administration team."
            reason = """
            <p><strong>What this means:</strong></p>
            <ul>
                <li>Your account is temporarily suspended</li>
                <li>You cannot access provider features</li>
                <li>Your services are hidden from customers</li>
                <li>Existing bookings may be affected</li>
            </ul>
            """
        else:
            message = "Your Service Connect user account has been suspended by our administration team."
            reason = """
            <p><strong>What this means:</strong></p>
            <ul>
                <li>Your account is temporarily suspended</li>
                <li>You cannot log in to your account</li>
                <li>You cannot book services or access platform features</li>
                <li>Existing bookings may be affected</li>
            </ul>
            """

        action = """
        <p><strong>What to do:</strong></p>
        <p>If you believe this is an error or would like to appeal this decision, please contact our support team at
        <a href="mailto:serviceconnectassistdesk@gmail.com">serviceconnectassistdesk@gmail.com</a> with your account details.</p>
        """

    elif new_status == 'inactive':
        subject = "Your Service Connect Account Has Been Deactivated"
        header_color = "#FF9800"  # Orange
        icon = "ℹ️"
        title = "Account Deactivated"

        if is_provider:
            message = f"Your service provider account for <strong>{business_display}</strong> has been deactivated."
            reason = """
            <p><strong>What this means:</strong></p>
            <ul>
                <li>Your account is currently inactive</li>
                <li>You cannot log in to your provider account</li>
                <li>Your services are not visible to customers</li>
                <li>You will not receive new booking requests</li>
            </ul>
            """
        else:
            message = "Your Service Connect user account has been deactivated."
            reason = """
            <p><strong>What this means:</strong></p>
            <ul>
                <li>Your account is currently inactive</li>
                <li>You cannot log in to your account</li>
                <li>You cannot access platform features</li>
            </ul>
            """

        action = """
        <p><strong>Need to reactivate?</strong></p>
        <p>If you would like to reactivate your account, please contact our support team at
        <a href="mailto:serviceconnectassistdesk@gmail.com">serviceconnectassistdesk@gmail.com</a> with your account details.</p>
        """

    elif new_status == 'active':
        subject = "Your Service Connect Account Has Been Activated"
        header_color = "#4CAF50"  # Green
        icon = "✅"
        title = "Account Activated"

        if is_provider:
            message = f"Great news! Your service provider account for <strong>{business_display}</strong> has been reactivated."
            reason = """
            <p><strong>You can now:</strong></p>
            <ul>
                <li>Log in to your provider account</li>
                <li>Manage your services and listings</li>
                <li>Accept new booking requests</li>
                <li>Communicate with customers</li>
                <li>Access all provider features</li>
            </ul>
            """
        else:
            message = "Great news! Your Service Connect user account has been reactivated."
            reason = """
            <p><strong>You can now:</strong></p>
            <ul>
                <li>Log in to your account</li>
                <li>Browse and book services</li>
                <li>Manage your bookings</li>
                <li>Access all platform features</li>
            </ul>
            """

        action = """
        <p>Welcome back to Service Connect! You can now log in and use all platform features.</p>
        """

    else:
        # Default for unknown status
        return {'success': False, 'message': f'Unknown status: {new_status}'}

    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: {header_color};
                color: white;
                padding: 30px 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px 20px;
                border-left: 1px solid #ddd;
                border-right: 1px solid #ddd;
            }}
            .footer {{
                background-color: #333;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                border-radius: 0 0 5px 5px;
            }}
            .highlight {{
                background-color: #fff;
                padding: 15px;
                border-left: 4px solid {header_color};
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{icon} {title}</h1>
        </div>
        <div class="content">
            <p>Dear {name},</p>

            <p>{message}</p>

            <div class="highlight">
                {reason}
            </div>

            {action}

            <p>If you have any questions, please don't hesitate to contact our support team at
            <a href="mailto:serviceconnectassistdesk@gmail.com">serviceconnectassistdesk@gmail.com</a>.</p>

            <p>Best regards,<br>
            <strong>The Service Connect Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Service Connect. All rights reserved.</p>
            <p>This is an automated message, please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Dear {name},

    {title}

    {message.replace('<strong>', '').replace('</strong>', '')}

    Status: {new_status.upper()}

    If you have any questions, please contact our support team at serviceconnectassistdesk@gmail.com.

    Best regards,
    The Service Connect Team

    © {datetime.now().year} Service Connect. All rights reserved.
    This is an automated message, please do not reply to this email.
    """

    return send_email(email, subject, html_content, text_content)


def send_account_rejection_email(email, name, account_type='user', business_name=None, reason=None):
    """
    Send account rejection/denial notification email

    Args:
        email (str): Account email address
        name (str): Account holder's full name
        account_type (str): 'user' or 'provider'
        business_name (str, optional): Business name for providers
        reason (str, optional): Reason for rejection

    Returns:
        dict: {'success': bool, 'message': str}
    """
    is_provider = account_type == 'provider'
    business_display = business_name if business_name else name

    subject = "Service Connect Account Application - Update"
    header_color = "#f44336"  # Red
    icon = "❌"
    title = "Account Application Denied"

    if is_provider:
        message = f"We regret to inform you that your service provider application for <strong>{business_display}</strong> has not been approved at this time."
        details = """
        <p><strong>What this means:</strong></p>
        <ul>
            <li>Your provider account application was not approved</li>
            <li>You will not be able to offer services on our platform</li>
            <li>Your account has been set to inactive status</li>
        </ul>
        """
    else:
        message = "We regret to inform you that your user account application has not been approved at this time."
        details = """
        <p><strong>What this means:</strong></p>
        <ul>
            <li>Your user account application was not approved</li>
            <li>You will not be able to access the platform</li>
            <li>Your account has been set to inactive status</li>
        </ul>
        """

    # Add reason if provided
    reason_section = ""
    if reason:
        reason_section = f"""
        <div class="highlight">
            <p><strong>Reason:</strong></p>
            <p>{reason}</p>
        </div>
        """

    action = """
    <p><strong>What you can do:</strong></p>
    <ul>
        <li>Review your application details and ensure all information was accurate</li>
        <li>Check that all required documents were properly submitted</li>
        <li>You may reapply by creating a new account with complete and accurate information</li>
        <li>Contact our support team if you believe this decision was made in error</li>
    </ul>

    <p>If you have questions or would like more information about this decision, please contact our support team at
    <a href="mailto:serviceconnectassistdesk@gmail.com">serviceconnectassistdesk@gmail.com</a>.</p>
    """

    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: {header_color};
                color: white;
                padding: 30px 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px 20px;
                border-left: 1px solid #ddd;
                border-right: 1px solid #ddd;
            }}
            .footer {{
                background-color: #333;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                border-radius: 0 0 5px 5px;
            }}
            .highlight {{
                background-color: #fff;
                padding: 15px;
                border-left: 4px solid {header_color};
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{icon} {title}</h1>
        </div>
        <div class="content">
            <p>Dear {name},</p>

            <p>{message}</p>

            <div class="highlight">
                {details}
            </div>

            {reason_section}

            {action}

            <p>Thank you for your interest in Service Connect.</p>

            <p>Best regards,<br>
            <strong>The Service Connect Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Service Connect. All rights reserved.</p>
            <p>This is an automated message, please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Dear {name},

    {title}

    {message.replace('<strong>', '').replace('</strong>', '')}

    What this means:
    - Your account application was not approved
    - Your account has been set to inactive status
    - You will not be able to access the platform

    {f'Reason: {reason}' if reason else ''}

    What you can do:
    - Review your application details and ensure all information was accurate
    - Check that all required documents were properly submitted
    - You may reapply by creating a new account with complete and accurate information
    - Contact our support team if you believe this decision was made in error

    If you have questions, please contact our support team at serviceconnectassistdesk@gmail.com.

    Thank you for your interest in Service Connect.

    Best regards,
    The Service Connect Team

    © {datetime.now().year} Service Connect. All rights reserved.
    This is an automated message, please do not reply to this email.
    """

    return send_email(email, subject, html_content, text_content)


def generate_otp(length=6):
    """
    Generate a random OTP code

    Args:
        length (int): Length of the OTP code (default 6)

    Returns:
        str: Generated OTP code
    """
    return ''.join(random.choices(string.digits, k=length))


def send_password_reset_otp_email(email, name, otp_code, account_type='user'):
    """
    Send password reset OTP email

    Args:
        email (str): Account email address
        name (str): Account holder's full name
        otp_code (str): OTP code for password reset
        account_type (str): 'user' or 'provider'

    Returns:
        dict: {'success': bool, 'message': str}
    """
    subject = "Password Reset Request - Service Connect"

    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #FF9800;
                color: white;
                padding: 30px 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px 20px;
                border-left: 1px solid #ddd;
                border-right: 1px solid #ddd;
            }}
            .footer {{
                background-color: #333;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                border-radius: 0 0 5px 5px;
            }}
            .otp-box {{
                background-color: #fff;
                padding: 20px;
                border: 2px dashed #FF9800;
                border-radius: 5px;
                text-align: center;
                margin: 20px 0;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: bold;
                color: #FF9800;
                letter-spacing: 5px;
                font-family: 'Courier New', monospace;
            }}
            .warning {{
                background-color: #fff3cd;
                padding: 15px;
                border-left: 4px solid #ffc107;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Dear {name},</p>

            <p>We received a request to reset the password for your Service Connect {account_type} account.</p>

            <div class="otp-box">
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">Your One-Time Password (OTP)</p>
                <div class="otp-code">{otp_code}</div>
                <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">This code will expire in 15 minutes</p>
            </div>

            <p><strong>How to reset your password:</strong></p>
            <ol>
                <li>Enter the OTP code above in the password reset form</li>
                <li>Create a new password for your account</li>
                <li>Confirm your new password</li>
            </ol>

            <div class="warning">
                <p><strong>⚠️ Security Notice:</strong></p>
                <ul style="margin: 5px 0;">
                    <li>Do not share this OTP with anyone</li>
                    <li>Service Connect staff will never ask for your OTP</li>
                    <li>This OTP is valid for 15 minutes only</li>
                </ul>
            </div>

            <p>If you did not request a password reset, please ignore this email or contact our support team immediately if you suspect unauthorized access to your account.</p>

            <p>Best regards,<br>
            <strong>The Service Connect Team</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Service Connect. All rights reserved.</p>
            <p>This is an automated message, please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
    Dear {name},

    Password Reset Request

    We received a request to reset the password for your Service Connect {account_type} account.

    Your One-Time Password (OTP): {otp_code}

    This code will expire in 15 minutes.

    How to reset your password:
    1. Enter the OTP code above in the password reset form
    2. Create a new password for your account
    3. Confirm your new password

    Security Notice:
    - Do not share this OTP with anyone
    - Service Connect staff will never ask for your OTP
    - This OTP is valid for 15 minutes only

    If you did not request a password reset, please ignore this email or contact our support team immediately if you suspect unauthorized access to your account.

    Best regards,
    The Service Connect Team

    © {datetime.now().year} Service Connect. All rights reserved.
    This is an automated message, please do not reply to this email.
    """

    return send_email(email, subject, html_content, text_content)


def send_booking_status_update_email(user_email, user_name, provider_name, service_title, booking_date, booking_time, old_status, new_status, booking_id):
    """
    Send booking status update notification email to user

    Args:
        user_email (str): User's email address
        user_name (str): User's full name
        provider_name (str): Provider's full name or business name
        service_title (str): Title of the service booked
        booking_date (str): Booking date (formatted)
        booking_time (str): Booking time (formatted)
        old_status (str): Previous booking status
        new_status (str): New booking status
        booking_id (int): Booking ID

    Returns:
        dict: {'success': bool, 'message': str}
    """
    # Configure email based on new status
    if new_status == 'Confirmed':
        subject = "Booking Confirmed - Service Connect"
        header_color = "#4CAF50"  # Green
        icon = "Confirmed"
        title = "Booking Confirmed!"
        message = f"Great news! Your booking with {provider_name} has been confirmed."
        booking_id_label = booking_id
    elif new_status == 'Completed':
        subject = "Service Completed - Service Connect"
        header_color = "#2196F3"  # Blue
        icon = "Completed"
        title = "Service Completed"
        message = f"Your service with {provider_name} has been marked as completed."
        booking_id_label = booking_id
    elif new_status == 'Cancelled':
        subject = "Booking Cancelled - Service Connect"
        header_color = "#f44336"  # Red
        icon = "Cancelled"
        title = "Booking Cancelled"
        message = f"Your booking with {provider_name} has been cancelled."
        booking_id_label = booking_id
    else:
        subject = "Booking Update - Service Connect"
        header_color = "#FF9800"  # Orange
        icon = "Updated"
        title = "Booking Updated"
        message = f"Your booking with {provider_name} has been updated."
        booking_id_label = booking_id

    # HTML email template
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {header_color}; color: white; padding: 30px 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 30px 20px; border-left: 1px solid #ddd; border-right: 1px solid #ddd; }}
        .footer {{ background-color: #333; color: white; padding: 20px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px; }}
        .highlight {{ background-color: #fff; padding: 15px; border-left: 4px solid {header_color}; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header"><h1>{title}</h1></div>
    <div class="content">
        <p>Dear {user_name},</p>
        <p>{message}</p>
        <div class="highlight">
            <p><strong>Booking Details:</strong></p>
            <ul>
                <li><strong>Service:</strong> {service_title}</li>
                <li><strong>Provider:</strong> {provider_name}</li>
                <li><strong>Date:</strong> {booking_date}</li>
                <li><strong>Time:</strong> {booking_time}</li>
                <li><strong>Booking ID:</strong> #{booking_id_label}</li>
                <li><strong>Status:</strong> {new_status}</li>
            </ul>
        </div>
        <p>If you have any questions or concerns, please don't hesitate to contact our support team at <a href="mailto:serviceconnectassistdesk@gmail.com">serviceconnectassistdesk@gmail.com</a>.</p>
        <p>Thank you for using Service Connect!</p>
        <p>Best regards,<br><strong>The Service Connect Team</strong></p>
    </div>
    <div class="footer">
        <p>&copy; {datetime.now().year} Service Connect. All rights reserved.</p>
        <p>This is an automated message, please do not reply to this email.</p>
    </div>
</body>
</html>"""

    # Plain text version
    text_content = f"""Dear {user_name},

{title}

{message}

Booking Details:
- Service: {service_title}
- Provider: {provider_name}
- Date: {booking_date}
- Time: {booking_time}
- Booking ID: #{booking_id_label}
- Status: {new_status}

If you have any questions or concerns, please contact our support team at serviceconnectassistdesk@gmail.com.

Thank you for using Service Connect!

Best regards,
The Service Connect Team

© {datetime.now().year} Service Connect. All rights reserved.
This is an automated message, please do not reply to this email."""

    return send_email(user_email, subject, html_content, text_content)
