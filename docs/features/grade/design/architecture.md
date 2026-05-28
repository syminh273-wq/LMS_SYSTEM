# Grade Module - Architecture

## Components

```text
GradeViewSet -> GradeService -> GradeRepository -> Grade
                              -> ExamRepository
                              -> ExamSubmissionRepository
                              -> OmniRouteClient (AI request only)
```

The service checks exam ownership before reading or writing grade history.
Only teacher grading updates `ExamSubmission`; AI grading stores a suggestion.
Final scores are bounded by `Exam.max_score`, not a maximum supplied by the
grading request.

## Routes

| Method | Space Endpoint | Result |
|---|---|---|
| POST | `/api/v1/space/course/grades/submissions/<uid>/ai/` | AI suggestion |
| PATCH | `/api/v1/space/course/grades/submissions/<uid>/teacher/` | Official grade |
| GET | `/api/v1/space/course/grades/submissions/<uid>/` | Grade history |

The existing `PATCH /api/v1/space/course/exams/submissions/<uid>/grade/`
endpoint remains compatible and uses the teacher grading service. Its
submission response exposes `score` as an alias of the existing official
`grade` field.
