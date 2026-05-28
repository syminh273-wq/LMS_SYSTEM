# Grade Module - Traceability

| Requirement | Component | Endpoint |
|---|---|---|
| GR-FR-01 | `GradeService.ai_grade_submission` | `POST /api/v1/space/course/grades/submissions/<uid>/ai/` |
| GR-FR-02, GR-FR-04 | `GradeService.teacher_grade_submission` | `PATCH /api/v1/space/course/grades/submissions/<uid>/teacher/` |
| GR-FR-06 | `GradeService.teacher_grade_submission` | `PATCH /api/v1/space/course/exams/submissions/<uid>/grade/` and teacher-grade endpoint |
| GR-FR-03 | `GradeRepository.list_by_submission` | `GET /api/v1/space/course/grades/submissions/<uid>/` |
| GR-FR-05 | `GradeRepository.soft_delete_by_submission` | Exam submission replacement flow |
