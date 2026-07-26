# Hướng dẫn chạy thử sau khi refactor

## Prerequisites

- Python 3.13+
- Apache Cassandra hoặc ScyllaDB chạy ở `127.0.0.1:9042`
- Tài khoản `cassandra/cassandra`
- Keyspace `lms_keyspace` đã tồn tại

## 1. Setup lần đầu (hoặc sau khi reset DB)

```bash
# Từ thư mục gốc project
cd /Users/siminh/PycharmProjects/LMS_BACKEND

# 1. Activate virtualenv
source .venv/bin/activate

# 2. Cài dependencies
poetry install

# 3. Sync schema mới (49 bảng)
python manage.py lms_sync_cassandra

# 4. Nếu có data cũ — chạy migration scripts (xem TODO_AFTER_PHASE3.md):
#    - migrate_quiz_collections.py
#    - migrate_blacklists.py
#    - migrate_social_tables.py
#    - migrate_teacher_contacts.py
#    - drop_legacy_tables.py
```

## 2. Chạy dev server

```bash
# 2a. Daphne (production-style, hỗ trợ WebSocket)
daphne -b 0.0.0.0 -p 8000 LMS_SYSTEM.asgi:application

# 2b. Django dev server (HTTP only, không có WebSocket)
python manage.py runserver 0.0.0.0:8000

# 2c. RQ worker (cho quiz AI + auto-close jobs)
python manage.py rqworker default
```

## 3. Verify schema

```bash
# Dump tất cả tables + columns
python dump_all_schema.py

# Xem số bảng hiện tại
python dump_all_schema.py 2>&1 | grep "^TOTAL"
# → TOTAL: 49 tables
```

## 4. Smoke test (nhanh)

### 4.1 Django check
```bash
python manage.py check
# → System check identified no issues (0 silenced).
```

### 4.2 Routes count
```bash
python manage.py show_urls 2>&1 | wc -l
# → ~540 routes
```

### 4.3 Test API bằng curl
```bash
# Health check (nếu có)
curl http://localhost:8000/api/v1/health/

# Login consumer
curl -X POST http://localhost:8000/api/v1/consumer/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# List classrooms
curl http://localhost:8000/api/v1/consumer/course/classrooms/ \
  -H "Authorization: Bearer <TOKEN>"
```

## 5. Bruno test collection

```bash
# Nếu có file bruno collection
ls bruno/

# Chạy từng test thủ công
# (cập nhật nếu có breaking change về consumer_uid → owner_id)
```

## 6. Kiểm tra tables đã drop đúng

```bash
python dump_all_schema.py 2>&1 | grep -E "doc_note|doc_reading|xp_rules|classroom_blacklists|teacher_global_blacklists|quiz_collection_items|course_courses|course_lessons|consumer_posts|post_comments|post_likes|user_follows"
# → (không có kết quả = OK)
```

## 7. Kiểm tra tables mới đã tạo

```bash
python dump_all_schema.py 2>&1 | grep -E "social_posts|social_post_likes|social_post_comments|social_follows|course_blacklists"
# → 5 bảng mới
```

## 8. Nếu gặp lỗi

### Lỗi: "No module named 'features.course.X'"
→ Module đã bị xóa trong Phase 3. Cần update caller.

### Lỗi: "Table X does not exist"
→ Chạy `python manage.py lms_sync_cassandra` để tạo schema.

### Lỗi: "Table Y does not exist" (Y là bảng cũ)
→ OK nếu Y là bảng cũ đã drop. Có thể bỏ qua.

### Lỗi: "Cannot import PublicCourseViewSet"
→ Đã comment-out. Xem TODO #2.

### Lỗi: "consumer_posts" không tồn tại
→ Bảng đã được rename thành `social_posts`. Cập nhật bruno tests.

## 9. Commit changes

```bash
# Stage specific files only (không dùng git add -A)
git add features/ core/ scripts/ docs/refactor/

# Commit
git commit -m "LMS-refactor Phase 2+3: gom blacklist, embed quiz items, refactor social, drop course tables

- course_blacklists: gom 2 bảng blacklist (sentinel UUID cho global)
- quiz_collections.item_quiz_ids: nhúng items, bỏ quiz_collection_items
- course_teacher_contacts: thêm history fields (last_contact_*, contact_count)
- social_*: refactor consumer_* → social_* với owner_id/owner_type
- Xóa: course_courses, course_lessons, course_classroom_blacklists,
  course_teacher_global_blacklists, quiz_collection_items,
  consumer_posts, post_comments, post_likes, user_follows
- 49 tables (giảm 7 từ 56)"

# Push
git push -u origin feature/refactor-schema-cleanup
```

## 10. Nếu cần rollback

```bash
# Revert commit
git revert HEAD

# Hoặc restore data từ backup (nếu đã backup trước)
cqlsh -e "SOURCE 'backup_2026-07-27.cql'"
```

## 11. Tiếp theo

Xem `docs/refactor/TODO_AFTER_PHASE3.md` cho:
- Data migration scripts (nếu có data cũ cần giữ)
- Bruno test updates
- Docs updates
- Re-implement PublicCourseViewSet
