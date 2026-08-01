from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class QuizQuestion(BaseTimeStampModel):
    """
    One question belonging to a Quiz, with an arbitrary number of answer options
    (between MIN_OPTIONS and MAX_OPTIONS). Partitioned by quiz_id so all questions
    for a quiz are co-located.

    `options` is an ordered list of option texts — position determines the letter
    shown in the UI (index 0 = 'A', 1 = 'B', ...), letters are never persisted.
    `correct_option_indices` holds the 0-based indices into `options` that are correct.
    """
    quiz_id = columns.UUID(partition_key=True, required=True)
    uid = columns.UUID(primary_key=True, default=uuid7, clustering_order="ASC")

    question_text = columns.Text(required=True)
    options = columns.List(columns.Text, required=True)   # ordered option texts, MIN_OPTIONS..MAX_OPTIONS items

    question_type = columns.Text(default='single_answer')   # 'single_answer' | 'multi_answer'
    correct_option_indices = columns.List(columns.Integer, default=[])   # e.g. [0] or [0, 2]

    explanation = columns.Text(default='')
    order = columns.Integer(default=0)

    __table_name__ = 'quiz_questions'

    MIN_OPTIONS = 2
    MAX_OPTIONS = 8

    class Meta:
        get_pk_field = 'uid'
