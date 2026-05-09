from django.db.models import TextChoices


class ConsumerRole(TextChoices):
    STUDENT = 'student', 'Student'
    INSTRUCTOR = 'instructor', 'Instructor'
    ADMIN = 'admin', 'Admin'
