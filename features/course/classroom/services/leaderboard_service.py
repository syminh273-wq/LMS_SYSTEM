"""Build the per-classroom leaderboard from quiz, exam, and attendance data.

Scoring (0-100):
    total_score   = quiz_avg * 0.6 + exam_avg * 0.4
    quiz_avg      = mean of best score_pct per quiz (capped 0-100, default 0 if none)
    exam_avg      = mean of grade/max_grade*100 per submission (default 0)
    attendance    = present / total_events * 100 (default 0 if no events)
"""
from collections import defaultdict

from features.course.classroom.repositories.leaderboard_repository import LeaderboardRepository
from features.account.consumer.repositories import ConsumerRepository


QUIZ_WEIGHT = 0.6
EXAM_WEIGHT = 0.4


class LeaderboardService:
    def __init__(self):
        self.repo = LeaderboardRepository()
        self.consumers = ConsumerRepository()

    def build(self, classroom_id, current_user_id, limit=10):
        members = self.repo.get_approved_students(str(classroom_id))
        student_ids = [str(m.member_id) for m in members]

        quiz_scores_by_student = self._aggregate_quiz_scores(str(classroom_id))
        exam_scores_by_student = self._aggregate_exam_scores(str(classroom_id))
        attendance_by_student = self._aggregate_attendance(str(classroom_id), student_ids)

        # Lookup consumer profiles in bulk for name/avatar (avoids N+1).
        profiles = {}
        for sid in student_ids:
            try:
                c = self.consumers.find(sid)
                if c is not None:
                    profiles[sid] = {
                        'name': getattr(c, 'full_name', '') or getattr(c, 'username', '') or sid,
                        'avatar': getattr(c, 'avatar_url', '') or '',
                    }
            except Exception:
                pass

        rows = []
        for sid in student_ids:
            quiz_avg, quiz_count = quiz_scores_by_student.get(sid, (0.0, 0))
            exam_avg, exam_count = exam_scores_by_student.get(sid, (0.0, 0))
            attendance_pct = attendance_by_student.get(sid, 0.0)
            total_score = round(quiz_avg * QUIZ_WEIGHT + exam_avg * EXAM_WEIGHT, 2)
            profile = profiles.get(sid, {'name': sid, 'avatar': ''})
            rows.append({
                'student_id': sid,
                'student_name': profile['name'],
                'student_avatar': profile['avatar'],
                'total_score': total_score,
                'quiz_avg': round(quiz_avg, 2),
                'exam_avg': round(exam_avg, 2),
                'quiz_count': quiz_count,
                'exam_count': exam_count,
                'attendance_pct': round(attendance_pct, 2),
            })

        # Highest score first; tie-break by quiz_count desc, then student_id asc.
        rows.sort(key=lambda r: (-r['total_score'], -r['quiz_count'], r['student_id']))

        for i, row in enumerate(rows, start=1):
            row['rank'] = i

        total_students = len(rows)
        my_rank = None
        my_score = None
        if current_user_id:
            cur = str(current_user_id)
            for row in rows:
                if row['student_id'] == cur:
                    my_rank = row['rank']
                    my_score = row['total_score']
                    break

        top = rows[:max(1, int(limit))]
        return {
            'classroom_uid': str(classroom_id),
            'total_students': total_students,
            'my_rank': my_rank,
            'my_score': my_score,
            'entries': top,
        }

    def _aggregate_quiz_scores(self, classroom_id):
        """Return {student_id: (avg_best_score_pct, distinct_quiz_count)}."""
        best_per_quiz = defaultdict(lambda: defaultdict(int))
        try:
            attempts = self.repo.iter_quiz_attempts(classroom_id)
        except Exception:
            attempts = []
        for a in attempts:
            sid = str(a.student_id)
            qid = str(a.quiz_id)
            score = int(getattr(a, 'score_pct', 0) or 0)
            if score > best_per_quiz[sid][qid]:
                best_per_quiz[sid][qid] = score

        try:
            logs = self.repo.iter_quiz_logs(classroom_id)
        except Exception:
            logs = []
        for lg in logs:
            sid = str(lg.student_id)
            qid = str(lg.quiz_id)
            score = int(getattr(lg, 'score_pct', 0) or 0)
            if score > best_per_quiz[sid][qid]:
                best_per_quiz[sid][qid] = score

        result = {}
        for sid, per_quiz in best_per_quiz.items():
            if not per_quiz:
                continue
            avg = sum(per_quiz.values()) / len(per_quiz)
            result[sid] = (avg, len(per_quiz))
        return result

    def _aggregate_exam_scores(self, classroom_id):
        """Return {student_id: (avg_grade_pct, submission_count)}."""
        per_student = defaultdict(list)
        try:
            subs = self.repo.iter_exam_submissions(classroom_id)
        except Exception:
            subs = []
        for s in subs:
            if getattr(s, 'is_deleted', False):
                continue
            grade = getattr(s, 'grade', None)
            max_grade = getattr(s, 'max_grade', None) or 0
            if grade is None or max_grade <= 0:
                continue
            per_student[str(s.student_id)].append((float(grade) / float(max_grade)) * 100.0)
        return {
            sid: (sum(scores) / len(scores), len(scores))
            for sid, scores in per_student.items()
        }

    def _aggregate_attendance(self, classroom_id, student_ids):
        try:
            events = self.repo.list_classroom_events(classroom_id)
        except Exception:
            events = []
        event_ids = [e.uid for e in events]
        total = len(event_ids)
        if total == 0 or not student_ids:
            return {sid: 0.0 for sid in student_ids}
        result = {}
        for sid in student_ids:
            try:
                present = self.repo.count_present(sid, event_ids)
            except Exception:
                present = 0
            result[sid] = (present / total) * 100.0
        return result
