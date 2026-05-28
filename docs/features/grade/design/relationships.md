# Grade Module - Relationships

```text
ExamSubmission 1 -> many Grade
Exam           1 -> many Grade
Classroom      1 -> many Grade
Consumer       1 -> many Grade
Space          1 -> many Grade (teacher records only)
```

All relationships are stored as UUID values. A teacher grade is copied to the
related `ExamSubmission` as its current official grade. AI records are
suggestions and are not visible through the official submission score unless
a teacher later approves them.
