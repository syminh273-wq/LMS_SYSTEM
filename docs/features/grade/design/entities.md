# Grade Module - Entities

## Grade

**Table**: `course_grades`

| Column | Type | Description |
|---|---|---|
| `bucket` | Integer | Partition key, default `0` |
| `uid` | UUID v7 | Clustering key DESC and grade identifier |
| `submission_id` | UUID | Indexed exam submission reference |
| `exam_id` | UUID | Indexed exam reference |
| `classroom_id` | UUID | Indexed classroom reference |
| `student_id` | UUID | Indexed consumer reference |
| `grader_role` | Text | `ai` or `teacher` |
| `grader_id` | UUID | Teacher ID; empty for AI |
| `score` | Float | Awarded or proposed score |
| `max_score` | Float | Maximum score for this record |
| `feedback` | Text | Grading feedback |
| `status` | Text | `suggested` or `final` |
| `ai_model` | Text | AI model fallback configuration for AI records |
| `created_at`, `updated_at` | DateTime | Audit timestamps |
| `is_deleted`, `deleted_at` | Boolean, DateTime | Soft deletion state |
