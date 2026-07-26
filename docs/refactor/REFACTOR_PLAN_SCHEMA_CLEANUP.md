# LMS Backend — Refactor Plan: Schema Cleanup & Generic Social

> **Ngày tạo:** 2026-07-27
> **Trạng thái:** DRAFT — chờ user confirm
> **Phạm vi:** 13 thay đổi lớn trên 56 tables hiện tại

---

## Tổng quan thay đổi

| # | Hành động | Tables liên quan | Rủi ro |
|---|-----------|------------------|--------|
| 1 | Xóa bảng + thêm metadata vào `portfolios` | `core_social_accounts` | Thấp |
| 2 | Xóa bảng `course_courses` | `course_courses` + dependents | Cao (cần audit code) |
| 3 | Xóa bảng `course_lessons` | `course_lessons` | Cao (cần audit code) |
| 4 | Gom 2 bảng blacklist thành 1 | `course_classroom_blacklists` + `course_teacher_global_blacklists` | Trung bình |
| 5 | Nhúng items vào `quiz_collections`, xóa `quiz_collection_items` | `quiz_collections` + `quiz_collection_items` | Trung bình |
| 6 | Xóa `resource_doc_notes` | `resource_doc_notes` | Thấp |
| 7 | Xóa `resource_doc_reading_progress` | `resource_doc_reading_progress` | Thấp |
| 8 | Refactor social: bỏ `consumer_` prefix, dùng `owner_id` chung | `consumer_posts`, `post_comments`, `post_likes`, `user_follows`, `user_profiles` | Cao (breaking) |
| 9 | Xóa `ranking_xp_rules` (hardcode) | `ranking_xp_rules` | Thấp |
| 10 | Refactor `course_teacher_contacts` thành bảng lịch sử | `course_teacher_contacts` | Trung bình |
| 11 | Sync Cassandra schema | tất cả | Bắt buộc |
| 12 | Cập nhật code (model/repo/service/view) | toàn bộ backend | Bắt buộc |
| 13 | Cập nhật docs + tests | docs/features | Bắt buộc |

---

## 1. Xóa `core_social_accounts` & thêm metadata vào `portfolios`

### Lý do
- `core_social_accounts` lưu liên kết MXH (Google, FB...) nhưng thông tin này đã có thể nằm trong JWT/profile → không cần bảng riêng.
- `portfolios` (KV store) nên có thêm field `metadata` để chứa cấu hình linh hoạt (oauth tokens, social links, certifications...).

### Thay đổi
- [ ] **Drop table** `core_social_accounts` trong Cassandra
- [ ] **Sửa model** `portfolios`:
  - Thêm field: `metadata map<text, text>` (mặc định rỗng)
- [ ] **Migrate data cũ** (nếu có): chuyển dữ liệu `core_social_accounts` → `portfolios` với `key="social:<provider>"`, `metadata={...}`
- [ ] **Cập nhật repository** `portfolios_repository`:
  - Thêm method `get_by_owner_and_key(owner_id, owner_type, key)`
  - Update `create()` để nhận `metadata`
- [ ] **Cập nhật service** `portfolios_service`
- [ ] **Xóa** các file liên quan đến social:
  - `core/repositories/social_account_repository.py`
  - `core/services/social_account_service.py`
  - `core/viewsets/social_account_viewset.py` (nếu có)
  - URL routes liên quan
- [ ] **Grep codebase** tìm tất cả chỗ import `core_social_accounts` / `SocialAccount`
- [ ] **Update AGENTS.md** + xóa bảng khỏi tài liệu schema
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

### Schema mới `portfolios`
```
PK: (owner_id, owner_type) + CK: (uid, key)
Fields:
  - created_at, updated_at, deleted_at, is_deleted
  - display_order (int)
  - is_public (boolean)
  - value (text)
  - metadata (map<text, text>)  ← MỚI
```

---

## 2. Xóa `course_courses` (không còn sử dụng)

### Lý do
- Theo user xác nhận, bảng `course_courses` không còn được sử dụng trong code hiện tại.
- `account_classrooms` đã đóng vai trò tương đương.

### Thay đổi
- [ ] **Audit code trước khi xóa**:
  - [ ] `grep -r "course_courses\|CourseCourse\|CourseRepository" features/ core/`
  - [ ] `grep -r "from .*course" features/course/ | grep -v classroom`
  - [ ] Kiểm tra migrations / docs / tests có tham chiếu không
- [ ] **Kiểm tra `course_enrollments_by_*`**: nếu FK tới `course_courses.uid` → xử lý trước
  - Nếu enrollment đang dùng → giữ bảng hoặc chuyển FK sang `classroom_uid`
- [ ] **Drop table** `course_courses` trong Cassandra
- [ ] **Xóa files**:
  - `features/course/course/models/course.py` (nếu có)
  - `features/course/course/repositories/course_repository.py`
  - `features/course/course/services/course_service.py`
  - `features/course/course/viewsets/course_viewset.py`
  - `features/course/course/urls.py`
  - `features/course/course/` (xóa cả folder nếu rỗng)
- [ ] **Xóa app** khỏi `INSTALLED_APPS` (nếu có `apps.py`)
- [ ] **Cập nhật docs**: xóa mọi tham chiếu đến "course" trong `docs/features/`
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 3. Xóa `course_lessons`

### Lý do
- Theo user xác nhận, không còn sử dụng (cùng lý do với `course_courses`).

### Thay đổi
- [ ] **Audit code trước khi xóa**:
  - [ ] `grep -r "course_lessons\|CourseLesson" features/ core/`
  - [ ] `grep -r "lessons" features/course/`
- [ ] **Drop table** `course_lessons` trong Cassandra
- [ ] **Xóa files**:
  - `features/course/lesson/` (toàn bộ folder nếu tồn tại)
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 4. Gom 2 bảng blacklist thành 1 bảng chung

### Lý do
- `course_classroom_blacklists` (per-classroom) + `course_teacher_global_blacklists` (per-teacher) cùng mục đích, chỉ khác scope.
- Thiết kế mới: nếu có `classroom_uid` thì là per-classroom, nếu `null` thì là global (áp dụng tất cả lớp của teacher).

### Schema mới `course_blacklists`
```
PK: (teacher_id, consumer_uid) + CK: (classroom_uid, uid)  ← classroom_uid NULL = global
Fields:
  - created_at, updated_at, deleted_at, is_deleted
  - reason (text)
  - added_by (uuid)
  - scope (text)  ← "classroom" | "global"  (computed/derived, optional)
  - is_global (boolean)  ← true nếu classroom_uid IS NULL
```

**Lưu ý Cassandra**: NULL không thể làm PK/clustering key. Cần dùng workaround:
- Cách A: Tạo 2 bảng riêng (`course_classroom_blacklists` + `course_teacher_global_blacklists`) — GIỮ NGUYÊN.
- Cách B: 1 bảng với PK `(teacher_id, classroom_uid_or_sentinel, consumer_uid)`, dùng UUID `00000000-0000-0000-0000-000000000000` làm sentinel cho global.
- Cách C: 1 bảng với composite PK `(teacher_id, consumer_uid)` + thêm `classroom_uid` nullable làm regular column (mất khả năng query nhanh theo classroom).

**Khuyến nghị**: Cách C (đơn giản nhất, query theo classroom cần ALLOW FILTERING nhưng acceptable).

### Thay đổi
- [ ] **Quyết định schema cuối** với user (Cách A/B/C)
- [ ] **Audit code**: `grep -r "course_classroom_blacklists\|course_teacher_global_blacklists\|ClassroomBlacklist\|TeacherGlobalBlacklist"`
- [ ] **Tạo bảng mới** `course_blacklists` (model + repo + service)
- [ ] **Migrate data**:
  - Copy rows từ `course_classroom_blacklists` → `course_blacklists` với `classroom_uid=<giá trị>`, `is_global=false`
  - Copy rows từ `course_teacher_global_blacklists` → `course_blacklists` với `classroom_uid=null`, `is_global=true`
- [ ] **Drop 2 bảng cũ**
- [ ] **Cập nhật service logic**:
  - Add blacklist: check global trước → rồi check per-classroom
  - Query "HV có bị block khỏi lớp X không?" = `is_global=true OR classroom_uid=X`
- [ ] **Update viewsets/URLs**
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 5. Nhúng items vào `quiz_collections`, xóa `quiz_collection_items`

### Lý do
- Items của 1 collection hiếm khi query độc lập — luôn truy cùng collection.
- Giảm 1 bảng, đơn giản hoá code.

### Schema mới `quiz_collections`
```
PK: uid
Fields:
  - ... (giữ nguyên)
  - items (list<frozen<uid, int, timestamp, timestamp>>)  ← MỚI: lưu (quiz_id, order, added_at, created_at)
  - items_count (int)  ← MỚI: denormalized counter
```

Hoặc dùng 2 list:
- `item_quiz_ids (list<uuid>)`
- `item_orders (list<int>)`  ← index song song

### Thay đổi
- [ ] **Audit code**: `grep -r "quiz_collection_items\|QuizCollectionItem"`
- [ ] **Sửa model** `quiz_collections`:
  - Thêm `items list<uuid>` (chỉ lưu quiz_id theo order)
  - Hoặc `items list<tuple<uuid, int>>` (UDT nếu Cassandra hỗ trợ)
- [ ] **Migrate data**: copy `quiz_id` từ `quiz_collection_items` → `items` list trong `quiz_collections`, sort theo `order`
- [ ] **Cập nhật repository**:
  - `add_quiz_to_collection(uid, quiz_id, order)` → append vào list
  - `remove_quiz_from_collection(uid, quiz_id)` → remove khỏi list
  - `reorder_items(uid, new_order_list)` → replace list
- [ ] **Cập nhật service**: tất cả thao tác CRUD collection
- [ ] **Drop bảng** `quiz_collection_items`
- [ ] **Xóa files**: model/repo/service/view của `quiz_collection_items`
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 6. Xóa `resource_doc_notes`

### Lý do
- Không còn sử dụng (theo user).

### Thay đổi
- [ ] **Audit code**: `grep -r "resource_doc_notes\|DocNote\|doc_note"`
- [ ] **Drop table** `resource_doc_notes`
- [ ] **Xóa files** model/repo/service/view/URL
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 7. Xóa `resource_doc_reading_progress`

### Lý do
- Không còn sử dụng (theo user).

### Thay đổi
- [ ] **Audit code**: `grep -r "resource_doc_reading_progress\|ReadingProgress\|reading_progress"`
- [ ] **Drop table** `resource_doc_reading_progress`
- [ ] **Xóa files** model/repo/service/view/URL
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 8. Refactor Social: Generic Owner-based

### Lý do
- Hiện tại các bảng social dùng `consumer_uid` → chỉ dành cho student.
- Cần mở rộng: cả `space` (teacher) cũng có thể post/follow.
- Refactor: thay `consumer_uid` → `owner_id` + `owner_type`.

### Thay đổi schema

#### 8.1 `social_posts` (rename từ `consumer_posts`)
```
PK: (owner_id, created_at, uid)  ← thay consumer_uid → owner_id
CK: created_at DESC, uid DESC
Fields:
  - owner_id (uuid)        ← MỚI (thay consumer_uid)
  - owner_type (text)      ← MỚI ("consumer" | "space")
  - owner_name (text)      ← snapshot
  - owner_avatar (text)    ← snapshot
  - classroom_tags (list<uuid>)
  - content (text)
  - image_url (text)
  - image_urls (list<text>)
  - emotion (text)
  - visibility (text)
  - comments_count (int)
  - likes_count (int)
  - created_at, updated_at, deleted_at, is_deleted
  - space_uid (uuid)       ← optional: nếu post trong context 1 space cụ thể
```

#### 8.2 `social_post_comments` (rename từ `post_comments`)
```
PK: (post_uid, created_at, uid)
Fields:
  - post_uid, created_at, uid, content
  - owner_id (uuid)        ← MỚI (thay consumer_uid)
  - owner_type (text)      ← MỚI
  - owner_name (text)
  - owner_avatar (text)
```

#### 8.3 `social_post_likes` (rename từ `post_likes`)
```
PK: (post_uid, owner_id)   ← thay consumer_uid
Fields:
  - post_uid, owner_id
  - owner_type (text)      ← MỚI
  - created_at, deleted_at, is_deleted
```

#### 8.4 `social_follows` (rename từ `user_follows`)
```
PK: (follower_id, followed_id)
Fields:
  - follower_id, follower_type, follower_name, follower_avatar
  - followed_id, followed_type, followed_name, followed_avatar
  - created_at, deleted_at, is_deleted
```

#### 8.5 `social_profiles` (rename từ `user_profiles`)
```
PK: owner_id  ← KHÔNG đổi (đã là owner_id rồi, chỉ đổi tên bảng)
Fields:
  - owner_id, owner_type
  - avatar_url, cover_url
  - followers_count, following_count, posts_count
  - created_at, updated_at, deleted_at, is_deleted
```

### Thay đổi code
- [ ] **Audit code**: `grep -r "consumer_posts\|post_comments\|post_likes\|user_follows\|user_profiles\|consumer_uid"`
- [ ] **Tạo app mới** `features/social/` (hoặc `core/social/`) gom 5 bảng
  - [ ] `models/social_post.py`
  - [ ] `models/social_post_comment.py`
  - [ ] `models/social_post_like.py`
  - [ ] `models/social_follow.py`
  - [ ] `models/social_profile.py`
  - [ ] `repositories/` cho từng bảng
  - [ ] `services/` cho từng bảng
  - [ ] `viewsets/` cho từng bảng
  - [ ] `serializers/`
  - [ ] `urls.py`
- [ ] **Migrate data**:
  - `consumer_posts` → `social_posts`: thêm `owner_type="consumer"`, copy `consumer_uid` → `owner_id`
  - `post_comments` → `social_post_comments`: tương tự
  - `post_likes` → `social_post_likes`
  - `user_follows` → `social_follows`
  - `user_profiles` → `social_profiles` (rename table only)
- [ ] **Drop 5 bảng cũ**
- [ ] **Cập nhật tất cả callers** trong codebase (rất nhiều chỗ — kiểm tra kỹ)
- [ ] **Update tất cả view code** (template không liên quan vì backend API)
- [ ] **Update WebSocket consumers** nếu có
- [ ] **Update docs** `docs/features/social/`
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 9. Xóa `ranking_xp_rules` (hardcode rule)

### Lý do
- User muốn hardcode các rule XP vào code (constants), không cần bảng DB.
- Đơn giản hoá, tránh trường hợp rule bị sửa ngoài ý muốn.

### Thay đổi
- [ ] **Audit code**: `grep -r "ranking_xp_rules\|XpRule\|xp_rule"`
- [ ] **Tạo file** `core/constants/xp_rules.py` (hoặc trong `features/ranking/`):
  ```python
  class XpEvent:
      QUIZ_PASSED = "quiz_passed"
      EXAM_PASSED = "exam_passed"
      CLASSROOM_JOINED = "classroom_joined"
      # ...
  
  XP_AMOUNTS = {
      XpEvent.QUIZ_PASSED: 10,
      XpEvent.EXAM_PASSED: 20,
      XpEvent.CLASSROOM_JOINED: 5,
      # ...
  }
  ```
- [ ] **Refactor service** `ranking_xp_service`:
  - Thay query bảng `ranking_xp_rules` → dùng constant `XP_AMOUNTS[event_type]`
- [ ] **Drop table** `ranking_xp_rules`
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 10. Refactor `course_teacher_contacts` thành bảng lịch sử

### Lý do
- Hiện tại chỉ lưu "HV từng join lớp của teacher" (1 dòng / pair).
- Refactor: lưu **toàn bộ lịch sử** tương tác giữa teacher ↔ consumer (inbox, call, message...).

### Schema mới `course_teacher_contact_history`
```
PK: (teacher_id, consumer_id) + CK: (last_contact_at, uid)
Fields:
  - teacher_id, consumer_id
  - teacher_name, teacher_avatar (snapshot)
  - consumer_name, consumer_avatar, consumer_email (snapshot)
  - first_name, last_name (legacy)
  - first_joined_at
  - last_contact_at
  - last_contact_type (text)  ← "joined" | "message" | "call" | "inquiry"
  - last_contact_ref_id (uuid)
  - contact_count (int)  ← số lần tương tác
  - created_at, updated_at
```

### Thay đổi
- [ ] **Audit code**: `grep -r "course_teacher_contacts\|TeacherContact"`
- [ ] **Đổi tên bảng** `course_teacher_contacts` → `course_teacher_contact_history` (hoặc giữ nguyên tên + thêm field)
  - Khuyến nghị: **giữ tên bảng, mở rộng schema** (đỡ phải migrate tên)
- [ ] **Thêm field** mới vào model:
  - `last_contact_at`, `last_contact_type`, `last_contact_ref_id`, `contact_count`
- [ ] **Refactor service**:
  - Method `record_contact(teacher_id, consumer_id, contact_type, ref_id=None)`:
    - Nếu chưa có row → tạo mới với `first_joined_at=now`, `contact_count=1`
    - Nếu đã có → update `last_contact_at`, `last_contact_type`, `contact_count+=1`
  - Hook vào các flow: HV join lớp, HV gửi message cho teacher, teacher reply, etc.
- [ ] **Update viewset/URL** (thêm endpoint "list contacts", "get history")
- [ ] **Sync Cassandra**: `python manage.py sync_cassandra`

---

## 11. Checklist tổng (Final Review)

### Trước khi implement
- [ ] **Đọc kỹ AGENTS.md**
- [ ] **Đọc docs/features/<module>/** cho từng module bị ảnh hưởng
- [ ] **Audit đầy đủ code** bằng grep cho từng bảng bị xoá/đổi
- [ ] **Kiểm tra cross-module dependencies** (VD: enrollment có FK tới course_courses không?)
- [ ] **Tạo branch** `feature/refactor-schema-cleanup`

### Trong quá trình implement
- [ ] Làm theo thứ tự ưu tiên (xem dưới)
- [ ] Mỗi bước: Model → Repository → Service → Serializer → ViewSet → URL
- [ ] **KHÔNG hard delete** trong code (dùng soft delete cho data migration)
- [ ] **KHÔNG** dùng `git add -A`
- [ ] **KHÔNG** commit nếu chưa sync_cassandra thành công
- [ ] Comment chỉ khi giải thích WHY (không giải thích WHAT)

### Sau khi implement mỗi bước
- [ ] `python manage.py sync_cassandra` thành công
- [ ] `python manage.py show_urls` kiểm tra route còn đúng
- [ ] Test happy path bằng Bruno (`bruno/`)
- [ ] `git add <files>` (specific only)
- [ ] `git commit -m "LMS-<id> <desc>"`
- [ ] Tiếp tục bước tiếp theo

### Trước khi push
- [ ] `git status` kiểm tra sạch
- [ ] `git diff main --stat` review tổng thể
- [ ] `python manage.py check` (Django system check)
- [ ] **Update AGENTS.md** nếu có thay đổi convention

### Push & PR
- [ ] `git push -u origin feature/refactor-schema-cleanup`
- [ ] Tạo PR với template:
  ```
  ## Summary
  - Xóa 5 bảng không dùng: course_courses, course_lessons, resource_doc_notes, resource_doc_reading_progress, ranking_xp_rules
  - Xóa 1 bảng: core_social_accounts (chuyển data sang portfolios)
  - Gom 2 bảng blacklist thành 1
  - Nhúng items vào quiz_collections
  - Refactor social: consumer_* → social_* (generic owner-based)
  - Mở rộng course_teacher_contacts thành lịch sử
  - Thêm metadata vào portfolios

  ## Test
  - [ ] sync_cassandra thành công
  - [ ] show_urls đúng
  - [ ] Bruno test happy path
  - [ ] Không còn import chết
  ```

---

## 12. Thứ tự ưu tiên implement (khuyến nghị)

### Phase 1: Cleanup an toàn (không ảnh hưởng logic chính)
1. ✅ **#1** — Xóa `core_social_accounts` + thêm `metadata` vào `portfolios`
2. ✅ **#6** — Xóa `resource_doc_notes`
3. ✅ **#7** — Xóa `resource_doc_reading_progress`
4. ✅ **#9** — Xóa `ranking_xp_rules` + hardcode

### Phase 2: Refactor schema có migrate data
5. ✅ **#4** — Gom blacklist (cần quyết định schema cuối với user)
6. ✅ **#5** — Nhúng items vào `quiz_collections`
7. ✅ **#10** — Mở rộng `course_teacher_contacts`

### Phase 3: Breaking changes (cần thông báo team)
8. ✅ **#8** — Refactor social (impact lớn nhất)
9. ✅ **#2** — Xóa `course_courses` (cần audit kỹ)
10. ✅ **#3** — Xóa `course_lessons`

### Phase 4: Verify & Deploy
11. ✅ Sync Cassandra lần cuối
12. ✅ Update docs toàn bộ
13. ✅ PR + review

---

## 13. Risks & Open Questions

### Open Questions (cần user quyết trước khi code)
- [ ] **#4 (blacklist)**: Chọn schema nào? (A: 2 bảng giữ nguyên / B: sentinel UUID / C: 1 bảng composite)
- [ ] **#5 (quiz_collections.items)**: Dùng `list<uuid>` hay `list<tuple>` (cần UDT)? Có cần thêm `items_count`?
- [ ] **#8 (social refactor)**: Có nên giữ backward compat (alias bảng cũ) trong 1 release, hay drop luôn?
- [ ] **#2 (`course_courses`)**: Có bảng nào khác đang FK tới `course_courses.uid` không? Cần grep + check schema trước.

### Risks
- **#8 Social refactor** impact lớn nhất — nhiều API endpoint, nhiều frontend caller. Cần plan migration kỹ.
- **#2/#3 Xoá course tables** có thể lộ dependency ở chỗ không ngờ (VD: trong `certificates`, `quiz_collection_items` cũ). Cần audit kỹ.
- **Cassandra không rollback được**: backup schema trước khi drop.
  ```bash
  cqlsh -e "DESC TABLE lms_keyspace.<table_name>" > backup_<table>.cql
  ```
- **Data migration**: nên viết 1 Django management command `python manage.py migrate_schema_v2` để chạy 1 lần, có log + dry-run mode.

---

## 14. Files cần tạo/sửa/xoá (tổng hợp)

### Files MỚI
- `core/constants/xp_rules.py` (#9)
- `core/management/commands/migrate_schema_v2.py` (data migration)
- `features/social/` (folder mới — #8)
  - `models/social_post.py`
  - `models/social_post_comment.py`
  - `models/social_post_like.py`
  - `models/social_follow.py`
  - `models/social_profile.py`
  - `repositories/social_post_repository.py`
  - `repositories/social_post_comment_repository.py`
  - `repositories/social_post_like_repository.py`
  - `repositories/social_follow_repository.py`
  - `repositories/social_profile_repository.py`
  - `services/social_post_service.py`
  - `services/social_post_comment_service.py`
  - `services/social_post_like_service.py`
  - `services/social_follow_service.py`
  - `services/social_profile_service.py`
  - `viewsets/social_post_viewset.py`
  - `viewsets/social_post_comment_viewset.py`
  - `viewsets/social_post_like_viewset.py`
  - `viewsets/social_follow_viewset.py`
  - `viewsets/social_profile_viewset.py`
  - `serializers/social_post_serializer.py`
  - `serializers/social_post_comment_serializer.py`
  - `serializers/social_post_like_serializer.py`
  - `serializers/social_follow_serializer.py`
  - `serializers/social_profile_serializer.py`
  - `urls.py`
- `features/course/blacklist/` (#4)
  - model + repo + service + viewset + serializer + urls

### Files SỬA
- `core/models/base_time_stamp_model.py` (không đổi, nhưng check)
- `core/models/portfolio.py` (#1 — thêm `metadata`)
- `features/quiz/models/quiz_collection.py` (#5 — thêm `items`)
- `features/ranking/services/ranking_xp_service.py` (#9 — dùng constant)
- `features/ranking/models/ranking_xp_transaction.py` (không đổi, chỉ check FK)
- `features/course/teacher_contact/models/teacher_contact.py` (#10 — thêm field)
- `features/course/teacher_contact/services/teacher_contact_service.py` (#10)
- `LMS_SYSTEM/urls.py` (cập nhật routes)
- `LMS_SYSTEM/settings.py` (thêm `features.social` vào INSTALLED_APPS nếu tách app)
- `AGENTS.md` (cập nhật schema overview + module structure)
- `docs/features/social/` (#8 — refactor toàn bộ)

### Files XOÁ
- `core/models/social_account.py` (#1)
- `core/repositories/social_account_repository.py` (#1)
- `core/services/social_account_service.py` (#1)
- `core/viewsets/social_account_viewset.py` (#1, nếu có)
- `features/course/course/` (toàn bộ — #2)
- `features/course/lesson/` (toàn bộ — #3)
- `features/course/classroom_blacklist/` (#4 — gộp vào blacklist mới)
- `features/course/teacher_global_blacklist/` (#4)
- `features/quiz/models/quiz_collection_item.py` (#5)
- `features/quiz/repositories/quiz_collection_item_repository.py` (#5)
- `features/quiz/services/quiz_collection_item_service.py` (#5)
- `features/quiz/viewsets/quiz_collection_item_viewset.py` (#5)
- `features/resource/doc_note/` (toàn bộ — #6)
- `features/resource/reading_progress/` (toàn bộ — #7)
- `features/post/consumer_post.py` (#8 — thay bằng social)
- `features/post/post_comment.py` (#8)
- `features/post/post_like.py` (#8)
- `features/social/follow.py` (#8 — thay bằng generic)
- `features/social/profile.py` (#8)
- `features/ranking/models/xp_rule.py` (#9)

---

## 15. Verification Commands

```bash
# Check không còn import chết
grep -r "core_social_accounts\|SocialAccount" features/ core/
grep -r "course_courses\|CourseCourse" features/ core/
grep -r "course_lessons\|CourseLesson" features/ core/
grep -r "resource_doc_notes\|DocNote" features/ core/
grep -r "resource_doc_reading_progress\|ReadingProgress" features/ core/
grep -r "ranking_xp_rules\|XpRule" features/ core/
grep -r "consumer_posts\|post_comments\|post_likes\|user_follows\|user_profiles" features/ core/
grep -r "course_classroom_blacklists\|course_teacher_global_blacklists" features/ core/
grep -r "quiz_collection_items\|QuizCollectionItem" features/ core/

# Sync schema
python manage.py sync_cassandra

# Check routes
python manage.py show_urls

# Django check
python manage.py check

# Test
pytest
```

---

## 16. Sign-off

- [ ] User confirm Phase 1 (cleanup an toàn)
- [ ] User confirm Phase 2 (refactor schema có migrate)
- [ ] User confirm Phase 3 (breaking changes)
- [ ] User confirm Open Questions (#4, #5, #8, #2)
- [ ] Code reviewed bởi 1 dev khác
- [ ] QA test happy path + edge cases
- [ ] PR merged
- [ ] Docs updated
- [ ] Tag release
