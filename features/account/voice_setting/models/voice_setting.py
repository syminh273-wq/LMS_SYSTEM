from cassandra.cqlengine import columns
from core.models.cassandra import BaseCassandraModel
from ..constants import VoiceNames

class UserVoiceSetting(BaseCassandraModel):
    __table_name__ = 'user_voice_settings'

    bucket = columns.Integer(partition_key=True, default=0)
    user_id = columns.UUID(primary_key=True)
    user_type = columns.Text(required=True, index=True) # 'consumer' or 'space'
    
    voice_name = columns.Text(default=VoiceNames.VI_HOAI_MY)
    is_voice_enabled = columns.Boolean(default=True)
    language = columns.Text(default='vi-VN')
    
    class Meta:
        get_pk_field = 'user_id'
