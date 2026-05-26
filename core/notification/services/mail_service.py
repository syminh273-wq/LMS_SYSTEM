from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from core.notification.interfaces.notification_interface import EmailNotificationInterface
from django.conf import settings


class MailService(EmailNotificationInterface):
    """Service for sending emails using Django's built-in mail support."""

    def send_mail(self, subject: str, message: str, recipient_list: list, html_message: str = None):
        """Send an email to a list of recipients."""
        return send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )

    def send_template_mail(self, subject: str, template_name: str, context: dict, recipient_list: list):
        """Send an email using a template."""
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        return self.send_mail(
            subject=subject,
            message=plain_message,
            recipient_list=recipient_list,
            html_message=html_message
        )

    def send_token_template(self, recipient_list: list, token: str, template_name: str = None):
        """Send a token using a template (defaults to token_template.html)."""
        template = template_name or "emails/token_template.html"
        return self.send_template_mail(
            subject="LMS System - Your Verification Token",
            template_name=template,
            context={"token": token},
            recipient_list=recipient_list
        )
