from cassandra.cqlengine import columns
from core.models.cassandra import BaseCassandraModel

class UserSetting(BaseCassandraModel):
    __table_name__ = 'user_settings'

    # Partition key + clustering key
    user_id = columns.UUID(partition_key=True)
    key = columns.Text(primary_key=True)
    
    user_type = columns.Text(required=True, index=True) # 'consumer' or 'space'
    value = columns.Text()
    
    class Meta:
        get_pk_field = 'user_id'
