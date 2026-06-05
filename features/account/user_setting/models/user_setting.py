from cassandra.cqlengine import columns
from core.models.cassandra import BaseCassandraModel

class UserSetting(BaseCassandraModel):
    __table_name__ = 'user_settings'

    # Partition keys
    bucket = columns.Integer(partition_key=True, default=0)
    user_id = columns.UUID(partition_key=True)
    
    # Clustering key
    key = columns.Text(primary_key=True)
    
    user_type = columns.Text(required=True, index=True) # 'consumer' or 'space'
    value = columns.Text()
    
    class Meta:
        get_pk_field = 'user_id'
