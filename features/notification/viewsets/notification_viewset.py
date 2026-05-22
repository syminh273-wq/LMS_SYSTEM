from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from features.notification.services.notification_service import NotificationService
from features.notification.serializers.notification_serializer import NotificationLogSerializer
from core.views.mixins import UserScopeMixin

class NotificationViewSet(UserScopeMixin, viewsets.ViewSet):
    def list(self, request):
        """Lấy danh sách thông báo"""
        target_uid = request.query_params.get('target_uid') or request.user.uid
        service = NotificationService()
        notifications = service.get_user_notifications(target_uid)
        serializer = NotificationLogSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='all')
    def all_notifications(self, request):
        """Lấy tất cả thông báo trong hệ thống (Global)"""
        limit = int(request.query_params.get('limit', 50))
        service = NotificationService()
        notifications = service.get_all_notifications(limit=limit)
        serializer = NotificationLogSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='send')
    def send_notification(self, request):
        """
        API cho FE gọi để gửi thông báo.
        BE sẽ lưu vào DB và đẩy lên Firebase.
        """
        data = request.data
        target_uid = data.get('target_uid')
        notify_type = data.get('notify_type', 'system')
        title = data.get('title')
        content = data.get('content')
        metadata = data.get('metadata', {})

        if not target_uid or not title or not content:
            return Response(
                {'error': 'target_uid, title, and content are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = NotificationService()
        log = service.send_notification(
            target_uid=target_uid,
            notify_type=notify_type,
            title=title,
            content=content,
            metadata=metadata
        )

        return Response(NotificationLogSerializer(log).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        """Đánh dấu 1 thông báo là đã đọc"""
        target_uid = request.data.get('target_uid') or request.user.uid
        service = NotificationService()
        service.mark_as_read(target_uid, pk)
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        """Đánh dấu tất cả thông báo của target_uid là đã đọc"""
        # Thử lấy từ query_params trước để đồng nhất với API list
        target_uid = request.query_params.get('target_uid') or \
                     request.data.get('target_uid') or \
                     request.user.uid
        
        service = NotificationService()
        count = service.mark_all_as_read(target_uid)
        return Response({
            'status': 'all marked as read',
            'updated_count': count,
            'target_uid': str(target_uid)
        })
