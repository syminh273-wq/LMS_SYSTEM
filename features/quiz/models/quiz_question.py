from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class QuizQuestion(BaseTimeStampModel):
    """
    One multiple-choice question belonging to a Quiz.
    Partitioned by quiz_id so all questions for a quiz are co-located.
    """
    quiz_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="ASC")

    question_text = columns.Text(required=True)
    option_a = columns.Text(required=True)
    option_b = columns.Text(required=True)
    option_c = columns.Text(required=True)
    option_d = columns.Text(required=True)
    correct_answer = columns.Text(required=True)   # 'a' | 'b' | 'c' | 'd'
    explanation = columns.Text(default='')
    order = columns.Integer(default=0)

    __table_name__ = 'quiz_questions'

    class Meta:
        get_pk_field = 'uid'
