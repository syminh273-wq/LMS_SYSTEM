import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')
django.setup()

from django.conf import settings
from core.notification.services.notification_service import NotificationService
from core.notification.enums.notification_provider import NotificationProvider

def send_test_email(recipient=None):
    """
    Script to test the Email Notification Service.
    Usage: python scripts/test_email.py [recipient_email]
    """
    if not recipient:
        recipient = "hosyminh11820004@gmail.com"
        if not recipient:
            print("Error: No recipient provided and EMAIL_HOST_USER is empty in settings.")
            return

    print(f"Initializing NotificationService with provider: EMAIL")
    service = NotificationService(NotificationProvider.EMAIL.value)
    
    subject = "LMS System - Email Test"
    message = "This is a test email from the LMS Backend system."
    html_message = """
    <html>
        <body>
            <h1 style='color: #4A90E2;'>LMS System Test</h1>
            <p>Hello! This is a <strong>test email</strong> sent via Django's SMTP backend.</p>
            <p>If you received this, your Gmail SMTP configuration is working correctly.</p>
        </body>
    </html>
    """
    
    print(f"Sending test email to: {recipient}...")
    try:
        result = service.send_mail(
            subject=subject,
            message=message,
            recipient_list=[recipient],
            html_message=html_message
        )
        print(f"Successfully sent! Result: {result}")
        print("Check your inbox (and spam folder) for the message.")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Ensure you are using an 'App Password' if using Gmail with 2FA.")
        print("2. Check if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are correct in .env.")
        print("3. Ensure EMAIL_PORT is 587 and EMAIL_USE_TLS is True.")

if __name__ == "__main__":
    target_email = sys.argv[1] if len(sys.argv) > 1 else None
    send_test_email(target_email)
