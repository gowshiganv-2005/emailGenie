import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    email = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    server = "smtp.gmail.com"
    port = 465

    if not email or not password:
        print("FAILED: SMTP_USERNAME or SMTP_PASSWORD not set in .env")
        return

    print(f"Testing SMTP for: {email}")
    print(f"Password length: {len(password)} (Should be 16)")

    try:
        with smtplib.SMTP_SSL(server, port, timeout=10) as smtp:
            smtp.login(email, password)
            print("SUCCESS: Credentials are correct!")
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_connection()
