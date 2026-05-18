from django.urls import include, path

urlpatterns = [
    path('classrooms/', include('features.course.classroom.urls')),
    path('exams/', include('features.course.exam.urls')),
]
