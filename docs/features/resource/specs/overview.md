# Resource Module — Overview

## Purpose

The Resource module manages file uploads and tracks uploaded assets per owner. It acts as the central file registry for the LMS platform — any module that needs to attach a file (exams, chat messages) references a resource record rather than uploading independently.

## Business Context

Both teachers and students can upload files. Files are stored in Cloudflare R2 (S3-compatible object storage). A `Resource` record is created in Cassandra after each successful upload, capturing the file URL, type, size, and owner. This allows other modules to reference files by `resource_uid` without re-uploading.

## Key Capabilities

### 1. File Upload to Cloudflare R2
Files are uploaded via multipart form data. The platform stores them in R2 and returns a public URL. In development, files fall back to local media storage.

### 2. Dual Bucket Strategy
Two R2 buckets are maintained: a public bucket (for images and shared documents) and a private bucket (for sensitive files). The bucket is selected at upload time.

### 3. Owner-Scoped Access
Resources are scoped to their owner (`owner_id` + `owner_type`). A Consumer owns files they upload; a Space owns files they upload. Resources are not shared between owners unless explicitly referenced.

### 4. File Type Tracking
Each resource records its `file_type` (e.g., `pdf`, `jpg`, `mp4`). This allows consumers of the resource to render appropriate UI (preview, download, player).

### 5. Flexible Metadata
An optional `metadata` map stores arbitrary key-value pairs (e.g., image dimensions, video duration) without requiring schema changes.

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Teachers (Space) | Upload exam files, course materials |
| Students (Consumer) | Upload assignment submissions, profile avatars |
| Other modules (Exam, Chat) | Reference uploaded files via `resource_uid` |
