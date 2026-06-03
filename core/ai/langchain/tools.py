"""
Converts LMSToolExecutor methods into LangChain StructuredTools.
Each tool has a typed Pydantic schema so the LLM can call them correctly.
"""

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


# ── Argument schemas ──────────────────────────────────────────────────────────

class SearchInput(BaseModel):
    query: str = Field(..., description="Từ khóa hoặc câu hỏi cần tìm trong tài liệu")
    top_k: int = Field(3, description="Số kết quả trả về (tối đa 20)")

class PidInput(BaseModel):
    pid: str = Field(..., description="Mã sinh viên (PID), ví dụ: LMS26xxxxxxxx")

class ExamIdInput(BaseModel):
    exam_id: str = Field(..., description="UUID của bài thi")


# ── Builder ───────────────────────────────────────────────────────────────────

def build_langchain_tools(executor, has_classroom: bool = False, include_search: bool = True) -> list:
    """
    Returns a list of LangChain tools backed by LMSToolExecutor.
    include_search=True  → includes search_documents.
    has_classroom=True   → includes classroom management tools.
    """
    tools = []

    if include_search:
        def _search(query: str, top_k: int = 3) -> str:
            return executor.execute("search_documents", {"query": query, "top_k": top_k})

        tools.append(StructuredTool.from_function(
            func=_search,
            name="search_documents",
            description="Tìm kiếm tài liệu, bài giảng, nội quy trong lớp học. Dùng khi câu hỏi liên quan đến nội dung tài liệu.",
            args_schema=SearchInput,
        ))

    if not has_classroom:
        return tools

    # ── Classroom management tools ────────────────────────────────────────────

    def _count_students() -> str:
        return executor.execute("count_students", {})

    tools.append(StructuredTool.from_function(
        func=_count_students,
        name="count_students",
        description="Đếm tổng số học sinh đã được duyệt trong lớp học hiện tại.",
    ))

    def _list_students() -> str:
        return executor.execute("list_students", {})

    tools.append(StructuredTool.from_function(
        func=_list_students,
        name="list_students",
        description="Lấy danh sách học sinh đã được duyệt trong lớp học hiện tại.",
    ))

    def _list_pending_students() -> str:
        return executor.execute("list_pending_students", {})

    tools.append(StructuredTool.from_function(
        func=_list_pending_students,
        name="list_pending_students",
        description="Lấy danh sách học sinh đang chờ duyệt vào lớp học hiện tại.",
    ))

    def _approve_student(pid: str) -> str:
        return executor.execute("approve_student", {"pid": pid})

    tools.append(StructuredTool.from_function(
        func=_approve_student,
        name="approve_student",
        description="Duyệt một học sinh vào lớp học hiện tại.",
        args_schema=PidInput,
    ))

    def _kick_student(pid: str) -> str:
        return executor.execute("kick_student", {"pid": pid})

    tools.append(StructuredTool.from_function(
        func=_kick_student,
        name="kick_student",
        description="Xóa (kick) một học sinh ra khỏi lớp học hiện tại.",
        args_schema=PidInput,
    ))

    def _get_student_info(pid: str) -> str:
        return executor.execute("get_student_info", {"pid": pid})

    tools.append(StructuredTool.from_function(
        func=_get_student_info,
        name="get_student_info",
        description="Lấy thông tin chi tiết của một học sinh theo mã sinh viên (PID).",
        args_schema=PidInput,
    ))

    def _get_classroom_info() -> str:
        return executor.execute("get_classroom_info", {})

    tools.append(StructuredTool.from_function(
        func=_get_classroom_info,
        name="get_classroom_info",
        description="Lấy thông tin chi tiết về lớp học hiện tại (tên, mô tả, mã mời, số học sinh, trạng thái).",
    ))

    def _list_my_classrooms() -> str:
        return executor.execute("list_my_classrooms", {})

    tools.append(StructuredTool.from_function(
        func=_list_my_classrooms,
        name="list_my_classrooms",
        description="Lấy danh sách tất cả lớp học của giáo viên hiện tại.",
    ))

    def _get_exam_stats(exam_id: str) -> str:
        return executor.execute("get_exam_stats", {"exam_id": exam_id})

    tools.append(StructuredTool.from_function(
        func=_get_exam_stats,
        name="get_exam_stats",
        description="Lấy thống kê bài thi: tổng số bài nộp, số đã chấm, điểm trung bình, tỉ lệ đạt.",
        args_schema=ExamIdInput,
    ))

    return tools
