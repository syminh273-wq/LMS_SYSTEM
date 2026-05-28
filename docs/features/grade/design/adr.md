# Grade Module - Architecture Decisions

## ADR-001: Separate Grade History From Official Submission Fields

**Decision**: Store each AI or teacher grading action in `course_grades` while
retaining final score fields on `ExamSubmission`.

**Reason**: Existing clients already consume grade data from submissions. A
separate history table distinguishes AI suggestions from final teacher
decisions without breaking that response contract.

## ADR-002: AI Suggestions Require Teacher Finalization

**Decision**: AI creates only `suggested` records and does not modify the
submission.

**Reason**: A teacher remains responsible for the published assessment result.

## ADR-003: Initial AI Input Is Markdown Only

**Decision**: Reject AI grading of file-backed submissions in this release.

**Reason**: Reliable extraction and OCR are separate concerns; accepting those
formats without validated extraction would make scores inconsistent.
