from django.urls import include, path
from features.course.exam.viewsets import SpaceExamViewSet

urlpatterns = [
    path(
        'classrooms/<uuid:classroom_uid>/exams/ai-grade/',
        SpaceExamViewSet.as_view({'post': 'ai_grade_classroom_submissions'}),
    ),
    path('classrooms/', include('features.course.classroom.urls')),
    path('meeting-rooms/', include('features.course.meeting_room.urls')),
    path('exams/', include('features.course.exam.urls')),
    path('ai/', include('features.course.ai.urls')),
]
