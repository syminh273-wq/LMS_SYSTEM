from features.notification.services.notification_service import NotificationService


def notify_issued(student_id, collection, issued):
    title = 'Chúc mừng! Bạn đã nhận chứng chỉ'
    content = f'Bạn đã hoàn thành bộ Quiz "{collection.title}" và nhận chứng chỉ.'
    metadata = {
        'issued_certificate_uid': str(issued.uid),
        'collection_uid': str(collection.uid),
        'collection_title': collection.title,
        'classroom_id': str(issued.classroom_id),
    }
    NotificationService().send_notification(
        target_uid=student_id,
        notify_type='certificate_issued',
        title=title,
        content=content,
        metadata=metadata,
    )
