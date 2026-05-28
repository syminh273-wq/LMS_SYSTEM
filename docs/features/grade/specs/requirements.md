# Grade Module - Requirements

| ID | Requirement |
|---|---|
| GR-BR-01 | Each official exam result is decided by the teacher who owns the exam. |
| GR-FR-01 | The teacher can request an AI grading suggestion for a markdown submission. |
| GR-FR-02 | The teacher can grade directly or use an AI suggestion as initial values. |
| GR-FR-03 | The teacher can list grading records for a submission. |
| GR-FR-04 | Official grading updates the related `ExamSubmission`. |
| GR-FR-05 | Resubmission soft-deletes prior grading records for that submission. |
| GR-FR-06 | Official scores must be between `0` and the related exam's `max_score`. |
| GR-NFR-01 | Grade records use soft deletion and Cassandra repository access only. |
| GR-NFR-02 | AI failures do not publish or overwrite an official grade. |
