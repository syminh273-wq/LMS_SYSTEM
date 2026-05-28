import json
import os
import re
import tempfile
from datetime import datetime

import requests
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from core.ai.llm.services.ai_client import AIClient
from core.ai.rag.services.rag_pipeline import RAGPipeline


class ExamAIGradingService:
    DEFAULT_RUBRIC = (
        "Hệ thống chấm điểm ở mức độ KỶ LUẬT CAO NHẤT theo các tiêu chí:\n"
        "1. Tính Chính xác và Logic (30%): Sai sót về sự kiện, logic hoặc phương pháp chuyên môn sẽ bị trừ điểm cực nặng (50-100% câu).\n"
        "2. Độ đầy đủ và Chi tiết (20%): Phải giải quyết tất cả yêu cầu chính, phụ và các ý ngầm định. Thiếu bất kỳ chi tiết nào đều bị trừ điểm.\n"
        "3. Tư duy Phản biện và Chiều sâu (20%): Đánh giá phân tích sâu sắc. Câu trả lời hời hợt, mang tính đối phó hoặc 'văn mẫu' chỉ được tối đa 30% số điểm câu đó.\n"
        "4. Sử dụng Tài liệu và Thuật ngữ (15%): Bắt buộc dùng đúng thuật ngữ chuyên môn và phương pháp từ tài liệu lớp học. Dùng từ ngữ phổ thông thay cho thuật ngữ chuyên môn sẽ bị trừ điểm.\n"
        "5. Hình thức và Tính chuyên nghiệp (15%): Cấu trúc bài làm phải mạch lạc, rõ ràng. Sai định dạng hoặc trình bày cẩu thả trừ 20% tổng điểm.\n"
        "6. QUY TẮC ĐẶC BIỆT (MẠNH TAY):\n"
        "   - Lạc đề hoặc không liên quan đến EXAM_CONTENT: 0 điểm toàn bài.\n"
        "   - Nội dung có dấu hiệu copy-paste máy móc hoặc lặp lại vô nghĩa: 0 điểm câu đó.\n"
        "   - Thiếu dẫn chứng/ví dụ minh họa khi đề yêu cầu: Trừ 50-70% số điểm câu."
    )

    SYSTEM_PROMPT = (
        "Bạn là giám khảo khắt khe nhất, đề cao tính học thuật và kỷ luật.\n"
        "Nhiệm vụ: Soi xét từng chi tiết trong bài làm của sinh viên để tìm lỗi sai và đánh giá thực lực.\n"
        "Hướng dẫn:\n"
        "- ĐỐI CHIẾU nghiêm ngặt STUDENT_SUBMISSION với EXAM_CONTENT. Nếu bài làm không bám sát đề, cho 0 điểm ngay.\n"
        "- PHÊ BÌNH thẳng thắn: Trong phần 'feedback' và 'breakdown', hãy chỉ rõ sự yếu kém, thiếu sót hoặc sai lầm của sinh viên.\n"
        "- KHÔNG NƯƠNG TAY: Điểm 10 chỉ dành cho bài làm hoàn hảo, có tư duy vượt trội. Bài làm trung bình chỉ được 4-5 điểm.\n"
        "- Tuyệt đối chỉ dựa trên tài liệu được cung cấp (CLASSROOM_DOCUMENT_CONTEXT).\n"
        "- Trả về JSON, không giải thích thêm.\n"
        "Schema JSON:\n"
        "{\n"
        '  "grade": number,\n'
        '  "feedback": "nhận xét nghiêm khắc và chuyên môn",\n'
        '  "reason": "phân tích tổng quát các lỗi sai dựa trên rubric",\n'
        '  "confidence": number,\n'
        '  "breakdown": [\n'
        '    {"question": "Câu/ý", "score": number, "max_score": number, "reason": "phân tích chi tiết lỗi sai và lý do trừ điểm"}\n'
        "  ]\n"
        "}\n"
    )

    def __init__(self):
        self.pipeline = RAGPipeline()

    def grade(self, exam, submission, rubric="", max_grade=10, top_k=5):
        # Extract text from both exam and submission resources
        exam_content_text = self._extract_text_from_resource(exam)
        submission_text = self._extract_text_from_resource(submission)

        if not submission_text.strip():
            raise ValueError("Submission has no readable text for AI grading")

        hits = self.pipeline.search(
            self._build_search_query(exam, exam_content_text, submission_text),
            top_k=top_k,
            filter_meta={"classroom_id": str(exam.classroom_id)},
        )
        context = "\n\n---\n\n".join(hit["document"] for hit in hits) if hits else ""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self._build_user_prompt(
                    exam=exam,
                    exam_content_text=exam_content_text,
                    submission=submission,
                    submission_text=submission_text,
                    context=context,
                    rubric=rubric or self.DEFAULT_RUBRIC,
                    max_grade=max_grade,
                ),
            },
        ]

        raw = AIClient.chat_sync(messages, timeout=180)
        result = self._parse_json(raw)
        result["grade"] = self._clamp_float(result.get("grade"), 0, max_grade)
        result["confidence"] = self._clamp_float(result.get("confidence", 0), 0, 1)
        result["feedback"] = str(result.get("feedback") or "")
        result["reason"] = str(result.get("reason") or "")
        result["breakdown"] = result.get("breakdown") if isinstance(result.get("breakdown"), list) else []
        result["sources"] = self._deduplicate_sources(hits)
        result["graded_at"] = datetime.utcnow()
        result["model"] = ",".join(AIClient.TEXT_MODELS)
        return result

    def _build_search_query(self, exam, exam_content_text, submission_text):
        # Focus RAG search on exam title and core content to reduce noise
        return "\n".join(
            part for part in [
                exam.title,
                exam.description,
                exam_content_text[:1000], # Include start of exam for context
                submission_text[:1000],    # Include start of submission
            ]
            if part
        )

    def _build_user_prompt(self, exam, exam_content_text, submission, submission_text, context, rubric, max_grade):
        return (
            f"MAX_GRADE: {max_grade}\n\n"
            f"RUBRIC:\n{rubric}\n\n"
            f"EXAM_TITLE:\n{exam.title}\n\n"
            f"EXAM_DESCRIPTION:\n{exam.description or ''}\n\n"
            f"EXAM_CONTENT:\n{exam_content_text or exam.resource_name}\n\n"
            f"STUDENT_ID:\n{submission.student_id}\n\n"
            f"STUDENT_SUBMISSION:\n{submission_text}\n\n"
            f"CLASSROOM_DOCUMENT_CONTEXT:\n{context or 'Không tìm thấy tài liệu lớp học phù hợp.'}\n\n"
            "Hãy chấm điểm bằng tiếng Việt. Nếu bài có nhiều câu/ý, breakdown phải có từng câu/ý."
        )

    def _extract_text_from_resource(self, resource):
        """Generic text extraction for Exam or ExamSubmission"""
        if resource.content_type == "markdown":
            return resource.content or ""

        if not resource.resource_url:
            return ""

        suffix = os.path.splitext(resource.resource_name or "")[1].lower()
        if not suffix and resource.content_type in {"pdf", "file"}:
            suffix = ".pdf" if resource.content_type == "pdf" else ".txt"

        if suffix not in {".pdf", ".txt", ".md"}:
            return ""

        tmp_path = None
        try:
            response = requests.get(resource.resource_url, timeout=60)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            loader = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path)
            docs = loader.load()
            return "\n\n".join(doc.page_content for doc in docs)
        except Exception:
            # Fallback to resource name if extraction fails
            return resource.resource_name or ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _parse_json(self, raw):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("AI did not return valid grading JSON")
            return json.loads(match.group(0))

    def _clamp_float(self, value, minimum, maximum):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = minimum
        return max(minimum, min(maximum, number))

    def _deduplicate_sources(self, hits):
        sources = []
        seen = set()
        for hit in hits:
            metadata = hit.get("metadata") or {}
            key = metadata.get("resource_uid") or metadata.get("doc_name") or hit.get("id")
            if key in seen:
                continue
            seen.add(key)
            sources.append({
                "resource_uid": metadata.get("resource_uid"),
                "doc_name": metadata.get("doc_name", "Tài liệu lớp học"),
                "doc_url": metadata.get("doc_url"),
                "page": metadata.get("page"),
                "score": hit.get("score", 0),
            })
        return sources
