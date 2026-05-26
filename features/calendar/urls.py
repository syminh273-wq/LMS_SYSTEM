from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.calendar.viewsets.calendar_viewset import CalendarViewSet
from features.calendar.viewsets.attendance_viewset import AttendanceViewSet
from features.calendar.viewsets.leave_request_viewset import LeaveRequestViewSet

router = DefaultRouter()
router.register('events', CalendarViewSet, basename='space-calendar-events')
router.register('attendance', AttendanceViewSet, basename='space-attendance')
router.register('leave-requests', LeaveRequestViewSet, basename='space-leave-requests')

urlpatterns = [
    path('', include(router.urls)),
]
