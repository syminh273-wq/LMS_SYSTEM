import base64
import json
import logging
import os
import re
import tempfile
from datetime import datetime

import requests
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from core.ai.llm.services.ai_client import AIClient
from core.ai.rag.services.rag_pipeline import RAGPipeline
from features.course.exam.models.exam import Exam
from features.course.exam.models.exam_submission import ExamSubmission

logger = logging.getLogger(__name__)

SUPPORTED_TEXT_SUFFIXES = {".pdf", ".txt", ".md"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB cap for vision calls


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
            f"EXAM_CONTENT:\n{exam_content_text or (self._load_meta(exam).get('name') or exam.title)}\n\n"
            f"STUDENT_ID:\n{submission.student_id}\n\n"
            f"STUDENT_SUBMISSION:\n{submission_text}\n\n"
            f"CLASSROOM_DOCUMENT_CONTEXT:\n{context or 'Không tìm thấy tài liệu lớp học phù hợp.'}\n\n"
            "Hãy chấm điểm bằng tiếng Việt. Nếu bài có nhiều câu/ý, breakdown phải có từng câu/ý."
        )

    def _extract_text_from_resource(self, resource):
        """Generic text extraction for Exam or ExamSubmission.

        Exam fields:           content_type, body (markdown text), meta (JSON with url/name)
        ExamSubmission fields: submission_type, content (essay text), meta (JSON with url/name)

        Returns the extracted text. Raises ValueError with a precise reason when the
        resource cannot be read (missing url, unsupported type, download failure,
        empty extracted content) so the caller can surface a useful error to the
        teacher instead of a generic "no readable text" message.
        """
        kind = "exam" if isinstance(resource, Exam) else (
            "submission" if isinstance(resource, ExamSubmission) else "resource"
        )
        meta = self._load_meta(resource)
        resource_url = meta.get("url")
        resource_name = meta.get("name") or ""

        if isinstance(resource, Exam):
            content_type = resource.content_type
            inline_text = resource.body or ""
        else:
            content_type = getattr(resource, "submission_type", None) or "file"
            inline_text = resource.content or ""

        if isinstance(resource, Exam) and content_type == "markdown":
            return inline_text
        if isinstance(resource, ExamSubmission) and content_type == "essay":
            return inline_text

        if not resource_url:
            logger.warning(
                "AI grading: %s has no url in meta (name=%r, content_type=%s)",
                kind, resource_name, content_type,
            )
            raise ValueError(
                f"{kind.capitalize()} has no downloadable file (url missing in meta). "
                f"content_type={content_type}, name={resource_name or '(empty)'}"
            )

        suffix = os.path.splitext(resource_name)[1].lower()
        if not suffix and content_type in {"pdf", "file"}:
            suffix = ".pdf" if content_type == "pdf" else ".txt"
        if not suffix and content_type in {"image", "png", "jpg", "jpeg", "webp", "gif", "bmp"}:
            suffix = ".png"

        if suffix in IMAGE_SUFFIXES:
            return self._describe_image(
                resource_url=resource_url,
                resource_name=resource_name,
                kind=kind,
            )

        if suffix not in SUPPORTED_TEXT_SUFFIXES:
            logger.warning(
                "AI grading: unsupported file type name=%r suffix=%r (content_type=%s)",
                resource_name, suffix, content_type,
            )
            raise ValueError(
                f"Unsupported file type for AI grading: name={resource_name!r}, "
                f"suffix={suffix or '(none)'}. Supported: "
                f"{sorted(SUPPORTED_TEXT_SUFFIXES | IMAGE_SUFFIXES)}. "
                f"Binary office files (.docx, .pptx, ...) cannot be graded automatically."
            )

        tmp_path = None
        try:
            response = requests.get(resource_url, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(
                "AI grading: download failed url=%s name=%r error=%s",
                resource_url, resource_name, exc,
            )
            raise ValueError(
                f"Failed to download file for AI grading: name={resource_name!r}, error={exc}"
            ) from exc

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            loader = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            if not text.strip():
                raise ValueError(
                    f"File appears to be empty or unreadable: name={resource_name!r}"
                )
            return text
        except ValueError:
            raise
        except Exception as exc:
            logger.warning(
                "AI grading: text extraction failed name=%r suffix=%s error=%s",
                resource_name, suffix, exc,
            )
            raise ValueError(
                f"Failed to extract text from file: name={resource_name!r}, error={exc}"
            ) from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _load_meta(resource):
        raw = getattr(resource, "meta", None) or ""
        try:
            return json.loads(raw) if raw else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def _describe_image(self, resource_url, resource_name, kind):
        """Download an image and have a vision model describe its content.

        Returns the description as plain text so the downstream grading flow
        can treat it like any other extracted text. Raises ValueError on any
        failure with a precise reason.
        """
        try:
            response = requests.get(resource_url, timeout=60, stream=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(
                "AI grading: image download failed url=%s name=%r error=%s",
                resource_url, resource_name, exc,
            )
            raise ValueError(
                f"Failed to download image for AI grading: name={resource_name!r}, error={exc}"
            ) from exc

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                raise ValueError(
                    f"Image too large for AI grading: name={resource_name!r} "
                    f"(>{MAX_IMAGE_BYTES // (1024*1024)} MB)"
                )
            chunks.append(chunk)
        image_bytes = b"".join(chunks)
        if not image_bytes:
            raise ValueError(f"Image is empty: name={resource_name!r}")

        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        prompt = (
            "Đây là ảnh bài làm của học sinh. Hãy trích xuất TOÀN BỘ nội dung văn bản, "
            "công thức, bảng biểu và mô tả ngắn gọn hình vẽ/sơ đồ (nếu có) theo đúng "
            "trình tự xuất hiện trong ảnh. Nếu ảnh chứa nhiều trang/khung, liệt kê rõ. "
            "Chỉ trả về nội dung trích xuất, không nhận xét thêm."
        )

        try:
            description = AIClient.chat_with_image(
                messages=[{"role": "user", "content": prompt}],
                image_b64=image_b64,
                timeout=180,
            )
        except Exception as exc:
            logger.warning(
                "AI grading: vision model failed name=%r error=%s",
                resource_name, exc,
            )
            error_text = str(exc)
            hint = ""
            if "not found" in error_text.lower() or "404" in error_text:
                hint = (
                    " Vision model is not installed in local Ollama. "
                    "Run: `ollama pull llava` (or set OLLAMA_VISION_MODEL to a vision "
                    "model you have already pulled, e.g. `llava:13b`, `llava-phi3`, `moondream`)."
                )
            raise ValueError(
                f"Failed to describe image with vision model: name={resource_name!r}, "
                f"error={error_text}.{hint}"
            ) from exc

        if not description or not description.strip():
            raise ValueError(
                f"Vision model returned empty description for image: name={resource_name!r}"
            )

        logger.info(
            "AI grading: image described name=%r kind=%s chars=%d",
            resource_name, kind, len(description),
        )
        return description

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
