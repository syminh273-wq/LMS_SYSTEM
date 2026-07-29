from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.calendar.viewsets.space_calendar_viewset import SpaceCalendarViewSet
from features.calendar.viewsets.space_attendance_viewset import SpaceAttendanceViewSet
from features.calendar.viewsets.space_leave_request_viewset import SpaceLeaveRequestViewSet

router = DefaultRouter()
router.register('events', SpaceCalendarViewSet, basename='space-calendar-events')
router.register('attendance', SpaceAttendanceViewSet, basename='space-attendance')
router.register('leave-requests', SpaceLeaveRequestViewSet, basename='space-leave-requests')

urlpatterns = [
    path('', include(router.urls)),
    path('recurring-schedules/', SpaceCalendarViewSet.as_view({'post': 'create_recurring'}), name='space-calendar-recurring'),
]
