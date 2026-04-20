import smtplib
from email.message import EmailMessage
from email.utils import formataddr
import os
import mimetypes
from dotenv import load_dotenv

load_dotenv(override=True)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.default_sender = os.getenv("DEFAULT_SENDER_NAME", "Shuttle One")

    def _validate_config(self):
        """Validate SMTP configuration before attempting to send."""
        if not self.username:
            return False, "SMTP_USERNAME is missing in .env configuration"
        if not self.password:
            return False, "SMTP_PASSWORD is missing in .env configuration"
        if not self.smtp_server:
            return False, "SMTP_SERVER is missing in .env configuration"
        return True, "OK"

    def send_to_multiple(self, subject, body, recipients, attachments=None):
        """
        Sends emails to multiple recipients with optional attachments.
        Returns (success: bool, message: str).
        """
        valid, msg = self._validate_config()
        if not valid:
            return False, msg

        if not recipients:
            return False, "No recipients provided"

        success_count = 0
        failure_count = 0
        errors = []

        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.login(self.username, self.password)
                
                for recipient in recipients:
                    try:
                        msg = EmailMessage()
                        
                        # Set HTML content for proper formatting, with plain text fallback
                        html_body = body.replace('\n', '<br>')
                        msg.set_content(body)  # Plain text fallback
                        msg.add_alternative(f"""
                        <html>
                            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                                    {html_body}
                                </div>
                            </body>
                        </html>
                        """, subtype='html')
                        
                        msg["Subject"] = subject
                        msg["From"] = formataddr((self.default_sender, self.username))
                        msg["To"] = recipient
                        
                        if attachments:
                            for filename, content, content_type in attachments:
                                if not content_type:
                                    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                                maintype, subtype = content_type.split('/', 1)
                                msg.add_attachment(
                                    content,
                                    maintype=maintype,
                                    subtype=subtype,
                                    filename=filename
                                )
                        
                        server.send_message(msg)
                        success_count += 1
                        
                    except smtplib.SMTPResponseException as e:
                        failure_count += 1
                        err_msg = str(e.smtp_error.decode()) if hasattr(e.smtp_error, 'decode') else str(e)
                        if e.smtp_code == 552:
                            return False, "Message too large for Gmail limits (Error 552). Please reduce attachment sizes."
                        errors.append(f"{recipient}: {err_msg}")
                    except Exception as e:
                        failure_count += 1
                        errors.append(f"{recipient}: {str(e)}")
                        
            if failure_count == 0:
                return True, f"Successfully sent to all {success_count} recipient(s)."
            else:
                summary = f"Sent to {success_count}, failed for {failure_count} recipient(s)."
                if errors:
                    summary += f" Errors: {'; '.join(errors[:3])}"
                    if len(errors) > 3:
                        summary += f" ...and {len(errors) - 3} more"
                return success_count > 0, summary

        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed. Check your username and app password in .env"
        except smtplib.SMTPConnectError:
            return False, f"Could not connect to SMTP server {self.smtp_server}:{self.smtp_port}"
        except TimeoutError:
            return False, "SMTP connection timed out. Check your internet connection and SMTP settings."
        except Exception as e:
            print(f"SMTP Critical Error: {e}")
            return False, f"SMTP connection failed: {str(e)}"

email_service = EmailService()
