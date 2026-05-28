# Exam Module — Entity Relationships

## Relationship Map

```
Space
  └── Exam.teacher_id

Classroom
  ├── Exam.classroom_id
  └── ExamSubmission.classroom_id

Consumer
  └── ExamSubmission.student_id

Resource
  ├── Exam.resource_uid
  └── ExamSubmission.resource_uid

ExamSubmission
  └── Grade.submission_id
```

---

## Detailed Relationships

### Space → Exam

**Type**: One-to-Many

**Business Meaning**: A teacher creates exams for classrooms they manage. The exam stores `teacher_id` as a plain UUID reference to the Space account.

### Classroom → Exam

**Type**: One-to-Many

**Business Meaning**: Exams belong to a classroom. Students can only submit to published exams in classrooms where they are members.

### Exam → ExamSubmission

**Type**: One-to-Many

**Business Meaning**: Each exam can have many student submissions. The v1 service allows one active submission per student per exam.

### Consumer → ExamSubmission

**Type**: One-to-Many

**Business Meaning**: A student submits markdown or file-backed work for a published exam.

### Resource → ExamSubmission

**Type**: One-to-One per file submission

**Business Meaning**: File submissions reference an uploaded resource and cache `resource_url` and `resource_name` for list/detail responses.

### ExamSubmission → Grade

**Type**: One-to-Many

**Business Meaning**: A submission can receive AI suggestions and teacher grading records. Only a teacher-finalized grade is copied onto the submission as the official result.
