from django.urls import include, path

urlpatterns = [
    path('classrooms/', include('features.course.classroom.urls')),
    path('meeting-rooms/', include('features.course.meeting_room.urls')),
    path('exams/', include('features.course.exam.urls')),
    path('grades/', include('features.course.grade.urls')),
]
