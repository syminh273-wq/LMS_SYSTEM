from datetime import datetime, time, timezone as datetime_timezone

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from features.course.exam.repositories import ExamRepository
from core.search_engine.typesense.indexer import LMSIndexer


class ExamService:
    MARKDOWN = "markdown"
    FILE_TYPES = ["pdf", "image", "file"]
    STATUSES = ["draft", "published", "closed", "ongoing"]
    EXAM_TYPES = ["assignment", "quiz"]

    def __init__(self):
        self.exam_repo = ExamRepository()

    def validate_exam_type(self, data):
        exam_type = data.get("exam_type", "assignment")
        if exam_type not in self.EXAM_TYPES:
            raise ValueError("Invalid exam_type. Must be 'assignment' or 'quiz'")
        return exam_type

    def validate_quiz_ref(self, quiz_id):
        from features.quiz.repositories.quiz_repository import QuizRepository
        try:
            quiz = QuizRepository().find(quiz_id)
        except Exception:
            raise ValueError("Quiz not found")
        return quiz

    def validate_content(self, data):
        import json
        exam_type = data.get("exam_type", "assignment")

        if exam_type == "quiz":
            ref_id = data.get("ref_id")
            if not ref_id:
                raise ValueError("ref_id (quiz) is required for quiz exam")
            self.validate_quiz_ref(ref_id)
            data["content_type"] = "quiz"
            data["body"] = ""
            data["ref_id"] = ref_id
            data["meta"] = "{}"
            return data

        content_type = data.get("content_type")

        if content_type == self.MARKDOWN:
            body = data.get("body", "")
            if not body:
                raise ValueError("body is required when content_type is markdown")
            data["body"] = body
            data["ref_id"] = None
            data["meta"] = "{}"
            return data

        if content_type in self.FILE_TYPES:
            ref_id = data.get("ref_id")
            if not ref_id:
                raise ValueError("ref_id (resource) is required when content_type is file/pdf/image")
            try:
                from features.resource.repositories import ResourceRepository
                resource = ResourceRepository().find(ref_id)
                data["meta"] = json.dumps({"url": resource.url, "name": resource.name}, ensure_ascii=False)
            except Exception:
                data["meta"] = "{}"
            data["ref_id"] = ref_id
            data["body"] = ""

            try:
                from features.course.exam.constants import FOLDER_NAME_TO_EXAM_PERIOD, EXAM_PERIODS
                if not data.get("exam_period") or data["exam_period"] not in EXAM_PERIODS:
                    folder_id = getattr(resource, "folder_id", None)
                    if folder_id:
                        from features.resource.repositories import ResourceFolderRepository
                        folder = ResourceFolderRepository().find(folder_id)
                        resolved = FOLDER_NAME_TO_EXAM_PERIOD.get(folder.name)
                        if resolved:
                            data["exam_period"] = resolved
            except Exception:
                pass

            if "exam_period" not in data or not data.get("exam_period"):
                data["exam_period"] = "regular"

            self._maybe_move_resource_to_folder(data)

            return data

        raise ValueError("Invalid content_type")

    def validate_status(self, status):
        if status not in self.STATUSES:
            raise ValueError("Invalid status")

    def normalize_due_date(self, data):
        if "due_date" not in data:
            return data

        due_date = data.get("due_date")
        if due_date in ("", None):
            data["due_date"] = None
            return data

        if isinstance(due_date, datetime):
            parsed_due_date = due_date
        elif isinstance(due_date, str):
            parsed_due_date = parse_datetime(due_date)
            if parsed_due_date is None:
                parsed_date = parse_date(due_date)
                if parsed_date is None:
                    raise ValueError("Invalid due_date format")
                parsed_due_date = datetime.combine(parsed_date, time.min)
        else:
            raise ValueError("Invalid due_date format")

        if timezone.is_aware(parsed_due_date):
            parsed_due_date = timezone.make_naive(parsed_due_date, datetime_timezone.utc)

        data["due_date"] = parsed_due_date
        return data

    def create_exam(self, teacher_id, data, file_obj=None):
        self.validate_exam_type(data)
        data = self.normalize_due_date(data)

        if file_obj is not None:
            data = self._handle_file_upload(data, file_obj, teacher_id)
        else:
            data = self.validate_content(data)

        data["teacher_id"] = teacher_id

        if not data.get("status"):
            data["status"] = "published" if data.get("exam_mode") == "online" else "draft"

        self.validate_status(data["status"])

        exam = self.exam_repo.create(**data)
        LMSIndexer.index_exam(exam)
        return exam

    def _handle_file_upload(self, data, file_obj, teacher_id):
        from uuid import UUID
        from features.resource.services.resource_service import ResourceService
        from features.resource.services.resource_folder_seed_service import ResourceFolderSeedService
        from features.course.exam.constants import EXAM_PERIOD_TO_FOLDER_NAME, EXAM_PERIODS

        raw_classroom_id = data.get("classroom_id")
        if not raw_classroom_id:
            raise ValueError("classroom_id is required when uploading exam file")
        classroom_id_uuid = UUID(str(raw_classroom_id))

        exam_period = data.get("exam_period") or "regular"
        if exam_period not in EXAM_PERIODS:
            raise ValueError(f"Invalid exam_period. Must be one of {list(EXAM_PERIODS)}")

        target_folder = ResourceFolderSeedService().resolve_exam_sub_folder(
            classroom_id=classroom_id_uuid, exam_period=exam_period
        )

        resource_service = ResourceService()
        result = resource_service.upload_resource(
            file_obj=file_obj,
            owner_id=classroom_id_uuid,
            owner_type="classroom",
            metadata={"exam_period": exam_period},
            folder_id=target_folder.uid if target_folder else None,
        )
        if not result.get("success"):
            raise ValueError(result.get("message", "Upload failed"))

        resource = result["data"]
        data["content_type"] = self._file_extension_to_content_type(resource.file_type)
        data["ref_id"] = resource.uid
        data["body"] = ""
        data["meta"] = json.dumps({"url": resource.url, "name": resource.name}, ensure_ascii=False)
        data["exam_period"] = exam_period
        return data

    def _file_extension_to_content_type(self, file_type):
        if not file_type:
            return "file"
        ft = file_type.lower()
        if ft == "pdf":
            return "pdf"
        if ft in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"):
            return "image"
        return "file"

    def _maybe_move_resource_to_folder(self, data):
        from uuid import UUID
        from features.resource.repositories import ResourceRepository, ResourceFolderRepository
        from features.course.exam.constants import FOLDER_NAME_TO_EXAM_PERIOD, EXAM_PERIODS

        ref_id = data.get("ref_id")
        if not ref_id:
            return

        exam_period = data.get("exam_period")
        if not exam_period or exam_period not in EXAM_PERIODS:
            return

        try:
            resource = ResourceRepository().find(ref_id)
        except Exception:
            return

        if getattr(resource, "folder_id", None):
            return

        classroom_id = getattr(resource, "owner_id", None)
        if not classroom_id:
            return

        from features.resource.services.resource_folder_seed_service import ResourceFolderSeedService
        target = ResourceFolderSeedService().resolve_exam_sub_folder(
            classroom_id=classroom_id, exam_period=exam_period
        )
        if not target:
            return

        resource_repo = ResourceRepository()
        resource_repo.update(resource, folder_id=target.uid)

    def get_exam(self, uid):
        exam = self.exam_repo.get_by_uid(uid)
        if not exam:
            raise ValueError("Exam not found")
        return exam

    def list_teacher_exams(self, teacher_id, classroom_id=None, status=None, exam_mode=None):
        if classroom_id:
            exams = self.exam_repo.list_by_classroom(classroom_id, status=status, exam_mode=exam_mode)
            exams = [e for e in exams if str(e.teacher_id) == str(teacher_id)]
        else:
            exams = self.exam_repo.list_by_teacher(teacher_id, status=status, exam_mode=exam_mode)
        return exams

    def update_exam(self, uid, data):
        exam = self.get_exam(uid)
        data = self.normalize_due_date(data)

        if "exam_type" in data:
            self.validate_exam_type(data)

        if "content_type" in data or "exam_type" in data:
            data = self.validate_content(data)

        if "status" in data:
            self.validate_status(data["status"])

        updated = self.exam_repo.update(exam, **data)
        LMSIndexer.index_exam(updated)
        return updated

    def delete_exam(self, uid):
        exam = self.get_exam(uid)
        result = self.exam_repo.soft_delete(exam)
        LMSIndexer.remove_exam(str(uid))
        return result

    def list_student_exams(self, classroom_id):
        return self.exam_repo.list_published_by_classroom(classroom_id)
