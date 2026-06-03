"""
Tool definitions (OpenAI schema) for LMS classroom management.

build_tool_definitions(classroom_id=None) returns the appropriate tool list:
  - Always includes search_documents
  - If classroom_id is given, also includes classroom management tools
"""

SEARCH_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": (
            "Tìm kiếm tài liệu, bài giảng, nội quy trong lớp học. "
            "Dùng khi câu hỏi liên quan đến nội dung tài liệu, bài giảng, quy định."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa hoặc câu hỏi cần tìm trong tài liệu",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Số kết quả trả về (mặc định 3)",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}

CLASSROOM_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "count_students",
            "description": "Đếm tổng số học sinh đã được duyệt trong lớp học hiện tại.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_students",
            "description": "Lấy danh sách học sinh đã được duyệt trong lớp học hiện tại.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pending_students",
            "description": "Lấy danh sách học sinh đang chờ duyệt vào lớp học hiện tại.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_student",
            "description": "Duyệt một học sinh vào lớp học hiện tại.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {"type": "string", "description": "Mã sinh viên (PID) của học sinh cần duyệt, ví dụ: LMS26xxxxxxxx"},
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_student",
            "description": "Xóa (kick) một học sinh ra khỏi lớp học hiện tại.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {"type": "string", "description": "Mã sinh viên (PID) của học sinh cần kick, ví dụ: LMS26xxxxxxxx"},
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_info",
            "description": "Lấy thông tin chi tiết của một học sinh theo mã sinh viên (PID).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {"type": "string", "description": "Mã sinh viên (PID), ví dụ: LMS26xxxxxxxx"},
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_classroom_info",
            "description": "Lấy thông tin chi tiết về lớp học hiện tại (tên, mô tả, mã mời, số học sinh tối đa, trạng thái).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_classrooms",
            "description": "Lấy danh sách tất cả lớp học của giáo viên hiện tại.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exam_stats",
            "description": "Lấy thống kê bài thi: tổng số bài nộp, số bài đã chấm, điểm trung bình, tỉ lệ đạt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exam_id": {"type": "string", "description": "UUID của bài thi"},
                },
                "required": ["exam_id"],
            },
        },
    },
]


def build_tool_definitions(classroom_id=None) -> list:
    """Return the tool list based on context. Always includes search_documents."""
    tools = [SEARCH_TOOL_DEFINITION]
    if classroom_id:
        tools += CLASSROOM_TOOL_DEFINITIONS
    return tools
