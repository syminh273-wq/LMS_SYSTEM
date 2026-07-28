from django.urls import include, path

urlpatterns = [
    path('', include('features.course.classroom.routing.consumer_urls')),
    path('', include('features.course.exam.routing.consumer_urls')),
    path('meeting-rooms/', include('features.course.meeting_room.routing.urls')),
]
