from django.urls import path
from features.notification.viewsets.notification_viewset import NotificationViewSet

list_view = NotificationViewSet.as_view({'get': 'list'})
mark_read_view = NotificationViewSet.as_view({'post': 'mark_read'})
mark_all_read_view = NotificationViewSet.as_view({'post': 'mark_all_read'})
send_notification_view = NotificationViewSet.as_view({'post': 'send_notification'})
all_notifications_view = NotificationViewSet.as_view({'get': 'all_notifications'})

urlpatterns = [
    path('', list_view, name='notification-list'),
    path('all/', all_notifications_view, name='notification-all'),
    path('read-all/', mark_all_read_view, name='notification-read-all'),
    path('send/', send_notification_view, name='notification-send'),
    path('<uuid:pk>/read/', mark_read_view, name='notification-read'),
]
