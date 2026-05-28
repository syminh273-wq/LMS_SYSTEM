# Exam Module — Entities

---

## 1. Exam

**Purpose**: Represents teacher-published work inside a classroom. An exam can be markdown content or a file-backed resource.

**Table**: `course_exams`

| Column | Type | Key | Description |
|---|---|---|---|
| `bucket` | Integer | Partition key | Distribution bucket, default `0` |
| `uid` | UUID v7 | Clustering key DESC | Exam identifier |
| `classroom_id` | UUID | Indexed | Classroom that owns the exam |
| `teacher_id` | UUID | Indexed | Space account that created the exam |
| `title` | Text | — | Exam title |
| `description` | Text | — | Optional instructions |
| `content_type` | Text | — | `markdown` \| `pdf` \| `image` \| `file` |
| `content` | Text | — | Markdown body when `content_type=markdown` |
| `resource_uid` | UUID | — | Referenced resource for file-backed exams |
| `resource_url` | Text | — | Cached resource URL |
| `resource_name` | Text | — | Cached resource display name |
| `status` | Text | — | `draft` \| `published` \| `closed` |
| `due_date` | DateTime | — | Optional due date |
| `created_at` | DateTime | — | Creation timestamp |
| `updated_at` | DateTime | — | Update timestamp |
| `is_deleted` | Boolean | — | Soft delete flag |
| `deleted_at` | DateTime | — | Soft delete timestamp |

---

## 2. ExamSubmission

**Purpose**: Records one active student submission for an exam, including file or markdown content and teacher grading metadata.

**Table**: `course_exam_submissions`

| Column | Type | Key | Description |
|---|---|---|---|
| `bucket` | Integer | Partition key | Distribution bucket, default `0` |
| `uid` | UUID v7 | Clustering key DESC | Submission identifier |
| `exam_id` | UUID | Indexed | Referenced exam |
| `classroom_id` | UUID | Indexed | Denormalized classroom ID from exam |
| `student_id` | UUID | Indexed | Consumer account that submitted |
| `content_type` | Text | — | `markdown` \| `pdf` \| `image` \| `file` |
| `content` | Text | — | Markdown answer when `content_type=markdown` |
| `resource_uid` | UUID | — | Referenced uploaded file for file submissions |
| `resource_url` | Text | — | Cached resource URL |
| `resource_name` | Text | — | Cached resource display name |
| `status` | Text | — | `submitted` \| `late` \| `graded` \| `returned` |
| `submitted_at` | DateTime | — | Submission timestamp |
| `grade` | Float | — | Teacher-assigned grade |
| `feedback` | Text | — | Teacher feedback |
| `graded_by` | UUID | — | Space account that graded |
| `graded_at` | DateTime | — | Grading timestamp |
| `grading_method` | Text | — | `manual` \| `ai` |
| `ai_model` | Text | — | AI backend/model used for grading |
| `ai_rubric` | Text | — | Teacher-provided grading rubric |
| `ai_reason` | Text | — | Overall AI grading reason |
| `ai_breakdown` | Text | — | JSON list of per-question score reasons |
| `ai_sources` | Text | — | JSON list of classroom document sources |
| `ai_confidence` | Float | — | AI confidence score from `0` to `1` |
| `created_at` | DateTime | — | Creation timestamp |
| `updated_at` | DateTime | — | Update timestamp |
| `is_deleted` | Boolean | — | Soft delete flag |
| `deleted_at` | DateTime | — | Soft delete timestamp |

**Design Notes**:
- The first version allows one active submission per `(exam_id, student_id)`.
- Late submissions are accepted and marked with `status=late`.
- Resource display fields are denormalized to avoid extra reads when listing submissions.
