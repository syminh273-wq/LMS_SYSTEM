
from cassandra.cqlengine import columns

from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Grade(BaseTimeStampModel):
    bucket = columns.Integer(partition_key=True, default=0)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="DESC")

    submission_id = columns.UUID(index=True, required=True)
    exam_id = columns.UUID(index=True, required=True)
    classroom_id = columns.UUID(index=True, required=True)
    student_id = columns.UUID(index=True, required=True)

    grader_role = columns.Text(required=True)
    grader_id = columns.UUID(required=False)
    score = columns.Float(required=True)
    max_score = columns.Float(default=10.0)
    feedback = columns.Text(default="")
    status = columns.Text(required=True)
    ai_model = columns.Text(default="")

    class Meta:
        get_pk_field = "uid"

    __table_name__ = "course_grades"
