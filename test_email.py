import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def test_email(to_email):
    print(f"Testing email to {to_email} from {EMAIL_USER}...")
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "AIVA Email Test"
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg.attach(MIMEText("This is a test email from AIVA.", 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        
        print("SUCCESS: Email sent!")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    # Test with a dummy email or let the user know
    test_email("yashranpariya32@gmail.com") # Sending to self to test
