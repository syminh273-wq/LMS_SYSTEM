# Grade Module - Workflow

## AI Suggestion

1. The teacher requests AI grading for a submission they own.
2. The service validates that the submission contains markdown text.
3. OmniRoute receives the exam prompt, optional rubric, and student answer.
4. A `suggested` grade record with `grader_role=ai` is stored.
5. The submission remains unchanged until the teacher grades it.

## Teacher Grade

1. The teacher submits a score and feedback, optionally identifying an AI
   suggestion.
2. When fields are omitted, values may be copied from that AI suggestion.
3. The score is rejected unless it is within `0` and `Exam.max_score`.
4. A `final` record with `grader_role=teacher` is stored.
5. The submission's official `grade`, `feedback`, `graded_by`, `graded_at`,
   and `status=graded` fields are updated.

## Resubmission

When a student replaces a submission, its old official score is cleared and
all grade records for the reused submission identifier are soft-deleted.
