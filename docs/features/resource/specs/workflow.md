# Resource Module — Workflows

---

## 1. File Upload

### Actors
- **User** (Consumer or Space)
- **Platform**
- **Cloudflare R2**

### Preconditions
- User is authenticated.

### Steps
1. User submits a `multipart/form-data` POST to `/api/v1/resource/upload/`.
2. Platform validates the file (present, within size limits).
3. Platform generates an object key (e.g., `uploads/<uid>/<filename>`).
4. Platform calls `StorageService.upload_fileobj()` which pushes the file to R2.
5. R2 returns success; `StorageService` constructs the public CDN URL.
6. Platform creates a `Resource` record with `owner_id`, `owner_type`, `url`, `name`, `file_type`, `size`.
7. Resource record is returned to the client including `uid` for future reference.

### Edge Cases
- **R2 not configured**: `StorageService` falls back to `save_local()`; URL points to `MEDIA_URL`.
- **File too large**: Rejected before upload with a size validation error.
- **Upload error from R2**: Returns 500 with an error message; no Resource record is created.

---

## 2. List Own Resources

### Actors
- **User**
- **Platform**

### Steps
1. User sends GET to `/api/v1/resource/`.
2. Platform filters `resource_resources` where `owner_id = request.user.uid` and `is_deleted = False`.
3. Results are returned, newest first.

---

## 3. Get Resource Detail

### Actors
- **User or Other Module**

### Steps
1. Caller provides `resource_uid`.
2. Platform fetches the `Resource` record by primary key (bucket + uid).
3. Record is returned.

### Edge Cases
- **Resource not found**: Returns 404.
- **Resource belongs to different owner**: Returns 403 (if owner check is enforced by the caller).

---

## 4. Soft Delete Resource

### Actors
- **User (owner)**
- **Platform**

### Steps
1. User sends DELETE to `/api/v1/resource/<uid>/`.
2. Platform verifies ownership (`owner_id = request.user.uid`).
3. Platform sets `is_deleted = True` and `deleted_at = now()`.
4. Resource no longer appears in list queries.

### Edge Cases
- **Non-owner delete attempt**: Returns 403.
- **File in use by another module**: Soft delete proceeds; the consuming module (Exam, Chat) retains the cached URL and still renders the file.
