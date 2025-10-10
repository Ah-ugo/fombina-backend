import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
FROM_NAME = os.getenv("FROM_NAME", "Fombina Tower")


async def send_email(to_email: str, subject: str, html_content: str, text_content: str = None):
    """
    Send email via SMTP

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text fallback (optional)

    Returns:
        dict: Send result
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        message["To"] = to_email

        # Add text and HTML parts
        if text_content:
            part1 = MIMEText(text_content, "plain")
            message.attach(part1)

        part2 = MIMEText(html_content, "html")
        message.attach(part2)

        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)

        return {"success": True, "message": "Email sent successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_booking_confirmation(booking_data: dict):
    """Send booking confirmation email"""
    subject = f"Booking Confirmation - {booking_data['space_name']}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); color: white; padding: 30px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .details {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #d4a574; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #d4a574; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Booking Confirmed!</h1>
                <p>Thank you for choosing Fombina Tower</p>
            </div>
            <div class="content">
                <p>Dear {booking_data['name']},</p>
                <p>Your booking has been confirmed. Here are your booking details:</p>

                <div class="details">
                    <h3>Booking Details</h3>
                    <p><strong>Space:</strong> {booking_data['space_name']}</p>
                    <p><strong>Booking ID:</strong> {booking_data['booking_id']}</p>
                    <p><strong>Amount:</strong> ₦{booking_data['amount']:,}</p>
                    <p><strong>Email:</strong> {booking_data['email']}</p>
                    <p><strong>Phone:</strong> {booking_data['phone']}</p>
                </div>

                <p>Our team will contact you within 24 hours to finalize the details.</p>

                <center>
                    <a href="https://fombinatower.vercel.app/booking/{booking_data['booking_id']}" class="button">View Booking</a>
                </center>
            </div>
            <div class="footer">
                <p>© 2025 Fombina Tower. All rights reserved.</p>
                <p>Plot 1839, Kur Muhd Avenue, CBD, FCT Abuja, Nigeria</p>
                <p>Phone: 09028132452, 08163686368</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(booking_data['email'], subject, html_content)


async def send_contact_notification(contact_data: dict):
    """Send contact form notification to admin"""
    subject = f"New Contact Form Submission - {contact_data['name']}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>New Contact Form Submission</h2>
            <div style="background: #f9f9f9; padding: 20px; margin: 20px 0;">
                <p><strong>Name:</strong> {contact_data['name']}</p>
                <p><strong>Email:</strong> {contact_data['email']}</p>
                <p><strong>Phone:</strong> {contact_data.get('phone', 'N/A')}</p>
                <p><strong>Subject:</strong> {contact_data.get('subject', 'N/A')}</p>
                <p><strong>Message:</strong></p>
                <p>{contact_data['message']}</p>
            </div>
        </div>
    </body>
    </html>
    """

    admin_email = os.getenv("ADMIN_EMAIL", "admin@fombinatower.com")
    return await send_email(admin_email, subject, html_content)


async def send_welcome_email(user_data: dict):
    """Send welcome email to new user"""
    subject = "Welcome to Fombina Tower"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); color: white; padding: 40px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #d4a574; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Fombina Tower</h1>
                <p>Where Luxury Meets Excellence</p>
            </div>
            <div class="content">
                <p>Dear {user_data['name']},</p>
                <p>Thank you for joining Fombina Tower. We're excited to have you as part of our exclusive community.</p>
                <p>Your account has been successfully created. You can now:</p>
                <ul>
                    <li>Browse available premium office and retail spaces</li>
                    <li>Book spaces with secure online payments</li>
                    <li>Track your bookings and transactions</li>
                    <li>Stay updated on construction progress</li>
                </ul>
                <center>
                    <a href="https://fombinatower.vercel.app/spaces" class="button">Explore Spaces</a>
                </center>
                <p>If you have any questions, feel free to contact our team.</p>
            </div>
            <div class="footer">
                <p>© 2025 Fombina Tower. All rights reserved.</p>
                <p>Plot 1839, Kur Muhd Avenue, CBD, FCT Abuja, Nigeria</p>
                <p>Phone: 09028132452, 08163686368</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(user_data['email'], subject, html_content)


async def send_password_reset_email(user_data: dict):
    """Send password reset email"""
    subject = "Reset Your Fombina Tower Password"

    reset_url = f"https://fombinatower.vercel.app/reset-password?token={user_data['reset_token']}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); color: white; padding: 40px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #d4a574; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Dear {user_data['name']},</p>
                <p>We received a request to reset your password for your Fombina Tower account.</p>
                <p>Click the button below to reset your password:</p>
                <center>
                    <a href="{reset_url}" class="button">Reset Password</a>
                </center>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <div class="warning">
                    <strong>Security Notice:</strong> This link will expire in 1 hour. If you didn't request this password reset, please ignore this email or contact support if you have concerns.
                </div>
            </div>
            <div class="footer">
                <p>© 2025 Fombina Tower. All rights reserved.</p>
                <p>Plot 1839, Kur Muhd Avenue, CBD, FCT Abuja, Nigeria</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(user_data['email'], subject, html_content)


async def send_application_confirmation(application_data: dict):
    """Send application confirmation email"""
    subject = "Application Received - Fombina Tower"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); color: white; padding: 40px; text-align: center; }}
            .content {{ background: #f9f9f9; padding: 30px; }}
            .details {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #d4a574; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .highlight {{ background: #d4a574; color: white; padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Application Received!</h1>
                <p>Thank you for your interest in Fombina Tower</p>
            </div>
            <div class="content">
                <p>Dear {application_data['name']},</p>
                <p>We have successfully received your application for a premium space at Fombina Tower.</p>

                <div class="details">
                    <h3>Application Summary</h3>
                    <p><strong>Application ID:</strong> {application_data['application_id']}</p>
                    <p><strong>Preferred Floor Level:</strong> {application_data['floor_level']}</p>
                    <p><strong>Payment Mode:</strong> {application_data['payment_mode']}</p>
                    <p><strong>Space Size:</strong> 49 Square Meters</p>
                    <p><strong>Total Price:</strong> ₦360,000,000</p>
                    <p><strong>Initial Deposit (40%):</strong> ₦144,000,000</p>
                </div>

                <div class="highlight">
                    <h3 style="margin: 0;">Next Steps</h3>
                </div>

                <ol>
                    <li><strong>Application Fee Payment:</strong> Pay the non-refundable application fee of ₦100,000</li>
                    <li><strong>Document Verification:</strong> Our team will review your submitted documents</li>
                    <li><strong>Letter of Offer:</strong> You will receive a Letter of Offer within 3-5 business days</li>
                    <li><strong>Initial Deposit:</strong> Pay the 40% initial deposit as per the Letter of Offer</li>
                    <li><strong>Letter of Allocation:</strong> Receive your Letter of Allocation after full payment</li>
                </ol>

                <p><strong>Important:</strong> Please ensure you have the following documents ready:</p>
                <ul>
                    <li>Valid means of identification (as specified in your application)</li>
                    <li>Recent passport photographs (applicant and next of kin)</li>
                    <li>Proof of source of funds</li>
                </ul>

                <p>Our team will contact you within 24-48 hours via email or phone to guide you through the next steps.</p>

                <div style="background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Contact Us:</strong></p>
                    <p style="margin: 5px 0;">📍 Plot 1839, Kur Muhd Avenue, CBD, FCT Abuja</p>
                    <p style="margin: 5px 0;">📞 09028132452, 08163686368</p>
                    <p style="margin: 5px 0;">✉️ info@fombinatower.com</p>
                </div>
            </div>
            <div class="footer">
                <p><strong>Developed by:</strong> Eagle Track Local Content LTD</p>
                <p><strong>Marketed by:</strong> Uloaku Ekwuribe & Partners</p>
                <p style="margin-top: 15px;">© 2025 Fombina Tower. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(application_data['email'], subject, html_content)
