from django.urls import path
from features.face.viewsets import SpaceFaceViewSet

urlpatterns = [
    path(
        "exams/<uuid:exam_uid>/logs/",
        SpaceFaceViewSet.as_view({"get": "exam_logs"}),
        name="face-exam-logs",
    ),
]
