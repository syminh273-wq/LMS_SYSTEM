from enum import Enum

"""Default XP rules. Hardcoded — không lưu trong DB."""


class XpEvent(str, Enum):
    CLASSROOM_JOINED = 'classroom_joined'
    ATTENDANCE_PRESENT = 'attendance_present'

    EXAM_SUBMITTED = 'exam_submitted'
    EXAM_PASSED = 'exam_passed'

    QUIZ_SUBMITTED = 'quiz_submitted'
    QUIZ_PASSED = 'quiz_passed'
    QUIZ_PERFECT = 'quiz_perfect'

    DOC_COMPLETED = 'doc_completed'

    COLLECTION_COMPLETED = 'collection_completed'
    CERTIFICATE_ISSUED = 'certificate_issued'


XP_AMOUNTS = {
    XpEvent.CLASSROOM_JOINED:   10,
    XpEvent.ATTENDANCE_PRESENT:  5,

    XpEvent.EXAM_SUBMITTED:     20,
    XpEvent.EXAM_PASSED:        50,

    XpEvent.QUIZ_SUBMITTED:     10,
    XpEvent.QUIZ_PASSED:        15,
    XpEvent.QUIZ_PERFECT:       20,

    XpEvent.DOC_COMPLETED:      10,

    XpEvent.COLLECTION_COMPLETED: 100,
    XpEvent.CERTIFICATE_ISSUED:   200,
}


XP_DESCRIPTIONS = {
    XpEvent.CLASSROOM_JOINED:   'Tham gia lớp học',
    XpEvent.ATTENDANCE_PRESENT: 'Có mặt tại buổi học',
    XpEvent.EXAM_SUBMITTED:     'Nộp bài thi',
    XpEvent.EXAM_PASSED:        'Đậu bài thi',
    XpEvent.QUIZ_SUBMITTED:     'Nộp bài quiz',
    XpEvent.QUIZ_PASSED:        'Đậu bài quiz',
    XpEvent.QUIZ_PERFECT:       'Đạt 100% bài quiz',
    XpEvent.DOC_COMPLETED:      'Hoàn thành đọc tài liệu',
    XpEvent.COLLECTION_COMPLETED: 'Hoàn thành bộ quiz',
    XpEvent.CERTIFICATE_ISSUED: 'Nhận chứng chỉ',
}


def get_xp_amount(event_type: str, default: int = 0) -> int:
    return int(XP_AMOUNTS.get(event_type, default) or 0)
