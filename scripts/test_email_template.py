import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')
django.setup()

from core.notification.services.notification_service import NotificationService
from core.notification.enums.notification_provider import NotificationProvider

def test_templates(recipient=None):
    """
    Script to test multiple Email Templates.
    Usage: python scripts/test_email_template.py [recipient_email]
    """
    if not recipient:
        recipient = "hosyminh11820004@gmail.com"

    print(f"Initializing NotificationService with provider: EMAIL")
    service = NotificationService(NotificationProvider.EMAIL.value)
    
    # 1. Test Token Template
    print(f"\n--- Testing Token Template ---")
    token_context = {"token": "XYZ-456"}
    try:
        service.send_template_mail(
            subject="LMS System - Your Verification Token",
            template_name="emails/token_template.html",
            context=token_context,
            recipient_list=[recipient]
        )
        print(f"Token email sent successfully to {recipient}")
    except Exception as e:
        print(f"Failed to send token email: {str(e)}")

    # 2. Test Notification Template
    print(f"\n--- Testing Notification Template ---")
    noti_context = {
        "title": "New Course Available!",
        "user_name": "Minh Ho",
        "message": "A new course 'Advanced Django and Cassandra' has been published in your classroom. Check it out now!",
        "action_url": "https://lms.example.com/courses/123",
        "action_text": "Go to Course"
    }
    try:
        service.send_template_mail(
            subject="LMS System - New Notification",
            template_name="emails/notification_template.html",
            context=noti_context,
            recipient_list=[recipient]
        )
        print(f"Notification email sent successfully to {recipient}")
    except Exception as e:
        print(f"Failed to send notification email: {str(e)}")

    # 3. Test Token Template with Helper Method (Default Template)
    print(f"\n--- Testing send_token_template (Default) ---")
    try:
        service.send_token_template(
            recipient_list=[recipient],
            token="DEF-456"
        )
        print(f"Token email (default) sent successfully to {recipient}")
    except Exception as e:
        print(f"Failed to send default token email: {str(e)}")

    # 4. Test Token Template with Helper Method (Switch Template)
    print(f"\n--- Testing send_token_template (Switch Template) ---")
    try:
        # Using notification_template as a placeholder "switched" template for testing
        service.send_token_template(
            recipient_list=[recipient],
            token="SWI-789",
            template_name="emails/token_template.html" # Can switch to another if exists
        )
        print(f"Token email (switched) sent successfully to {recipient}")
    except Exception as e:
        print(f"Failed to send switched token email: {str(e)}")

if __name__ == "__main__":
    target_email = sys.argv[1] if len(sys.argv) > 1 else None
    test_templates(target_email)
