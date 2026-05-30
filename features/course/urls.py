from django.urls import include, path
from features.course.exam.viewsets import SpaceExamViewSet
from features.course.classroom.views.teacher_student_views import (
    TeacherStudentListView,
    TeacherStudentDetailView,
    TeacherStudentSearchView,
)

urlpatterns = [
    path(
        'classrooms/<uuid:classroom_uid>/exams/ai-grade/',
        SpaceExamViewSet.as_view({'post': 'ai_grade_classroom_submissions'}),
    ),
    path('classrooms/', include('features.course.classroom.urls')),
    path('meeting-rooms/', include('features.course.meeting_room.urls')),
    path('exams/', include('features.course.exam.urls')),
    path('ai/', include('features.course.ai.urls')),
    # Teacher's student roster
    path('students/search/', TeacherStudentSearchView.as_view(), name='teacher-students-search'),
    path('students/', TeacherStudentListView.as_view(), name='teacher-students-list'),
    path('students/<str:consumer_uid>/', TeacherStudentDetailView.as_view(), name='teacher-student-detail'),
]
