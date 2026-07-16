"""
Background task for AI quiz generation.

The view enqueues this with django-rq and returns task_id immediately.
The worker calls QuizGenerationService.generate (sync mode) and persists
the quiz + questions. The job's result attribute stores the payload
returned to the frontend. Job meta is updated at every state transition
so the list endpoint can show live progress even for failed jobs.
"""
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
    resource_url: str = None,
    quiz_type: str = 'multiple_choice',
    num_questions: int = 10,
    max_content_length: int = 12000,
) -> dict:
    """
    Run AI quiz generation synchronously inside the RQ worker.

    Returns a dict that is stored as job.result and exposed via the
    task status endpoint. RQ itself stores worker exceptions on the job
    — the status view reads job.is_failed to surface them.
    """
    logger.info(
        "[generate_quiz_task] start teacher=%s type=%s n=%s",
        teacher_uid, quiz_type, num_questions,
    )

    _save_meta(status='running', progress=5, current_step=1)

    try:
        ai_data = QuizGenerationService.generate(
            content=content,
            resource_url=resource_url,
            quiz_type=quiz_type,
            num_questions=num_questions,
            max_content_length=max_content_length,
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
