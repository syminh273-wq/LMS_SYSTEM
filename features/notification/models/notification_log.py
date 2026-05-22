from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7

class NotificationLog(BaseTimeStampModel):
    """
    Lưu trữ lịch sử thông báo vào Cassandra.
    """
    __table_name__ = 'notification_logs'

    # Khóa chính (Partition Key)
    target_uid = columns.UUID(partition_key=True)
    
    # Clustering Key (Để sắp xếp theo thời gian mới nhất lên đầu)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")
    
    # Loại thông báo (e.g., 'student_joined', 'system', 'announcement')
    notify_type = columns.Text(index=True, required=True)
    
    # Nội dung thông báo
    title = columns.Text(required=True)
    content = columns.Text(required=True)
    
    # Dữ liệu bổ sung (JSON string)
    metadata = columns.Text(required=False)
    
    # Trạng thái đọc
    is_read = columns.Boolean(index=True, default=False)

    class Meta:
        get_pk_field = 'uid'
