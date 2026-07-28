from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.calendar.viewsets.consumer_calendar_viewset import ConsumerCalendarViewSet
from features.calendar.viewsets.consumer_attendance_viewset import ConsumerAttendanceViewSet
from features.calendar.viewsets.consumer_leave_request_viewset import ConsumerLeaveRequestViewSet

router = DefaultRouter()
router.register('events', ConsumerCalendarViewSet, basename='consumer-calendar-events')
router.register('attendance', ConsumerAttendanceViewSet, basename='consumer-attendance')
router.register('leave-requests', ConsumerLeaveRequestViewSet, basename='consumer-leave-requests')

urlpatterns = [
    path('', include(router.urls)),
]
