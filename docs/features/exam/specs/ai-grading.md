# Exam AI Grading Spec

## Purpose

Teachers can ask AI to grade submitted exam work using the exam prompt, the student's submission, an optional teacher rubric, and indexed classroom documents.

## Scope

- Grade one submitted exam answer.
- Grade all submissions for one exam.
- Grade all exam submissions in one classroom.
- Persist the final score on `course_exam_submissions.grade`.
- Mark AI-generated grading metadata on the same submission row.

## Cassandra Table

Existing table: `course_exam_submissions`

New columns:

| Column | Type | Description |
|---|---|---|
| `grading_method` | Text | `manual` or `ai` |
| `ai_model` | Text | AI backend/model fallback list used |
| `ai_rubric` | Text | Teacher-provided rubric |
| `ai_reason` | Text | Overall grading reason |
| `ai_breakdown` | Text | JSON list of per-question grading reasons |
| `ai_sources` | Text | JSON list of classroom document sources |
| `ai_confidence` | Float | AI confidence from `0` to `1` |

Schema sync required:

```bash
python manage.py sync_cassandra
```

## API

### Grade one submission

`POST /api/v1/space/course/exams/submissions/<submission_uid>/ai-grade/`

### Grade all submissions in one exam

`POST /api/v1/space/course/exams/<exam_uid>/submissions/ai-grade/`

### Grade all submissions in one classroom

`POST /api/v1/space/course/classrooms/<classroom_uid>/exams/ai-grade/`

Request body:

```json
{
  "rubric": "Chấm theo thang điểm 10, ưu tiên đúng ý và dẫn chứng từ tài liệu.",
  "max_grade": 10,
  "overwrite": false,
  "top_k": 5
}
```

## Business Rules

- Only the teacher who owns the exam can AI-grade its submissions.
- If `overwrite=false`, already graded submissions are skipped.
- AI grading updates `grade`, `feedback`, `graded_by`, `graded_at`, `status=graded`, and `grading_method=ai`.
- Manual grading later sets `grading_method=manual`.
- File submissions are graded only when readable text can be extracted from markdown, PDF, TXT, or MD content.
- Classroom documents are retrieved from the RAG index using `classroom_id`.

## Response Notes

Submission responses include:

- `grading_method`
- `ai_reason`
- `ai_breakdown`
- `ai_sources`
- `ai_confidence`

Batch responses include total, graded count, failed count, and per-submission errors.
