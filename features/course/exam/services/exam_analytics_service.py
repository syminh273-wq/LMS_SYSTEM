from features.course.classroom.repositories import Repository as ClassroomRepository
from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository
from core.services.base_service import BaseService

SCORE_BUCKETS = [
    {"label": "<=1", "min": 0, "max": 1},
    {"label": "<=2", "min": 1.01, "max": 2},
    {"label": "<=3", "min": 2.01, "max": 3},
    {"label": "<=4", "min": 3.01, "max": 4},
    {"label": "<=5", "min": 4.01, "max": 5},
    {"label": "<=6", "min": 5.01, "max": 6},
    {"label": "<=7", "min": 6.01, "max": 7},
    {"label": "<=8", "min": 7.01, "max": 8},
    {"label": "<=9", "min": 8.01, "max": 9},
    {"label": "<=10", "min": 9.01, "max": 10},
]


class ExamAnalyticsService(BaseService):
    def __init__(self):
        self.exam_repo = ExamRepository()
        self.classroom_repo = ClassroomRepository()
        self.member_repo = ClassroomMemberRepository()
        self.submission_repo = ExamSubmissionRepository()

    def get_exam_analytics(self, exam_id, teacher_id):
        exam = self.exam_repo.get_by_uid(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        if str(exam.teacher_id) != str(teacher_id):
            raise ValueError("You do not own this exam")

        try:
            classroom = self.classroom_repo.find(exam.classroom_id)
        except Exception:
            raise ValueError("Classroom not found")

        members = [
            m for m in self.member_repo.get_members(exam.classroom_id)
            if m.role == "student"
        ]
        submissions = list(self.submission_repo.list_by_exam(exam_id))

        stats = self._build_stats(members, submissions)

        return {
            "exam": exam,
            "classroom": classroom,
            "members": members,
            "submissions": submissions,
            "stats": stats,
        }

    def _build_stats(self, members, submissions):
        sub_by_student = {str(s.student_id): s for s in submissions}

        matched = [sub_by_student.get(str(m.member_id)) for m in members]
        submitted = sum(1 for s in matched if s is not None)
        missing = max(0, len(members) - submitted)

        graded_matched = [s for s in matched if s is not None and s.grade is not None]
        graded = len(graded_matched)
        passed = sum(1 for s in matched if s is not None and s.passed is True)
        failed = sum(1 for s in matched if s is not None and s.passed is False)

        submission_rate = round((submitted / len(members)) * 100) if members else 0
        completion_rate = round((graded / len(members)) * 100) if members else 0
        average_score = (
            round(sum(s.grade for s in graded_matched) / graded, 1) if graded else None
        )

        return {
            "total_members": len(members),
            "submitted": submitted,
            "missing": missing,
            "graded": graded,
            "passed": passed,
            "failed": failed,
            "submission_rate": submission_rate,
            "completion_rate": completion_rate,
            "average_score": average_score,
            **self._build_score_distribution(submissions),
        }

    def _build_score_distribution(self, submissions):
        grades = sorted(
            s.grade for s in submissions if isinstance(s.grade, (int, float))
        )

        score_buckets = []
        for bucket in SCORE_BUCKETS:
            count = sum(1 for g in grades if bucket["min"] <= g <= bucket["max"] + 0.0001)
            score_buckets.append({
                "label": bucket["label"],
                "count": count,
                "percent": round((count / len(grades)) * 100) if grades else 0,
            })

        total_score = sum(grades)
        average_grade = total_score / len(grades) if grades else 0
        if not grades:
            median_grade = 0
        elif len(grades) % 2 == 1:
            median_grade = grades[(len(grades) - 1) // 2]
        else:
            median_grade = (grades[len(grades) // 2 - 1] + grades[len(grades) // 2]) / 2

        counts = {}
        for g in grades:
            key = round(g, 1)
            counts[key] = counts.get(key, 0) + 1
        mode_grade = 0
        max_count = 0
        for value, count in counts.items():
            if count > max_count:
                max_count = count
                mode_grade = value

        return {
            "score_buckets": score_buckets,
            "total_score": total_score,
            "average_grade": round(average_grade, 2),
            "median_grade": round(median_grade, 1),
            "mode_grade": round(mode_grade, 1),
        }
