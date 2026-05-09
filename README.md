# LMS_SYSTEM

Learning Management System built with Django + Cassandra.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 5.x + Django REST Framework |
| Database | Apache Cassandra (via `django-cassandra-engine`) |
| Authentication | JWT (SimpleJWT) |
| Architecture | Feature-based + Repository/Service Pattern |

## Project Structure

```
LMS_SYSTEM/
├── LMS_SYSTEM/              # Project settings
├── core/                    # Core utilities
│   ├── configs/            # Database config
│   ├── db/                 # DB engines (Cassandra compat)
│   ├── models/             # Base models
│   └── repositories/       # Base repository
├── features/               # Feature-based apps
│   └── account/            # Account module
│       ├── consumer/       # User management
│       │   ├── models/consumer.py
│       │   ├── repositories/
│       │   ├── services/
│       │   └── enums/consumer_role.py
│       └── space/          # Organization/Space management
│           └── models/space.py
├── manage.py
└── requirements.txt
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Database Setup

### `sync_cassandra` Command

Command này được cung cấp bởi `django-cassandra-engine` để đồng bộ hóa tất cả Cassandra models thành bảng trong database.

```bash
python3 manage.py sync_cassandra
```

**Output example:**
```
Creating keyspace lms_system [CONNECTION default] ..
Syncing features.account.models.Consumer
Syncing features.account.models.Space
```

### `sync_table` Function

Bên trong `sync_cassandra`, nó sử dụng `sync_table()` từ `cassandra.cqlengine.management`:

| Chức năng | Mô tả |
|-----------|-------|
| Tạo table | Tạo table mới nếu chưa tồn tại trong keyspace |
| Cập nhật schema | Thêm cột mới vào table đã tồn tại |
| Giữ nguyên data | **Không** xóa cột hoặc data hiện có |

**Ví dụ sử dụng manual:**
```python
from cassandra.cqlengine.management import sync_table
from features.account.consumer.models import Consumer

sync_table(Consumer)  # Sync 1 model cụ thể
```

**Location import:**
```python
# File: core/db/engines/cassandra_engine/compat.py
from cassandra.cqlengine.management import sync_table
```

### Các bước khởi tạo database

```bash
# 1. Đảm bảo Cassandra đang chạy (port 9042)
# 2. Sync tất cả models
python3 manage.py sync_cassandra

# 3. Kiểm tra trong cqlsh
# DESCRIBE TABLES;
```

## Run Server

```bash
python3 manage.py runserver
```

## Key Commands

| Command | Description |
|---------|-------------|
| `python3 manage.py sync_cassandra` | Sync all Cassandra models to tables |
| `python3 manage.py runserver` | Start development server |
| `python3 manage.py shell` | Django shell |

## Models

### Consumer (User)
- `uid` (UUID, PK)
- `username`, `email`, `full_name`, `phone`
- `role`: student | instructor | admin
- Auth fields: `password`, `is_verified`, `is_active`, `last_login`
- Timestamps: `created_at`, `updated_at`, soft delete support

### Space (Organization)
- `uid` (UUID, PK)
- `owner_uid` (UUID, FK to Consumer)
- `name`, `slug`, `description`
- `logo_url`, `cover_url`
- `is_active`, timestamps, soft delete

## Authentication

JWT-based authentication configured with:
- Access token: 60 minutes
- Refresh token: 1 day
- Header type: `Bearer`

## Dependencies

```
cassandra-driver
python-decouple==3.8
django-cassandra-engine
djangorestframework
djangorestframework-simplejwt
django-filter
```

## License

MIT
