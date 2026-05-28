# Grade Module - Overview

## Purpose

The grade module records assessment results for exam submissions through two
grading roles:

- AI produces a suggested score and feedback for teacher review.
- A teacher submits the final score and feedback exposed through the exam
  submission.

AI output never becomes an official student grade without a teacher action.

## Scope

- Record grading history for an exam submission.
- Generate AI suggestions for markdown submissions.
- Let the exam owner enter a grade or approve/edit an AI suggestion.
- Preserve the current `ExamSubmission.grade` fields as the official result.
