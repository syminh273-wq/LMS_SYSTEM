from django.urls import path
from features.face.viewsets import ConsumerFaceViewSet

urlpatterns = [
    path(
        "enroll/",
        ConsumerFaceViewSet.as_view({"get": "enrollment_status", "post": "enroll"}),
        name="face-enroll",
    ),
    path(
        "exams/<uuid:exam_uid>/verify/",
        ConsumerFaceViewSet.as_view({"post": "verify"}),
        name="face-verify",
    ),
    path(
        "classrooms/<uuid:classroom_uid>/verify/",
        ConsumerFaceViewSet.as_view({
            "get": "classroom_session_status",
            "post": "verify_for_classroom",
        }),
        name="face-classroom-verify",
    ),
]
