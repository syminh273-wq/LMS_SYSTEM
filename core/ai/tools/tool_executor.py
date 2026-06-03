"""
LMSToolExecutor — executes tool calls from the AI agent.

Constructed with teacher_id (for authorization) and filter_meta (for RAG scoping).
Each tool method maps 1-to-1 to a tool name defined in classroom_tools.py.
"""

import json

from core.ai.rag.services.rag_pipeline import RAGPipeline

_pipeline = RAGPipeline()


class LMSToolExecutor:

    def __init__(self, teacher_id: str, filter_meta: dict = None):
        self.teacher_id = teacher_id
        self.filter_meta = filter_meta or {}
        self._member_svc = None
        self._classroom_svc = None

    # ── Lazy service init (avoid circular imports at module load) ─────────────

    def _get_member_svc(self):
        if self._member_svc is None:
            from features.course.classroom.services.classroom_member_service import ClassroomMemberService
            self._member_svc = ClassroomMemberService()
        return self._member_svc

    def _get_classroom_svc(self):
        if self._classroom_svc is None:
            from features.course.classroom.services.classroom_service import Service
            self._classroom_svc = Service()
        return self._classroom_svc

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def execute(self, name: str, args: dict) -> str:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = handler(**args)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            print(f"[ToolExecutor] {name} error: {exc}")
            return json.dumps({"error": str(exc)})

    # ── Tool implementations ──────────────────────────────────────────────────

    def _tool_search_documents(self, query: str, top_k: int = 3) -> dict:
        print(f"\n[Tool:search_documents] query={query!r} top_k={top_k} filter={self.filter_meta}")
        hits = _pipeline.search(query, top_k=top_k, filter_meta=self.filter_meta or None)
        if not hits:
            print(f"[Tool:search_documents] No results found.")
            return {"results": [], "message": "Không tìm thấy tài liệu phù hợp."}
        return {
            "results": [
                {
                    "content": h["document"],
                    "score": h.get("score"),
                    "source": h.get("metadata", {}).get("doc_name", ""),
                    "page": h.get("metadata", {}).get("page"),
                }
                for h in hits
            ]
        }

    @property
    def _classroom_id(self) -> str:
        return self.filter_meta.get("classroom_id", "")

    def _tool_count_students(self) -> dict:
        members = self._get_member_svc().get_members(self._classroom_id)
        return {"count": len(members)}

    def _resolve_consumer_by_pid(self, pid: str):
        from features.account.consumer.repositories import ConsumerRepository
        consumer = ConsumerRepository().find_by_pid(pid)
        if not consumer:
            raise ValueError(f"Không tìm thấy sinh viên với mã PID: {pid}")
        return consumer

    def _enrich_member(self, m) -> dict:
        from features.account.consumer.repositories import ConsumerRepository
        entry = {"pid": "", "name": m.member_name, "joined_at": str(m.joined_at)}
        try:
            consumer = ConsumerRepository().find(m.member_id)
            if consumer:
                entry["pid"] = consumer.pid or ""
        except Exception:
            pass
        return entry

    def _tool_list_students(self) -> dict:
        members = self._get_member_svc().get_members(self._classroom_id)
        return {
            "students": [self._enrich_member(m) for m in members],
            "total": len(members),
        }

    def _tool_list_pending_students(self) -> dict:
        pending = self._get_member_svc().get_pending_members(self._classroom_id)
        return {
            "pending": [self._enrich_member(m) for m in pending],
            "total": len(pending),
        }

    def _tool_approve_student(self, pid: str) -> dict:
        consumer = self._resolve_consumer_by_pid(pid)
        member = self._get_member_svc().approve(
            classroom_uid=self._classroom_id,
            member_id=consumer.uid,
            approved_by_id=self.teacher_id,
        )
        return {"success": True, "approved_name": member.member_name, "pid": pid}

    def _tool_kick_student(self, pid: str) -> dict:
        consumer = self._resolve_consumer_by_pid(pid)
        self._get_member_svc().kick(
            classroom_uid=self._classroom_id,
            member_id=consumer.uid,
            kicked_by_id=self.teacher_id,
        )
        return {"success": True, "kicked_pid": pid, "name": consumer.full_name or consumer.username}

    def _tool_get_student_info(self, pid: str) -> dict:
        consumer = self._resolve_consumer_by_pid(pid)
        return {
            "pid": consumer.pid,
            "full_name": consumer.full_name or "",
            "email": consumer.email or "",
            "avatar_url": consumer.avatar_url or "",
            "role": consumer.role or "",
        }

    def _tool_get_classroom_info(self) -> dict:
        classroom = self._get_classroom_svc().find(self._classroom_id)
        if not classroom:
            return {"error": "Không tìm thấy lớp học."}
        return {
            "uid": str(classroom.uid),
            "name": classroom.name,
            "description": classroom.description,
            "invite_code": classroom.pid,
            "max_students": classroom.max_students,
            "status": classroom.status,
        }

    def _tool_list_my_classrooms(self) -> dict:
        classrooms = list(self._get_classroom_svc().get_by_teacher(self.teacher_id))
        return {
            "classrooms": [
                {
                    "uid": str(c.uid),
                    "name": c.name,
                    "status": c.status,
                    "invite_code": c.pid,
                }
                for c in classrooms
            ],
            "total": len(classrooms),
        }

    def _tool_get_exam_stats(self, exam_id: str) -> dict:
        from features.course.exam.repositories import ExamRepository, ExamSubmissionRepository

        exam = ExamRepository().get_by_uid(exam_id)
        if not exam:
            return {"error": "Không tìm thấy bài thi."}

        submissions = list(ExamSubmissionRepository().list_by_exam(exam_id))
        active = [s for s in submissions if not getattr(s, "is_deleted", False)]
        graded = [s for s in active if s.graded_at is not None]
        passed = [s for s in active if getattr(s, "passed", False)]
        grades = [s.grade for s in active if s.grade is not None]

        return {
            "exam_title": exam.title,
            "total_submissions": len(active),
            "graded_count": len(graded),
            "avg_grade": round(sum(grades) / len(grades), 2) if grades else None,
            "pass_rate": round(len(passed) / len(active) * 100, 1) if active else None,
        }
