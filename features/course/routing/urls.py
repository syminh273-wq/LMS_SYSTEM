from django.urls import include, path
from features.course.exam.viewsets import SpaceExamViewSet
from features.course.views.teacher_student_views import (
    TeacherStudentListView,
    TeacherStudentDetailView,
    TeacherStudentSearchView,
)
from features.course.views.global_blacklist_views import (
    GlobalBlacklistView,
    GlobalBlacklistDetailView,
)

urlpatterns = [
    path(
        'classrooms/<uuid:classroom_uid>/exams/ai-grade/',
        SpaceExamViewSet.as_view({'post': 'ai_grade_classroom_submissions'}),
    ),
    path('classrooms/', include('features.course.classroom.routing.urls')),
    path('meeting-rooms/', include('features.course.meeting_room.routing.urls')),
    path('exams/', include('features.course.exam.routing.urls')),
    path('assignments/', include('features.course.exam.routing.assignment_urls')),
    path('ai/', include('features.course.ai.routing.urls')),
    path('students/search/', TeacherStudentSearchView.as_view(), name='teacher-students-search'),
    path('students/', TeacherStudentListView.as_view(), name='teacher-students-list'),
    path('students/<str:consumer_uid>/', TeacherStudentDetailView.as_view(), name='teacher-student-detail'),
    path('blacklist/', GlobalBlacklistView.as_view(), name='global-blacklist'),
    path('blacklist/<str:consumer_uid>/', GlobalBlacklistDetailView.as_view(), name='global-blacklist-detail'),
]
