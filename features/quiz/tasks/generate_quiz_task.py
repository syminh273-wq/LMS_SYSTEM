import logging
import traceback

from features.quiz.services.quiz_generation_service import QuizGenerationService
from features.quiz.services.quiz_service import QuizService

logger = logging.getLogger(__name__)


def _current_job():
    try:
        from rq import get_current_job
        return get_current_job()
    except Exception:
        return None


def _save_meta(**fields):
    job = _current_job()
    if job is None:
        return
    try:
        for k, v in fields.items():
            job.meta[k] = v
        job.save_meta()
    except Exception as exc:
        logger.warning("[generate_quiz_task] save_meta failed: %s", exc)


def generate_quiz_task(
    teacher_uid: str,
    content: str,
    num_questions: int = 5,
    question_type: str = 'single_answer',
    num_options: int = 4,
    option_counts: list = None,
    correct_counts: list = None,
) -> dict:
    """
    Run AI quiz generation synchronously inside the RQ worker.

    Returns a dict that is stored as job.result and exposed via the
    task status endpoint. RQ itself stores worker exceptions on the job
    — the status view reads job.is_failed to surface them.
    """
    logger.info(
        "[generate_quiz_task] start teacher=%s n=%s type=%s options=%s",
        teacher_uid, num_questions, question_type, option_counts or num_options,
    )

    _save_meta(status='running', progress=5, current_step=1)

    try:
        ai_data = QuizGenerationService.generate(
            content=content,
            num_questions=num_questions,
            question_type=question_type,
            num_options=num_options,
            option_counts=option_counts,
            correct_counts=correct_counts,
        )
    except Exception as exc:
        tb = traceback.format_exc(limit=2)
        msg = f"{type(exc).__name__}: {exc}"
        logger.error("[generate_quiz_task] AI generation failed: %s\n%s", msg, tb)
        _save_meta(
            status='failed',
            error_message=msg,
            error_traceback=tb,
        )
        raise

    _save_meta(progress=70, current_step=max(1, num_questions - 1))

    title = (ai_data.get('title') or '').strip() or 'Untitled Quiz'
    description = (ai_data.get('description') or '').strip()

    try:
        service = QuizService()
        quiz, _questions = service.create_quiz_with_questions(
            created_by=teacher_uid,
            title=title,
            description=description,
            resource_id=None,
            questions=ai_data['questions'],
        )
    except Exception as exc:
        tb = traceback.format_exc(limit=2)
        msg = f"{type(exc).__name__}: {exc}"
        logger.error("[generate_quiz_task] Persist failed: %s\n%s", msg, tb)
        _save_meta(
            status='failed',
            error_message=f"Lưu quiz thất bại: {msg}",
            error_traceback=tb,
        )
        raise

    _save_meta(
        progress=100,
        current_step=num_questions,
        quiz_uid=str(quiz.uid),
        title=quiz.title,
    )

    result = {
        'quiz_uid': str(quiz.uid),
        'title': quiz.title,
        'description': quiz.description,
        'questions_count': quiz.questions_count,
    }
    logger.info("[generate_quiz_task] done quiz=%s n=%s", quiz.uid, quiz.questions_count)
    return result
