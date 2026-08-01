import io
import json
import logging
import re

from core.ai.llm.services.ai_client import AIClient
from features.quiz.models.quiz_question import QuizQuestion

logger = logging.getLogger(__name__)

_MAX_CONTENT_LENGTH = 12000
_DEFAULT_NUM_OPTIONS = 4
_TF_OPTIONS = ["Đúng", "Sai"]



def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    if not pdf_bytes.startswith(b'%PDF-'):
        raise ValueError('File không đúng định dạng PDF.')
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _normalize_option_counts(option_counts=None, num_questions: int = 5, num_options: int = _DEFAULT_NUM_OPTIONS) -> list:
    """Build the per-question option-count list callers actually iterate on.
    Explicit `option_counts` wins; otherwise every question gets `num_options`."""
    if option_counts:
        return [
            max(QuizQuestion.MIN_OPTIONS, min(QuizQuestion.MAX_OPTIONS, int(c)))
            for c in option_counts
        ]
    n = max(1, int(num_questions))
    count = max(QuizQuestion.MIN_OPTIONS, min(QuizQuestion.MAX_OPTIONS, int(num_options)))
    return [count] * n


def _normalize_correct_counts(correct_counts, option_counts: list):
    """Clamp each required correct-answer count into [1, that question's option count].
    Returns None when not provided — the AI then decides freely per question."""
    if not correct_counts:
        return None
    return [
        max(1, min(option_counts[i], int(c)))
        for i, c in enumerate(correct_counts)
    ]


def _build_option_counts_instruction(option_counts: list, correct_counts: list = None) -> str:
    if correct_counts is None and len(set(option_counts)) == 1:
        return f"Each question MUST have exactly {option_counts[0]} options."
    lines = []
    for i, c in enumerate(option_counts):
        if correct_counts is not None:
            lines.append(f"  Question {i + 1}: exactly {c} options, exactly {correct_counts[i]} of them correct")
        else:
            lines.append(f"  Question {i + 1}: exactly {c} options")
    instruction = "Each question has its OWN requirements — follow exactly:\n" + "\n".join(lines)

    if correct_counts is not None:
        example_idx = next((i for i, n in enumerate(correct_counts) if n > 1), 0)
        example_correct = list(range(correct_counts[example_idx]))
        instruction += (
            "\n\nTHE CORRECT-ANSWER COUNT PER QUESTION IS MANDATORY, NOT A SUGGESTION.\n"
            f"- Do NOT default to picking just one correct answer per question.\n"
            f"- Example: question {example_idx + 1} above requires exactly "
            f"{correct_counts[example_idx]} correct answers, so its \"correct\" field MUST be "
            f"an array with exactly {correct_counts[example_idx]} indices, e.g. {example_correct}.\n"
            "- Before answering, count the entries in your \"correct\" array for every single "
            "question and verify it matches that question's required count exactly."
        )
    return instruction


_NDJSON_FORMAT_RULE = (
    "OUTPUT FORMAT RULES (MUST FOLLOW EXACTLY):\n"
    "- Print ONLY raw JSON lines. Zero prose, zero markdown, zero extra text.\n"
    "- Line 1 MUST be: {\"title\":\"<quiz title>\",\"description\":\"<one sentence description>\"}\n"
    "- Each question MUST be: {\"question\":\"<question text>\",\"options\":[\"<option 1>\",\"<option 2>\",...],\"correct\":<0-based index of the correct option>,\"explanation\":\"<why the correct answer is right>\"}\n"
    "- The \"options\" array length MUST match the required option count for that question (see requirements above).\n"
    "- The \"correct\" field MUST be a single integer: the 0-based index into \"options\" (0 = first option).\n"
    "- The \"explanation\" field MUST explain why the correct answer is correct.\n"
    "- Each JSON object on ONE line only. No line breaks inside JSON values.\n"
    "- Start immediately with the title line. Do not write anything before or after."
)

_SYNC_FORMAT_RULE = (
    'Return ONLY a raw JSON object — no markdown, no text outside JSON:\n'
    '{"title":"...","description":"...","questions":[{"question":"...","options":["...","...",...],"correct":<0-based index>,"explanation":"..."}]}\n'
    "Start with { end with }."
)

_NDJSON_FORMAT_RULE_MULTI = (
    "OUTPUT FORMAT RULES (MUST FOLLOW EXACTLY):\n"
    "- Print ONLY raw JSON lines. Zero prose, zero markdown, zero extra text.\n"
    "- Line 1 MUST be: {\"title\":\"<quiz title>\",\"description\":\"<one sentence description>\"}\n"
    "- Each question MUST be: {\"question\":\"<question text>\",\"options\":[\"<option 1>\",\"<option 2>\",...],\"correct\":[<index>,<index>,...],\"explanation\":\"<why those answers are right>\"}\n"
    "- The \"options\" array length MUST match the required option count for that question (see requirements above).\n"
    "- The \"correct\" field MUST be a JSON array of 1 or more 0-based indices into \"options\".\n"
    "- The \"explanation\" field MUST explain why each correct answer is correct.\n"
    "- Each JSON object on ONE line only. No line breaks inside JSON values.\n"
    "- Start immediately with the title line. Do not write anything before or after."
)

_SYNC_FORMAT_RULE_MULTI = (
    'Return ONLY a raw JSON object — no markdown, no text outside JSON:\n'
    '{"title":"...","description":"...","questions":[{"question":"...","options":["...","...",...],"correct":[<index>,<index>],"explanation":"..."}]}\n'
    'The "correct" field MUST be an array of 0-based indices into "options".\n'
    "Start with { end with }."
)

_NDJSON_FORMAT_RULE_TF = (
    "OUTPUT FORMAT RULES (MUST FOLLOW EXACTLY):\n"
    "- Print ONLY raw JSON lines. Zero prose, zero markdown, zero extra text.\n"
    "- Line 1 MUST be: {\"title\":\"<quiz title>\",\"description\":\"<one sentence description>\"}\n"
    "- Each item MUST be: {\"question\":\"<the statement>\",\"correct\":true|false,\"explanation\":\"<why the statement is true or false>\"}\n"
    "- Do NOT include an \"options\" field — there are none, only true/false.\n"
    "- The \"correct\" field MUST be the JSON boolean true or false (not a string).\n"
    "- Each JSON object on ONE line only. No line breaks inside JSON values.\n"
    "- Start immediately with the title line. Do not write anything before or after."
)

_SYNC_FORMAT_RULE_TF = (
    'Return ONLY a raw JSON object — no markdown, no text outside JSON:\n'
    '{"title":"...","description":"...","questions":[{"question":"<the statement>","correct":true|false,"explanation":"..."}]}\n'
    'The "correct" field MUST be the JSON boolean true or false (not a string). Do not include "options".\n'
    "Start with { end with }."
)

# ─────────────────────────────────────────────────────────────────────────────
# System message
# ─────────────────────────────────────────────────────────────────────────────

_PERSONA = "QuizMaster AI — expert MCQ designer for educational assessments"
_TASK_TYPE = "Multiple-choice — variable options per question, exactly 1 correct answer"
_RULES = [
    "Each question has a required number of options (given above). One unambiguously correct answer.",
    "Distractors must be plausible but clearly wrong to anyone who read the material.",
    "Never use 'all of the above' or 'none of the above'.",
    "Cover a mix of recall, comprehension, application, and analysis.",
    "Questions and answers must come from the document content — never invent facts.",
    "Options should be similar in length to avoid length-bias clues.",
]

_TASK_TYPE_MULTI = "Multiple-select — variable options per question, 1 to N correct answers"
_RULES_MULTI = [
    "Each question has a required number of options (given above). Any number of them can be correct — decide per question.",
    "Every option (correct or not) must be independently plausible.",
    "Never use 'all of the above' or 'none of the above'.",
    "Cover a mix of recall, comprehension, application, and analysis.",
    "Questions and answers must come from the document content — never invent facts.",
    "Options should be similar in length to avoid length-bias clues.",
]
_RULES_MULTI_FIXED_COUNT = [
    "Each question has a required number of options AND a required number of correct answers "
    "(both given above) — this required correct-answer count is fixed per question, you do not "
    "get to choose it.",
    "Every option (correct or not) must be independently plausible.",
    "Never use 'all of the above' or 'none of the above'.",
    "Cover a mix of recall, comprehension, application, and analysis.",
    "Questions and answers must come from the document content — never invent facts.",
    "Options should be similar in length to avoid length-bias clues.",
]

_TASK_TYPE_TF = "True/False — a declarative statement, exactly 1 correct answer (true or false)"
_RULES_TF = [
    "Each item is a STATEMENT (not a question) that is either entirely TRUE or entirely FALSE "
    "according to the document — phrase it as an assertion, e.g. 'X was founded in 1930.', not "
    "as a question.",
    "Mix true and false statements roughly evenly across the quiz — do not make them all true.",
    "A false statement must be plausible, not absurd — change exactly one concrete fact (a date, "
    "a name, a number, a place) from what the document actually says.",
    "Statements must be based on the document content — never invent facts.",
]

_USER_TEMPLATE = "Generate the quiz from the document below.\n\n<document>\n{content}\n</document>"


def _build_system(
    format_rule: str, option_counts: list, question_type: str = 'single_answer', correct_counts: list = None,
) -> dict:
    is_multi = question_type == 'multi_answer'
    is_tf = question_type == 'true_false'
    if is_tf:
        task_type = _TASK_TYPE_TF
        rules = _RULES_TF
    elif is_multi:
        task_type = _TASK_TYPE_MULTI
        rules = _RULES_MULTI_FIXED_COUNT if correct_counts is not None else _RULES_MULTI
    else:
        task_type = _TASK_TYPE
        rules = _RULES
    rules_text = "\n".join(f"- {r}" for r in rules)
    options_instruction = "" if is_tf else _build_option_counts_instruction(
        option_counts, correct_counts if is_multi else None,
    )
    content = (
        f"You are: {_PERSONA}\n"
        f"Language: Vietnamese ONLY. Translate all content to Vietnamese.\n"
        f"Task: {task_type}. Generate exactly {len(option_counts)} items.\n"
        f"{options_instruction}\n"
        f"Rules:\n{rules_text}\n\n"
        f"{format_rule}"
    )
    return {"role": "system", "content": content}


def _get_messages(
    content: str, option_counts: list, streaming: bool, question_type: str = 'single_answer',
    correct_counts: list = None,
) -> list:
    is_multi = question_type == 'multi_answer'
    is_tf = question_type == 'true_false'
    if is_tf:
        fmt = _NDJSON_FORMAT_RULE_TF if streaming else _SYNC_FORMAT_RULE_TF
    elif streaming:
        fmt = _NDJSON_FORMAT_RULE_MULTI if is_multi else _NDJSON_FORMAT_RULE
    else:
        fmt = _SYNC_FORMAT_RULE_MULTI if is_multi else _SYNC_FORMAT_RULE
    system = _build_system(fmt, option_counts, question_type, correct_counts)
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

    @classmethod
    def _extract_options(cls, q: dict) -> list:
        """Accept an `options` array (preferred), a legacy {"a":..,"b":..} dict,
        or legacy flat a/b/c/d/e/f/g/h keys — always returns a plain ordered list."""
        opts_raw = q.get('options')
        if isinstance(opts_raw, list):
            return [str(v) for v in opts_raw if v is not None and str(v).strip()]
        if isinstance(opts_raw, dict):
            return [str(v) for _, v in sorted(opts_raw.items()) if v]
        opts = []
        for letter in 'abcdefgh':
            v = q.get(letter) or q.get(letter.upper())
            if v:
                opts.append(str(v))
        return opts

    @classmethod
    def _normalize_correct_index(cls, raw, num_options: int) -> int:
        """Normalize a single AI 'correct' value to a valid 0-based int index,
        tolerant of legacy letter output (a/b/c/...) some models still emit
        despite the prompt asking for an index."""
        idx = 0
        if isinstance(raw, bool):
            idx = 0
        elif isinstance(raw, (int, float)):
            idx = int(raw)
        elif isinstance(raw, str):
            s = raw.strip().lower()
            if s.isdigit():
                idx = int(s)
            elif len(s) == 1 and 'a' <= s <= 'z':
                idx = ord(s) - ord('a')
        return idx if num_options and 0 <= idx < num_options else 0

    @classmethod
    def _normalize_correct_indices_multi(cls, raw, num_options: int) -> list:
        """Normalize any multi-answer shape (list, or comma/space-separated string) to a
        sorted, deduped list of valid indices, e.g. [0, 2]."""
        if raw is None:
            return []
        if isinstance(raw, str):
            parts = re.split(r'[,\s/]+', raw)
        elif isinstance(raw, (list, tuple, set)):
            parts = list(raw)
        else:
            parts = [raw]
        indices = {
            cls._normalize_correct_index(p, num_options)
            for p in parts if p is not None and str(p).strip() != ''
        }
        return sorted(indices)

    @staticmethod
    def _normalize_bool(raw) -> bool:
        """Normalize an AI 'correct' value for a true/false statement to a Python bool.
        Tolerant of JSON booleans, 0/1, and Vietnamese/English yes-no words."""
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            s = raw.strip().lower()
            return s in ('true', 'đúng', 'dung', 'yes', 'y', '1', 'correct')
        return False

    @staticmethod
    def _fit_correct_count(correct: list, required: int, num_options: int) -> list:
        """Force `correct` to have exactly `required` entries — the AI's own correct-answer
        count is only a hint, `correct_counts` from the caller is authoritative. Truncates
        when the AI over-supplied; pads with the lowest-index unused options when it
        under-supplied (small local models very often just return a single correct answer
        regardless of what was asked for)."""
        correct = sorted(set(correct))
        if len(correct) > required:
            return correct[:required]
        if len(correct) < required:
            for i in range(num_options):
                if len(correct) >= required:
                    break
                if i not in correct:
                    correct.append(i)
            correct.sort()
        return correct

    @classmethod
    def _parse_quiz_payload(
        cls, raw: str, option_counts: list, question_type: str = 'single_answer', correct_counts: list = None,
    ) -> dict:
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

        is_tf = question_type == 'true_false'
        num_questions = len(option_counts)
        valid = []
        for q in raw_questions:
            if not isinstance(q, dict):
                continue

            if is_tf:
                question_text = (q.get('question') or q.get('q') or '').strip()
                if not question_text:
                    continue
                correct_key = next((k for k in ('correct', 'answer', 'ans') if k in q), None)
                is_true = cls._normalize_bool(q.get(correct_key)) if correct_key else True
                explanation = (q.get('explanation') or q.get('why') or '').strip()
                valid.append({
                    'question': question_text,
                    'options': list(_TF_OPTIONS),
                    'correct': 0 if is_true else 1,
                    'explanation': explanation,
                })
                if len(valid) >= num_questions:
                    break
                continue

            expected_count = option_counts[len(valid)] if len(valid) < len(option_counts) else option_counts[-1]

            opts = cls._extract_options(q)
            if len(opts) < QuizQuestion.MIN_OPTIONS:
                continue
            if len(opts) > expected_count:
                opts = opts[:expected_count]

            question_text = (q.get('question') or q.get('q') or '').strip()
            if not question_text:
                continue

            correct_raw = q.get('correct') or q.get('answer') or q.get('ans')

            if question_type == 'multi_answer':
                correct = cls._normalize_correct_indices_multi(correct_raw, len(opts))
                if len(correct) < 1:
                    continue
                if correct_counts is not None:
                    required = correct_counts[len(valid)] if len(valid) < len(correct_counts) else correct_counts[-1]
                    correct = cls._fit_correct_count(correct, required, len(opts))
            else:
                correct = cls._normalize_correct_index(correct_raw, len(opts))

            explanation = (q.get('explanation') or q.get('why') or '').strip()

            valid.append({
                'question': question_text,
                'options': opts,
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
        content: str,
        num_questions: int = 5,
        question_type: str = 'single_answer',
        num_options: int = _DEFAULT_NUM_OPTIONS,
        option_counts: list = None,
        correct_counts: list = None,
    ) -> dict:
        if not content:
            raise ValueError("Provide 'content'")
        content = content[:_MAX_CONTENT_LENGTH]
        if question_type == 'true_false':
            option_counts = [2] * max(1, int(num_questions if not option_counts else len(option_counts)))
            correct_counts = None
        else:
            option_counts = _normalize_option_counts(option_counts, num_questions, num_options)
            correct_counts = _normalize_correct_counts(correct_counts, option_counts) if question_type == 'multi_answer' else None

        messages = _get_messages(
            content, option_counts, streaming=False, question_type=question_type, correct_counts=correct_counts,
        )

        def validator(raw: str) -> bool:
            try:
                parsed = cls._parse_quiz_payload(
                    raw, option_counts, question_type=question_type, correct_counts=correct_counts,
                )
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
            return cls._parse_quiz_payload(raw, option_counts, question_type=question_type, correct_counts=correct_counts)
        except ValueError:
            logger.error("[QuizGen] Final parse failed. Raw AI output:\n%s", raw)
            raise

    @classmethod
    def generate_stream(
        cls,
        content: str,
        num_questions: int = 5,
        question_type: str = 'single_answer',
        num_options: int = _DEFAULT_NUM_OPTIONS,
        option_counts: list = None,
        correct_counts: list = None,
    ):
        """
        Generator that yields dicts as the AI produces them.

        First yield:  {"type": "meta",     "title": "...", "description": "..."}
        Subsequent:   {"type": "question",  "index": 0,    "question": "...", ...}
        Final yield:  {"type": "done",      "total": N}
        On error:     {"type": "error",     "detail": "..."}
        """
        try:
            if not content:
                raise ValueError("Provide 'content'")
            content = content[:_MAX_CONTENT_LENGTH]
        except Exception as exc:
            yield {"type": "error", "detail": str(exc)}
            return

        if question_type == 'true_false':
            option_counts = [2] * max(1, int(num_questions if not option_counts else len(option_counts)))
            correct_counts = None
        else:
            option_counts = _normalize_option_counts(option_counts, num_questions, num_options)
            correct_counts = _normalize_correct_counts(correct_counts, option_counts) if question_type == 'multi_answer' else None
        messages = _get_messages(
            content, option_counts, streaming=True, question_type=question_type, correct_counts=correct_counts,
        )

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
            if question_index >= len(option_counts):
                break
            q = obj

            if question_type == 'true_false':
                question_text = (q.get('question') or q.get('q', '') or '').strip()
                if not question_text:
                    continue
                correct_key = next((k for k in ('correct', 'answer', 'ans') if k in q), None)
                is_true = cls._normalize_bool(q.get(correct_key)) if correct_key else True
                opts = list(_TF_OPTIONS)
                correct = 0 if is_true else 1
                explanation = q.get('explanation') or q.get('why', '') or ''
                yield {
                    "type": "question",
                    "index": question_index,
                    "question": question_text,
                    "options": opts,
                    "correct": correct,
                    "explanation": explanation,
                }
                question_index += 1
                continue

            expected_count = option_counts[question_index]

            opts = cls._extract_options(q)
            if len(opts) > expected_count:
                opts = opts[:expected_count]

            question_text = (q.get('question') or q.get('q', '') or '').strip()
            correct_raw = q.get('correct') or q.get('ans')
            if question_type == 'multi_answer':
                correct = cls._normalize_correct_indices_multi(correct_raw, len(opts))
                if correct_counts is not None and correct:
                    correct = cls._fit_correct_count(correct, correct_counts[question_index], len(opts))
            else:
                correct = cls._normalize_correct_index(correct_raw, len(opts))
            explanation = q.get('explanation') or q.get('why', '') or ''

            if not question_text:
                continue
            if len(opts) < QuizQuestion.MIN_OPTIONS:
                continue
            if question_type == 'multi_answer' and len(correct) < 1:
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
