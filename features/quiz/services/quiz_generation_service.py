"""
QuizGenerationService

Two modes:
  generate()        → sync, returns full dict (legacy)
  generate_stream() → generator, yields parsed question dicts one by one
                      as the AI produces them (NDJSON streaming)

PDF URLs are extracted properly using pypdf — not treated as raw text.
"""
import io
import json
import os
import re
import tempfile

import requests

from core.ai.llm.services.ai_client import AIClient

# ─────────────────────────────────────────────────────────────────────────────
# PDF text extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _fetch_content(url: str, timeout: int = 30) -> str:
    """Download a resource URL and return its text content.

    For PDFs: extracts text via pypdf instead of returning raw bytes.
    For other text types: returns response text directly.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    content_type = resp.headers.get('content-type', '').lower()
    is_pdf = 'pdf' in content_type or url.lower().split('?')[0].endswith('.pdf')

    if is_pdf:
        text = _extract_pdf_text(resp.content)
        if not text.strip():
            raise ValueError("Could not extract text from PDF — the file may be scanned or image-only.")
        return text

    return resp.text


# ─────────────────────────────────────────────────────────────────────────────
# Shared output schema (injected into every system message)
# ─────────────────────────────────────────────────────────────────────────────

_NDJSON_FORMAT_RULE = (
    "CRITICAL — output format is NDJSON (one JSON object per line, nothing else):\n"
    'Line 1: {"title": "...", "description": "..."}\n'
    'Line 2+: {"question": "...", "options": {"a":"...","b":"...","c":"...","d":"..."}, "correct": "a|b|c|d", "explanation": "..."}\n'
    "No markdown. No extra whitespace between lines. No wrapper array. Start immediately."
)

_SYNC_FORMAT_RULE = (
    'Return ONLY a raw JSON object — no markdown, no text outside JSON:\n'
    '{"title":"...","description":"...","questions":[{"question":"...","options":{"a":"...","b":"...","c":"...","d":"..."},"correct":"a|b|c|d","explanation":"..."}]}\n'
    "Start with { end with }."
)

# ─────────────────────────────────────────────────────────────────────────────
# System message registry  (switch on quiz_type)
# ─────────────────────────────────────────────────────────────────────────────

def _build_system(persona: str, task_type: str, rules: list, format_rule: str, num_questions: int) -> dict:
    return {
        "role": "system",
        "content": json.dumps({
            "persona": persona,
            "language_rule": "Always write in Vietnamese. Even if the document is in English, translate the concepts into natural, accurate Vietnamese for the quiz.",
            "task": {
                "type": task_type,
                "quantity": f"Exactly {num_questions} questions",
            },
            "rules": rules,
            "output_format": format_rule,
        }, ensure_ascii=False),
    }


_RULES = {
    "multiple_choice": [
        "Exactly 4 options: a, b, c, d. One unambiguously correct answer.",
        "Distractors must be plausible but clearly wrong to anyone who read the material.",
        "Never use 'all of the above' or 'none of the above'.",
        "Cover a mix of recall, comprehension, application, and analysis.",
        "Questions and answers must come from the document content — never invent facts.",
        "Options should be similar in length to avoid length-bias clues.",
    ],
    "true_false": [
        "Each question is a declarative STATEMENT, not a question.",
        "option_a is always 'Đúng'. option_b is always 'Sai'.",
        "option_c and option_d are plausible partial-truth distractors.",
        "Exactly half the statements should be TRUE, half FALSE.",
        "False statements must contain one specific, testable error from the document.",
        "Statements must come strictly from the document.",
    ],
    "fill_blank": [
        "The question field contains the sentence with ___ marking the blank.",
        "The blank must replace a KEY TERM — not a preposition or filler word.",
        "4 options are possible words/phrases to fill the blank — only one is correct.",
        "3 wrong options must be plausible terms from the same domain.",
        "Each question tests a different key term from the document.",
    ],
    "scenario": [
        "Every question MUST open with a 2-3 sentence real-world scenario.",
        "The question asks what to do, conclude, or identify in that scenario.",
        "The correct answer requires applying document concepts, not just recalling them.",
        "Wrong options represent common misconceptions or surface-level thinking.",
        "Scenarios and concepts must be grounded in the document content.",
    ],
}

_PERSONAS = {
    "multiple_choice": "QuizMaster AI — expert MCQ designer for educational assessments",
    "true_false": "QuizMaster AI — expert True/False quiz designer",
    "fill_blank": "QuizMaster AI — expert fill-in-the-blank quiz designer",
    "scenario": "QuizMaster AI — expert scenario-based assessment designer",
}

_TASK_TYPES = {
    "multiple_choice": "Multiple-choice — 4 options, exactly 1 correct answer",
    "true_false": "True/False statements — students judge correct or incorrect",
    "fill_blank": "Fill-in-the-blank — sentence with key term removed, 4 choices",
    "scenario": "Scenario-based — real-world situation + applied-knowledge question",
}

QUIZ_TYPES = list(_RULES.keys())

_USER_TEMPLATE = "Generate the quiz from the document below.\n\n<document>\n{content}\n</document>"


def _get_messages(quiz_type: str, content: str, num_questions: int, streaming: bool) -> list:
    """Switch on quiz_type → build [system, user] message pair."""
    qt = quiz_type if quiz_type in _RULES else 'multiple_choice'
    fmt = _NDJSON_FORMAT_RULE if streaming else _SYNC_FORMAT_RULE
    system = _build_system(_PERSONAS[qt], _TASK_TYPES[qt], _RULES[qt], fmt, num_questions)
    user = {"role": "user", "content": _USER_TEMPLATE.format(content=content)}
    return [system, user]


# ─────────────────────────────────────────────────────────────────────────────
# NDJSON stream parser
# ─────────────────────────────────────────────────────────────────────────────

def _iter_ndjson(chunks):
    """
    Consume text chunks from the AI stream.
    Yields parsed dicts as each complete newline-delimited JSON line arrives.
    """
    buf = ''
    for chunk in chunks:
        if not isinstance(chunk, str):
            continue
        buf += chunk
        while '\n' in buf:
            line, buf = buf.split('\n', 1)
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass   # incomplete line or junk — keep buffering

    # flush remaining buffer (last line with no trailing newline)
    line = buf.strip()
    if line:
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class QuizGenerationService:

    # ── Sync (legacy) ────────────────────────────────────────────────────────

    @classmethod
    def generate(
        cls,
        content: str = None,
        resource_url: str = None,
        quiz_type: str = 'multiple_choice',
        num_questions: int = 10,
        max_content_length: int = 12000,
    ) -> dict:
        if not content and not resource_url:
            raise ValueError("Provide either 'content' or 'resource_url'")
        if not content:
            content = _fetch_content(resource_url)
        content = content[:max_content_length]

        messages = _get_messages(quiz_type, content, num_questions, streaming=False)
        raw = AIClient.chat_sync(messages, models=AIClient.TEXT_MODELS, timeout=90)

        clean = re.sub(r'```(?:json)?', '', raw).strip().strip('`').strip()
        start, end = clean.find('{'), clean.rfind('}')
        if start == -1:
            raise ValueError("AI did not return valid JSON")
        data = json.loads(clean[start:end + 1])

        valid = [
            q for q in data.get('questions', [])
            if all(k in q for k in ('question', 'options', 'correct', 'explanation'))
            and all(k in q['options'] for k in ('a', 'b', 'c', 'd'))
            and q['correct'] in ('a', 'b', 'c', 'd')
        ]
        data['questions'] = valid[:num_questions]
        if not data['questions']:
            raise ValueError("AI returned no valid questions")
        return data

    # ── Streaming ─────────────────────────────────────────────────────────────

    @classmethod
    def generate_stream(
        cls,
        content: str = None,
        resource_url: str = None,
        quiz_type: str = 'multiple_choice',
        num_questions: int = 10,
        max_content_length: int = 12000,
    ):
        """
        Generator that yields dicts as the AI produces them.

        First yield:  {"type": "meta",     "title": "...", "description": "..."}
        Subsequent:   {"type": "question",  "index": 0,    "question": "...", ...}
        Final yield:  {"type": "done",      "total": N}
        On error:     {"type": "error",     "detail": "..."}
        """
        try:
            if not content and not resource_url:
                raise ValueError("Provide either 'content' or 'resource_url'")
            if not content:
                content = _fetch_content(resource_url)
            content = content[:max_content_length]
        except Exception as exc:
            yield {"type": "error", "detail": str(exc)}
            return

        messages = _get_messages(quiz_type, content, num_questions, streaming=True)

        # raw_chunks is a generator of str chunks + final tuple
        raw_chunks = AIClient.chat_stream(messages, models=AIClient.TEXT_MODELS, timeout=120)

        def text_only(chunks):
            for chunk in chunks:
                if isinstance(chunk, tuple):
                    break   # ('__FULL__', ...) or ('__ERROR__', ...)
                yield chunk

        meta_sent = False
        question_index = 0

        for obj in _iter_ndjson(text_only(raw_chunks)):
            # First object = quiz metadata
            if not meta_sent:
                yield {
                    "type": "meta",
                    "title": obj.get("title", "Untitled Quiz"),
                    "description": obj.get("description", ""),
                }
                meta_sent = True
                continue

            # Subsequent objects = questions
            if question_index >= num_questions:
                break
            q = obj
            if not all(k in q for k in ('question', 'options', 'correct')):
                continue
            opts = q.get('options', {})
            if not all(k in opts for k in ('a', 'b', 'c', 'd')):
                continue
            if q.get('correct') not in ('a', 'b', 'c', 'd'):
                continue

            yield {
                "type": "question",
                "index": question_index,
                "question": q['question'],
                "options": opts,
                "correct": q['correct'],
                "explanation": q.get('explanation', ''),
            }
            question_index += 1

        yield {"type": "done", "total": question_index}
