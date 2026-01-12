import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from src.config import get_settings

settings = get_settings()


class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str):
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    @staticmethod
    async def send_verification_email(to_email: str, otp_code: str):
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4F46E5; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background-color: #f9fafb; }
                .otp-box { background-color: white; border: 2px dashed #4F46E5; padding: 20px; text-align: center; margin: 20px 0; }
                .otp-code { font-size: 32px; font-weight: bold; color: #4F46E5; letter-spacing: 5px; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ app_name }}</h1>
                </div>
                <div class="content">
                    <h2>Verify Your Email</h2>
                    <p>Thank you for registering! Please use the following OTP to verify your email address:</p>
                    <div class="otp-box">
                        <div class="otp-code">{{ otp_code }}</div>
                    </div>
                    <p>This OTP will expire in {{ expire_minutes }} minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        html_content = html_template.render(
            app_name=settings.APP_NAME,
            otp_code=otp_code,
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )
        
        await EmailService.send_email(
            to_email,
            f"Verify Your Email - {settings.APP_NAME}",
            html_content
        )

    @staticmethod
    async def send_password_reset_email(to_email: str, otp_code: str):
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #DC2626; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px 20px; background-color: #f9fafb; }
                .otp-box { background-color: white; border: 2px dashed #DC2626; padding: 20px; text-align: center; margin: 20px 0; }
                .otp-code { font-size: 32px; font-weight: bold; color: #DC2626; letter-spacing: 5px; }
                .warning { background-color: #FEF3C7; border-left: 4px solid #F59E0B; padding: 15px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ app_name }}</h1>
                </div>
                <div class="content">
                    <h2>Reset Your Password</h2>
                    <p>We received a request to reset your password. Use the following OTP to proceed:</p>
                    <div class="otp-box">
                        <div class="otp-code">{{ otp_code }}</div>
                    </div>
                    <p>This OTP will expire in {{ expire_minutes }} minutes.</p>
                    <div class="warning">
                        <strong>Security Alert:</strong> If you didn't request this password reset, please ignore this email and ensure your account is secure.
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2024 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        html_content = html_template.render(
            app_name=settings.APP_NAME,
            otp_code=otp_code,
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )
        
        await EmailService.send_email(
            to_email,
            f"Reset Your Password - {settings.APP_NAME}",
            html_content
        )