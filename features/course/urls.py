from django.urls import include, path

urlpatterns = [
    path('classrooms/', include('features.course.classroom.urls')),
]
