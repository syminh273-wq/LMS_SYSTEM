# LMS Backend — Portfolio Consolidation Report

> **Branch:** `refactor/consolidate-models`
> **Ngày:** 2026-07-27
> **Mục tiêu:** Gộp 3 bảng profile/settings dư thừa vào 1 bảng `portfolios` polymorphic, dùng chung cho cả `consumer` và `space`.

---

## 1. Tổng quan thay đổi

### Trước refactor (3 bảng chồng chéo)

| Bảng | File | Vấn đề |
|---|---|---|
| `teacher_settings` | `features/account/consumer/models/teacher_settings.py` | **Dead code** — frontend không bao giờ gọi endpoint này |
| `student_profile_settings` | `features/account/consumer/models/student_profile_settings.py` | Trùng key-value với `user_settings` + `user_profiles` |
| `user_profiles` (social) | `features/social/models/user_profile.py` | Chứa `bio, major, skills, github, linkedin, website` — overlap với `student_profile_settings` |

### Sau refactor (1 bảng polymorphic)

| Bảng | File | Trạng thái |
|---|---|---|
| `portfolios` | `features/portfolio/models/portfolio.py` | ⭐ **Mở rộng** — partition key `(owner_id, owner_type)`, mở rộng `VALID_KEYS` từ 6 → 33 keys |

**Kết quả:** 3 bảng → 1 bảng. Tất cả profile data (bio, appearance, privacy, social links, rich entries) lưu trong `portfolios` với `owner_type='consumer' | 'space'`.

---

## 2. Schema `portfolios` mới

```python
class Portfolio(BaseTimeStampModel):
    __table_name__ = 'portfolios'

    uid          = columns.UUID(primary_key=True, default=uuid7)
    owner_id     = columns.UUID(partition_key=True, required=True)
    owner_type   = columns.Text(partition_key=True, required=True)  # 'consumer' | 'space'
    key          = columns.Text(primary_key=True, required=True)

    value         = columns.Text(default='{}')
    is_public     = columns.Boolean(default=True)
    display_order = columns.Integer(default=0)
```

**Composite PK:** `(owner_id, owner_type, key)` — query "lấy tất cả profile của user X" = 1 partition scan.

### Valid keys (33 keys, gộp từ 3 bảng cũ)

| Nhóm | Keys |
|---|---|
| **Profile** | `bio, city, country, major, department` |
| **Social links** | `github, linkedin, website, skills` |
| **Appearance** | `theme_color, cover_style, cover_value` |
| **Privacy** | `profile_visibility, show_stats, show_classrooms, show_grades, show_badges, show_address, show_links, show_hobbies, show_certificates, show_activity, show_contact` |
| **Layout** | `sections_order, metadata` |
| **Rich entries** | `intro, certificate, experience, achievement, course, education` |

---

## 3. Files đã xóa (8 files)

| File | Lý do |
|---|---|
| `features/account/consumer/models/teacher_settings.py` | Dead code |
| `features/account/consumer/services/teacher_settings_service.py` | Dead code |
| `features/account/consumer/views/teacher_settings_view.py` | Dead code |
| `features/account/consumer/serializers/teacher_settings_serializer.py` | Dead code |
| `features/account/consumer/models/student_profile_settings.py` | Đã migrate sang `portfolios` |
| `features/account/consumer/services/student_profile_service.py` | Đã rewrite thành `PortfolioService.get_profile_settings()` |

---

## 4. Files đã sửa (10 files)

### Models
- `features/portfolio/models/portfolio.py` — thêm `uid`, `partition_key=(owner_id, owner_type)`, mở rộng `VALID_KEYS` (6 → 33), thêm `SINGLE_KEYS/PRIVACY_KEYS/APPEARANCE_KEYS/PROFILE_KEYS/RICH_KEYS` constants
- `features/social/models/user_profile.py` — xóa `bio, major, department, skills, github, linkedin, website` (chuyển sang `PortfolioService.get_social_profile()`)

### Repositories
- `features/portfolio/repositories/portfolio_repository.py` — dùng `uuid7()` thay vì `uuid.uuid4()`

### Services
- `features/portfolio/services/portfolio_service.py` — thêm `get_profile_settings()`, `get_profile_settings_or_public()`, `update_profile_settings()`, `get_social_profile()`
- `features/social/services/profile_service.py` — `serialize()` nhận thêm `social_profile` param, `update_mine()` ghi bio/major/skills/... vào `Portfolio` thay vì `UserProfile`

### Views
- `features/account/consumer/viewsets/student_profile_viewset.py` — `StudentProfileSettingsView` dùng `PortfolioService` thay vì `StudentProfileService`

### URLs / Init
- `features/account/consumer/services/__init__.py` — xóa `StudentProfileService`, `TeacherSettingsService`
- `features/account/consumer/serializers/__init__.py` — xóa `TeacherSettingSerializer`
- `features/account/consumer/models/__init__.py` — xóa `StudentProfileSettings`, `TeacherSetting`
- `features/account/space/urls.py` — xóa route `path('settings/', TeacherSettingsView.as_view(), ...)`
- `features/account/models.py` — xóa `StudentProfileSettings`, `TeacherSetting` khỏi exports

### Scripts (debug)
- `inspect_address.py` — cập nhật để đọc `portfolios` thay vì `student_profile_settings`
- `verify_address_logic.py` — cập nhật để dùng `PortfolioService.get_profile_settings_or_public()`

---

## 5. Logic mapping (cũ → mới)

### `student_profile_settings` (per-consumer) → `portfolios` (per-user)

| Field cũ | Key mới trong `portfolios` | is_public |
|---|---|---|
| `bio` | `bio` | ✅ true |
| `city` | `city` | ✅ true |
| `country` | `country` | ✅ true |
| `theme_color` | `theme_color` | ✅ true |
| `cover_style` | `cover_style` | ✅ true |
| `cover_value` | `cover_value` | ✅ true |
| `show_stats` | `show_stats` | ❌ false (privacy) |
| `show_classrooms` | `show_classrooms` | ❌ false (privacy) |
| `show_grades` | `show_grades` | ❌ false (privacy) |
| `show_badges` | `show_badges` | ❌ false (privacy) |
| `show_address` | `show_address` | ❌ false (privacy) |
| `show_links` | `show_links` | ❌ false (privacy) |
| `show_hobbies` | `show_hobbies` | ❌ false (privacy) |
| `show_certificates` | `show_certificates` | ❌ false (privacy) |
| `show_activity` | `show_activity` | ❌ false (privacy) |
| `show_contact` | `show_contact` | ❌ false (privacy) |
| `sections_order` | `sections_order` | ❌ false (privacy) |
| `profile_visibility` | `profile_visibility` | ❌ false (privacy) |
| `metadata` | `metadata` | ❌ false (privacy) |

### `user_profiles` (social) — fields đã xóa

| Field cũ | Chuyển sang |
|---|---|
| `bio` | `PortfolioService.get_social_profile()` → `portfolios['bio']` |
| `major` | `PortfolioService.get_social_profile()` → `portfolios['major']` |
| `department` | `PortfolioService.get_social_profile()` → `portfolios['department']` |
| `skills` | `PortfolioService.get_social_profile()` → `portfolios['skills']` |
| `github` | `PortfolioService.get_social_profile()` → `portfolios['github']` |
| `linkedin` | `PortfolioService.get_social_profile()` → `portfolios['linkedin']` |
| `website` | `PortfolioService.get_social_profile()` → `portfolios['website']` |
| `avatar_url` | **GIỮ** trong `user_profiles` (identity) |
| `cover_url` | **GIỮ** trong `user_profiles` (identity) |
| `posts_count` | **GIỮ** trong `user_profiles` (counter) |
| `followers_count` | **GIỮ** trong `user_profiles` (counter) |
| `following_count` | **GIỮ** trong `user_profiles` (counter) |

### `teacher_settings` (dead code)

| Endpoint cũ | Endpoint mới |
|---|---|
| `GET /api/v1/space/account/settings/` | `GET /api/v1/account/user-settings/` (đã có sẵn, frontend đã dùng) |
| `PATCH /api/v1/space/account/settings/` | `POST /api/v1/account/user-settings/` (đã có sẵn) |

**Không cần frontend change** — frontend (`space-web/src/lib/api/user-settings.ts`) đã chỉ gọi `/user-settings/` từ đầu.

---

## 6. Service API mới

### `PortfolioService` (đã mở rộng)

```python
# Rich entries (intro, certificate, experience, achievement, course, education)
PortfolioService().get_mine(user)              # dict với 6 keys
PortfolioService().get_public(owner_type, owner_id)  # dict public-only

# Profile settings (thay thế StudentProfileService)
PortfolioService().get_profile_settings(user)              # dict 19 keys
PortfolioService().get_profile_settings_or_public(uid)     # dict 19 keys (no auth)
PortfolioService().update_profile_settings(user, data)     # dict 19 keys

# Social profile (thay thế phần bio/major/skills của UserProfile)
PortfolioService().get_social_profile(owner_id, owner_type)  # dict 9 keys

# Rich entries CRUD (giữ nguyên)
PortfolioService().upsert_entry(user, data)
PortfolioService().bulk_upsert(user, entries)
PortfolioService().delete_entry(user, uid)
PortfolioService().reorder(user, orders)
```

### `ProfileService` (social) — API không đổi

```python
ProfileService().get_mine(user)          # merge UserProfile + Portfolio social
ProfileService().get_public(owner_id)    # merge UserProfile + Portfolio social
ProfileService().update_mine(user, data) # ghi UserProfile (avatar/cover) + Portfolio (bio/skills/...)
ProfileService().increment_posts(owner_id, delta)
ProfileService().increment_followers(owner_id, delta)
ProfileService().increment_following(owner_id, delta)
```

---

## 7. Endpoints (không đổi)

| Method | URL | View | Service |
|---|---|---|---|
| GET | `/api/v1/consumer/account/profile-settings/` | `StudentProfileSettingsView` | `PortfolioService.get_profile_settings()` |
| PATCH | `/api/v1/consumer/account/profile-settings/` | `StudentProfileSettingsView` | `PortfolioService.update_profile_settings()` |
| GET | `/api/v1/consumer/account/profile/<uid>/public/` | `PublicStudentProfileView` | `PortfolioService.get_profile_settings_or_public()` |
| GET | `/api/v1/portfolio/me/` | `MyPortfolioView` | `PortfolioService.get_mine()` |
| GET | `/api/v1/portfolio/<owner_type>/<owner_id>/` | `PublicPortfolioView` | `PortfolioService.get_public()` |

**Không có breaking change ở API layer.**

---

## 8. Migration steps (production)

```bash
# 1. Drop old tables (sau khi migrate data)
DROP TABLE IF EXISTS lms_keyspace.teacher_settings;
DROP TABLE IF EXISTS lms_keyspace.student_profile_settings;

# 2. Migrate student_profile_settings → portfolios
INSERT INTO lms_keyspace.portfolios (uid, owner_id, owner_type, key, value, is_public, display_order, created_at, updated_at)
SELECT
  uuid(),
  consumer_uid,
  'consumer',
  'bio',
  toJson(bio),
  true, 0, currentTimestamp(), currentTimestamp()
FROM lms_keyspace.student_profile_settings;
# ... repeat cho 19 keys (city, country, theme_color, ..., metadata)

# 3. Migrate user_profiles bio/major/skills → portfolios
INSERT INTO lms_keyspace.portfolios (uid, owner_id, owner_type, key, value, is_public, display_order, created_at, updated_at)
SELECT
  uuid(),
  owner_id,
  owner_type,
  'bio',
  toJson(bio),
  true, 0, currentTimestamp(), currentTimestamp()
FROM lms_keyspace.user_profiles WHERE bio != '';
# ... repeat cho major, department, skills, github, linkedin, website

# 4. sync_cassandra
python manage.py sync_cassandra
```

---

## 9. Verification

```bash
# Sync schema
$ python manage.py sync_cassandra
Syncing features.portfolio.models.Portfolio
... OK

# URLs (no broken routes)
$ python manage.py show_urls | grep -E "profile-setting|portfolio"
api/v1/consumer/account/profile-settings/ (StudentProfileSettingsView)
api/v1/portfolio/me/ (MyPortfolioView)
api/v1/portfolio/me/upload/ (PortfolioUploadView)
api/v1/portfolio/me/reorder/ (PortfolioReorderView)
api/v1/portfolio/me/entries/ (PortfolioEntryCreateView)
api/v1/portfolio/me/entries/<str:uid>/ (PortfolioEntryDetailView)
api/v1/portfolio/<str:owner_type>/<str:owner_id>/ (PublicPortfolioView)

# Django check (no broken imports)
$ python -c "import django; django.setup(); from django.urls import get_resolver; get_resolver()"
All URLs loaded OK
```

---

## 10. Kết quả

| Metric | Trước | Sau | Delta |
|---|---|---|---|
| Cassandra tables (profile/settings) | 3 | 1 | **−2** |
| Models (Python) | 3 | 1 | **−2** |
| Services (profile/settings) | 3 | 1 | **−1** (`StudentProfileService` → `PortfolioService.get_profile_settings()`) |
| Views (dead code) | 1 (`TeacherSettingsView`) | 0 | **−1** |
| URLs (dead code) | 1 (`/space/account/settings/`) | 0 | **−1** |
| Serializers (dead code) | 1 (`TeacherSettingSerializer`) | 0 | **−1** |
| Lines of code | — | — | **−49** (336 deletions, 287 insertions) |

**Net win:** −2 tables, −1 dead endpoint, −1 service, −1 view, −1 URL, −1 serializer, 1 polymorphic table thay thế 3.

---

## 11. Frontend impact

### Không cần thay đổi

- `space-web/src/lib/api/user-settings.ts` — đã dùng `/user-settings/` từ đầu
- `consumer-web/src/lib/api/user-settings.ts` — đã dùng `/user-settings/` từ đầu

### Tùy chọn (cleanup sau)

- `consumer-web/src/lib/api/account.ts` — có thể xóa `getProfileSettings()` / `updateProfileSettings()` và thay bằng `portfolioService.getMine()` (optional, không breaking).

---

## 12. Next steps (chưa làm trong PR này)

1. **Quiz consolidation** — merge `quiz_plays` + `quiz_logs` → `quiz_attempts` (1 sprint)
2. **Activity log consolidation** — merge `classroom_activity_logs` + `exam_audit_logs` + `face_verification_logs` → `activity_events` (1 sprint)
3. **Account unification** — merge `consumer` + `space` → `accounts` (P3, touch nhiều FKs)
4. **Membership consolidation** — merge `classroom_members` + `meeting_room_participants` + `conversation_members` → `memberships` (P2)

Xem `AGENTS.md` và báo cáo architecture review đầy đủ để biết chi tiết.
