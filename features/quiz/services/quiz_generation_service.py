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
import logging
import os
import re
import tempfile

import requests

from core.ai.llm.services.ai_client import AIClient

logger = logging.getLogger(__name__)

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
    "OUTPUT FORMAT RULES (MUST FOLLOW EXACTLY):\n"
    "- Print ONLY raw JSON lines. Zero prose, zero markdown, zero extra text.\n"
    "- Line 1 MUST be: {\"title\":\"<quiz title>\",\"description\":\"<one sentence description>\"}\n"
    "- Each question MUST be: {\"question\":\"<question text>\",\"a\":\"<option A>\",\"b\":\"<option B>\",\"c\":\"<option C>\",\"d\":\"<option D>\",\"correct\":\"<letter a or b or c or d>\",\"explanation\":\"<why the correct answer is right>\"}\n"
    "- The field \"correct\" MUST contain exactly one lowercase letter: a, b, c, or d.\n"
    "- The field \"explanation\" MUST explain why the correct answer is correct.\n"
    "- Each JSON object on ONE line only. No line breaks inside JSON values.\n"
    "- Start immediately with the title line. Do not write anything before or after."
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
    rules_text = "\n".join(f"- {r}" for r in rules)
    content = (
        f"You are: {persona}\n"
        f"Language: Vietnamese ONLY. Translate all content to Vietnamese.\n"
        f"Task: {task_type}. Generate exactly {num_questions} questions.\n"
        f"Rules:\n{rules_text}\n\n"
        f"{format_rule}"
    )
    return {"role": "system", "content": content}


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
    Extract complete JSON objects from a text stream using brace-depth tracking.
    Handles both single-line NDJSON and multi-line JSON objects.
    Ignores all non-JSON text (extra words, markdown, etc.) between objects.
    """
    obj_buf = ''
    depth = 0
    in_string = False
    escape_next = False

    for chunk in chunks:
        if not isinstance(chunk, str):
            continue
        for char in chunk:
            if escape_next:
                escape_next = False
                if depth > 0:
                    obj_buf += char
                continue
            if char == '\\' and in_string:
                escape_next = True
                if depth > 0:
                    obj_buf += char
                continue
            if char == '"':
                in_string = not in_string
                if depth > 0:
                    obj_buf += char
                continue
            if in_string:
                if depth > 0:
                    obj_buf += char
                continue
            # Outside strings
            if char == '{':
                depth += 1
                obj_buf += char
            elif char == '}':
                if depth > 0:
                    depth -= 1
                    obj_buf += char
                    if depth == 0:
                        try:
                            yield json.loads(obj_buf)
                        except json.JSONDecodeError:
                            pass
                        obj_buf = ''
            elif depth > 0:
                obj_buf += char
            # depth == 0: ignore commas, whitespace, "NDJSON" text, etc.


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class QuizGenerationService:

    # ── Sync (legacy) ────────────────────────────────────────────────────────

    @classmethod
    def _normalize_correct(cls, raw) -> str:
        """Normalize any answer-letter shape to 'a'/'b'/'c'/'d'."""
        if raw is None:
            return 'a'
        s = str(raw).strip().lower()
        mapping = {
            'a': 'a', '1': 'a', '①': 'a',
            'b': 'b', '2': 'b', '②': 'b',
            'c': 'c', '3': 'c', '③': 'c',
            'd': 'd', '4': 'd', '④': 'd',
        }
        return mapping.get(s, s[:1] if s[:1] in 'abcd' else 'a')

    @classmethod
    def _looks_like_questions_json(cls, raw: str) -> bool:
        """Cheap pre-check: does the raw text contain a plausible questions array?"""
        if not raw:
            return False
        low = raw.lower()
        has_q = '"question"' in low or '"q"' in low
        has_correct = '"correct"' in low or '"answer"' in low or '"ans"' in low
        return has_q and has_correct

    @classmethod
    def _parse_quiz_payload(cls, raw: str, num_questions: int) -> dict:
        """
        Parse AI raw text into a normalized quiz dict.
        Tolerant: strips code fences, finds first '{' and last '}', normalizes options.
        Also handles NDJSON output (one JSON object per line) — common with
        small local models (qwen2.5:3b) that ignore the "single object" rule.
        Returns dict with at least {'title': str, 'description': str, 'questions': list}.
        Raises ValueError if no usable questions can be extracted.
        """
        if not raw or not raw.strip():
            raise ValueError("Empty AI response")

        clean = re.sub(r'```(?:json)?', '', raw).strip().strip('`').strip()
        start, end = clean.find('{'), clean.rfind('}')
        if start == -1 or end == -1 or end <= start:
            raise ValueError("AI did not return valid JSON (no braces found)")

        # Try strict JSON first
        data = None
        try:
            data = json.loads(clean[start:end + 1])
        except json.JSONDecodeError:
            # Fallback: try NDJSON (one object per line) — small models often emit this
            objs = []
            for line in clean.splitlines():
                line = line.strip().rstrip(',')
                if not line or not line.startswith('{'):
                    continue
                try:
                    objs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            if objs:
                title_obj = next((o for o in objs if 'title' in o and 'question' not in o), None)
                question_objs = [o for o in objs if 'question' in o or 'q' in o]
                if not question_objs and not title_obj:
                    question_objs = objs
                data = {
                    'title': (title_obj or {}).get('title', 'Untitled Quiz'),
                    'description': (title_obj or {}).get('description', ''),
                    'questions': question_objs,
                }

        if data is None:
            raise ValueError("AI returned invalid JSON")

        if not isinstance(data, dict):
            raise ValueError("AI JSON root is not an object")

        title = (data.get('title') or '').strip() or 'Untitled Quiz'
        description = (data.get('description') or '').strip()

        raw_questions = data.get('questions') or data.get('items') or []
        if not isinstance(raw_questions, list):
            # Model may emit questions as a JSON string or single dict
            if isinstance(raw_questions, str):
                try:
                    raw_questions = json.loads(raw_questions)
                except json.JSONDecodeError:
                    raw_questions = []
            elif isinstance(raw_questions, dict):
                raw_questions = [raw_questions]
            else:
                raw_questions = []

        valid = []
        for q in raw_questions:
            if not isinstance(q, dict):
                continue

            # Normalize options: accept nested dict OR flat a/b/c/d
            opts_raw = q.get('options')
            if isinstance(opts_raw, dict):
                opts = {str(k).lower(): str(v) for k, v in opts_raw.items() if v}
            else:
                opts = {}
                for letter in ('a', 'b', 'c', 'd'):
                    v = q.get(letter) or q.get(letter.upper())
                    if v:
                        opts[letter] = str(v)
            opts = {k: v for k, v in opts.items() if k in ('a', 'b', 'c', 'd') and v}

            if not all(k in opts for k in ('a', 'b', 'c', 'd')):
                continue

            question_text = (q.get('question') or q.get('q') or '').strip()
            if not question_text:
                continue

            correct_raw = q.get('correct') or q.get('answer') or q.get('ans')
            correct = cls._normalize_correct(correct_raw)
            if correct not in ('a', 'b', 'c', 'd'):
                correct = 'a'

            explanation = (q.get('explanation') or q.get('why') or '').strip()

            valid.append({
                'question': question_text,
                'options': {'a': opts['a'], 'b': opts['b'], 'c': opts['c'], 'd': opts['d']},
                'correct': correct,
                'explanation': explanation,
            })

            if len(valid) >= num_questions:
                break

        if not valid:
            raise ValueError("AI returned no valid questions")

        return {'title': title, 'description': description, 'questions': valid}

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

        def validator(raw: str) -> bool:
            try:
                parsed = cls._parse_quiz_payload(raw, num_questions)
                return len(parsed['questions']) > 0
            except ValueError:
                return False

        try:
            raw = AIClient.chat_sync_with_fallback(
                messages,
                validator=validator,
                models=AIClient.TEXT_MODELS,
                timeout=90,
            )
        except RuntimeError as exc:
            logger.error("[QuizGen] All models failed: %s", exc)
            raise

        try:
            return cls._parse_quiz_payload(raw, num_questions)
        except ValueError:
            logger.error("[QuizGen] Final parse failed. Raw AI output:\n%s", raw)
            raise

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
                    break
                yield chunk

        meta_sent = False
        question_index = 0
        all_objs = list(_iter_ndjson(text_only(raw_chunks)))

        for obj in all_objs:
            # First object = quiz metadata only if it has title but no question key
            if not meta_sent:
                if 'title' in obj and 'question' not in obj:
                    yield {
                        "type": "meta",
                        "title": obj.get("title", "Untitled Quiz"),
                        "description": obj.get("description", ""),
                    }
                    meta_sent = True
                    continue
                else:
                    # Model skipped metadata — emit default and fall through to process as question
                    yield {"type": "meta", "title": "Untitled Quiz", "description": ""}
                    meta_sent = True
                    # intentionally no continue — process this obj as a question below

            # Subsequent objects = questions
            if question_index >= num_questions:
                break
            q = obj
            # Normalize: accept nested options OR flat a/b/c/d at top level
            raw_opts = q.get('options') or {
                'a': q.get('a', '') or q.get('A', ''),
                'b': q.get('b', '') or q.get('B', ''),
                'c': q.get('c', '') or q.get('C', ''),
                'd': q.get('d', '') or q.get('D', ''),
            }
            opts = {k.lower(): v for k, v in raw_opts.items() if v}
            question_text = (q.get('question') or q.get('q', '') or '').strip()
            correct = cls._normalize_correct(q.get('correct') or q.get('ans'))
            explanation = q.get('explanation') or q.get('why', '') or ''

            if not question_text:
                continue
            if not all(opts.get(k) for k in ('a', 'b', 'c', 'd')):
                continue

            yield {
                "type": "question",
                "index": question_index,
                "question": question_text,
                "options": opts,
                "correct": correct,
                "explanation": explanation,
            }
            question_index += 1

        yield {"type": "done", "total": question_index}
