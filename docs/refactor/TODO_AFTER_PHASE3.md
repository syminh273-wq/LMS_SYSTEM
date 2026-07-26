# TODO — Phase 3+ refactor follow-up

> **Status**: Phase 1, 2, 3 đã commit. Django check pass, schema sync OK.
> Schema giảm: **56 → 49 bảng**.
>
> Những việc dưới đây là **cần làm sau** để hoàn thiện refactor.

---

## 1. Refactor `consumer_posts` table name

Hiện tại `social_posts` đã tạo nhưng bảng cũ `consumer_posts` đã drop. Code đã tham chiếu `SocialPost` (class) → `social_posts` (table). **OK**.

Nhưng cần check kỹ:

- [ ] Nếu có Bruno test / Postman collection tham chiếu `consumer_posts` → đổi sang `social_posts`
- [ ] Update docs: `docs/features/social/`, `docs/refactoring/2026-07-27-rescan-report.md`

---

## 2. Re-implement `PublicCourseViewSet`

`/api/v1/public/course/preview/<code>/` đã bị comment-out vì Phase 3 xóa `course_courses`.

Cần làm:

- [ ] Re-implement endpoint này dựa trên `account_classrooms` (vì logic thực tế chỉ dùng classroom) — tạo `PublicClassroomPreviewView` thay thế
- [ ] Bỏ comment dòng trong `LMS_SYSTEM/urls.py`
- [ ] Cập nhật bruno test (nếu có)

---

## 3. `CourseEnrollmentService` API changes

Cũ: nhận `course` object + `course_service.ensure_classroom(course)`.
Mới: chỉ làm ledger (insert row), không tạo classroom.

Code cũ đang gọi `enroll_free` / `enroll_paid` cần refactor:

- [ ] Tìm tất cả caller của `enroll_free` / `enroll_paid`
- [ ] Caller phải tự gọi `classroom_member_service` để join classroom trước, rồi gọi `record_enrollment` (method mới)
- [ ] Xoá method `enroll_free`, `enroll_paid` (giữ `record_enrollment` thôi)

```bash
grep -rn "enroll_free\|enroll_paid" features/
```

---

## 4. `quiz_collections.item_quiz_ids` migration

Khi `quiz_collection_items` bị drop, các collection cũ **mất items**.

Cần:

- [ ] Viết migration script (Django management command) để copy `quiz_id` từ bảng cũ → `item_quiz_ids` list trong `quiz_collections`
- [ ] Nếu data cũ quan trọng → backup trước khi drop

```python
# Pseudo-code
for item in old_quiz_collection_items:
    collection = QuizCollection.get(item.collection_id)
    if collection and item.quiz_id not in collection.item_quiz_ids:
        collection.item_quiz_ids.append(item.quiz_id)
        collection.save()
```

---

## 5. `course_blacklists` migration

Bảng cũ `course_classroom_blacklists` + `course_teacher_global_blacklists` bị drop, bảng mới `course_blacklists` dùng sentinel UUID cho global block.

Cần:

- [ ] Migration script copy dữ liệu từ 2 bảng cũ → `course_blacklists`
  - `course_classroom_blacklists` row → `(teacher_id=classroom.teacher_id, classroom_uid=classroom_uid, consumer_uid=...)`
  - `course_teacher_global_blacklists` row → `(teacher_id=..., classroom_uid=GLOBAL_SENTINEL, consumer_uid=...)`
- [ ] Backfill `teacher_id` cho `course_classroom_blacklists` rows (cần join với `account_classrooms.teacher_id`)

---

## 6. `social_post_likes` / `social_post_comments` migration

- [ ] Migration script copy `post_likes` → `social_post_likes` (đổi tên `consumer_uid` → `owner_id`, thêm `owner_type='consumer'`)
- [ ] Migration script copy `post_comments` → `social_post_comments`
- [ ] Migration script copy `user_follows` → `social_follows` (thêm `follower_type`, `followed_type='consumer'`)

Cảnh báo: nếu user đã có `follower_type='space'` (rất hiếm), cần detect trước khi migrate.

---

## 7. `course_teacher_contacts` schema migration

Bảng giữ nguyên tên, chỉ thêm 4 field mới: `last_contact_at`, `last_contact_type`, `last_contact_ref_id`, `contact_count`.

Cần:

- [ ] Migration script backfill: với row hiện tại → set `last_contact_at = first_joined_at`, `last_contact_type = 'joined'`, `contact_count = 1`
- [ ] Hook vào các flow hiện tại để gọi `record_contact()` khi:
  - HV mới join classroom (đã có trong `classroom_member_service._register_teacher_contact`)
  - HV gửi message cho teacher (chat module)
  - Teacher reply (chat module)
  - HV submit bài (exam module)

---

## 8. `social` module cleanup

Refactor đã làm:

- `ConsumerPost` → `SocialPost` ✅
- `PostLike` → `SocialPostLike` ✅
- `PostComment` → `SocialPostComment` ✅
- `UserFollow` → `SocialFollow` ✅
- `UserProfile` → `SocialProfile` ✅ (table giữ tên `user_profiles`)

Cần verify:

- [ ] `show_urls` liệt kê đúng tất cả routes
- [ ] Bruno tests (nếu có) dùng `consumer_uid` → đổi sang `owner_id`
- [ ] Frontend gọi API social đang dùng `consumer_uid` → đổi sang `owner_id`

```bash
grep -rn "consumer_uid" features/social/
```

---

## 9. Update AGENTS.md

Schema overview trong AGENTS.md cần update:

- [ ] Bỏ `core_social_accounts` (nếu xóa) — đã giữ
- [ ] Bỏ `course_courses`, `course_lessons`, `quiz_collection_items`, `course_classroom_blacklists`, `course_teacher_global_blacklists`
- [ ] Bỏ `resource_doc_notes`, `resource_doc_reading_progress`, `ranking_xp_rules`
- [ ] Thêm `course_blacklists`, `social_posts`, `social_post_likes`, `social_post_comments`, `social_follows`
- [ ] Update module structure tree (xóa `features/course/course/`, `features/course/lesson/`, thêm `social_*`)

---

## 10. Update docs/features

Mỗi module bị ảnh hưởng cần update docs:

- [ ] `docs/features/portfolio/` — thêm field `metadata`
- [ ] `docs/features/quiz_collection/` — bỏ `QuizCollectionItem`, document `item_quiz_ids`
- [ ] `docs/features/course/classroom/` — bỏ `ClassroomBlacklist` + `TeacherGlobalBlacklist`, thêm `TeacherBlacklist`
- [ ] `docs/features/course/teacher_contact/` — thêm field history
- [ ] `docs/features/social/` — refactor owner-based
- [ ] `docs/features/course/course/` — **XÓA folder** (đã không còn code)
- [ ] `docs/features/course/lesson/` — **XÓA folder**

---

## 11. Typesense search indexer

`core/search_engine/typesense/indexer.py` có mapping cũ:

```python
'TeacherContact': ('lms_teacher_contact', _teacher_contact_doc),
```

Cần verify:

- [ ] Nếu code dùng `consumer_uid` / `consumer_name` → đổi sang `owner_id` / `owner_name`
- [ ] Reindex Typesense sau khi schema thay đổi (nếu có data cũ)

---

## 12. WebSocket consumers

`core/ws/` có thể tham chiếu `ConsumerPost`, `PostComment` etc.:

- [ ] Check: `grep -rn "ConsumerPost\|PostComment\|UserFollow\|UserProfile" core/ws/`
- [ ] Refactor sang `SocialPost`, `SocialPostComment`, `SocialFollow`, `SocialProfile`

---

## 13. Test (nếu có)

- [ ] Chạy test suite hiện có (pytest / Django test)
- [ ] Bruno collection: update URL + body
- [ ] Smoke test thủ công các flow chính:
  - Login (consumer + space)
  - Tạo classroom
  - Join classroom
  - Post bài + like + comment
  - Follow user
  - Tạo quiz + collection
  - Assign quiz cho classroom
  - Submit quiz → check certificate
  - Blacklist HV
  - Upload resource

---

## 14. Production migration order (nếu deploy lên env thật)

```
1. Backup Cassandra: cqlsh -e "DESC KEYSPACE lms_keyspace" > backup_$(date).cql
2. Run migration scripts (TODO #4, #5, #6, #7)
3. Deploy code mới
4. Run `python manage.py lms_sync_cassandra` (sẽ tạo schema mới + bỏ qua bảng cũ)
5. Run `python drop_legacy_tables.py` (sẽ xóa bảng cũ)
6. Verify `python manage.py show_urls`
7. Smoke test
```

---

## Quick reference — Files changed

```
Phase 1:
  + features/portfolio/metadata column
  - resource_doc_notes
  - resource_doc_reading_progress
  - ranking_xp_rules
  - 6 endpoint doc_*
  + features/ranking/constants.py

Phase 2:
  - course_classroom_blacklists
  - course_teacher_global_blacklists
  + course_blacklists (GLOBAL_SENTINEL)
  - quiz_collection_items
  + quiz_collections.item_quiz_ids list<uuid>
  + course_teacher_contacts: +last_contact_at, +last_contact_type,
    +last_contact_ref_id, +contact_count
  + features/course/classroom/repositories/teacher_blacklist_repository.py

Phase 3:
  - course_courses
  - course_lessons
  - features/course/{course,lesson}/
  - consumer_posts → +social_posts
  - post_comments → +social_post_comments
  - post_likes → +social_post_likes
  - user_follows → +social_follows
  - consumer_uid → owner_id + owner_type (4 bảng social)
  - LMS_SYSTEM/urls.py: comment out PublicCourseViewSet
```
