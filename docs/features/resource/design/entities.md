# Resource Module — Entities

---

## 1. Resource

**Purpose**: Tracks a file uploaded to R2 storage. Acts as the single source of truth for all file assets on the platform.

**Table**: `resource_resources`

| Column | Type | Key | Description |
|---|---|---|---|
| `bucket` | Integer | Partition key | Distribution bucket (default `0`) |
| `uid` | UUID v7 | Clustering key DESC | Time-ordered resource identifier |
| `name` | Text | — | Original filename *(required)* |
| `file_type` | Text | Indexed | File extension: `pdf`, `jpg`, `mp4`, `docx`, etc. |
| `url` | Text | — | Public CDN URL *(required)* |
| `size` | BigInt | — | File size in bytes |
| `owner_id` | UUID | Indexed | References `Consumer.uid` or `Space.uid` |
| `owner_type` | Text | Indexed | `consumer` \| `space` |
| `metadata` | Map<Text, Text> | — | Arbitrary key-value pairs |
| `created_at` | DateTime | — | |
| `updated_at` | DateTime | — | |
| `is_deleted` | Boolean | — | Soft delete flag |
| `deleted_at` | DateTime | — | |

---

## 2. StorageService (Infrastructure)

**Purpose**: Abstracts file storage. Not a Cassandra entity — an application service class in `core/storages/storage_service.py`.

| Method | Description |
|---|---|
| `upload_fileobj(file, key, is_public)` | Upload to R2; returns `{success, url, object_key}` |
| `get_public_url(object_key)` | Constructs CDN URL from `R2_PUBLIC_DOMAIN` |
| `delete_object(key)` | Remove file from R2 |
| `save_local(file, key)` | Fallback: save to `MEDIA_ROOT` |
| `check_connection()` | Health check for R2 connectivity |
