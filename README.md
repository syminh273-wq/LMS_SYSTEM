# LMS Backend

A Learning Management System REST API built with Django and Apache Cassandra, designed to support both teachers (Space accounts) and students (Consumer accounts).

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 4.x + Django REST Framework |
| Database | Apache Cassandra (`django-cassandra-engine`) |
| Authentication | JWT (`djangorestframework-simplejwt`) |
| Real-time | Django Channels + Daphne (WebSocket) |
| Storage | Cloudflare R2 (`boto3`) |
| Push Notification | Firebase Admin SDK (FCM + Realtime Database) |
| Dependency Management | Poetry |

---

## Modules

| Module | Path | Description |
|--------|------|-------------|
| Account | `features/account/` | Consumer (Student) & Space (Teacher) accounts |
| Classroom | `features/course/classroom/` | Classroom creation and management |
| Resource | `features/resource/` | File upload to R2 storage |
| Sharing | `features/sharing/` | Shareable links for resources |
| Chat | `features/chat/` | Conversations and real-time messaging |
| Notification | `core/notification/` | FCM push + Firebase Realtime Database |

---

## Project Structure

```
LMS_BACKEND/
├── LMS_SYSTEM/                        # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
│
├── core/                              # Shared infrastructure
│   ├── backend/                       # Auth backends & exception handling
│   ├── configs/                       # Database configuration
│   ├── db/engines/cassandra_engine/   # Cassandra engine & compatibility
│   ├── firebase/                      # Firebase integration
│   │   ├── client/firebase_app.py     # Singleton Firebase app init
│   │   ├── fcm/fcm_service.py         # FCM push notifications
│   │   └── realtime/realtime_service.py
│   ├── models/                        # Base models & mixins (timestamp, soft delete)
│   ├── notification/                  # Notification abstraction layer
│   │   ├── dto/
│   │   ├── enums/
│   │   ├── interfaces/
│   │   └── services/
│   ├── repositories/                  # Base repository pattern
│   ├── services/                      # Base service pattern
│   ├── storages/                      # Cloudflare R2 storage service
│   └── ws/                            # WebSocket consumers & routing
│
├── features/
│   ├── account/
│   │   ├── consumer/                  # Student account management
│   │   └── space/                     # Teacher account management
│   ├── course/
│   │   └── classroom/                 # Classrooms & members
│   ├── chat/                          # Conversations & messages
│   ├── resource/                      # File management
│   └── sharing/                       # Sharing links
│
├── manage.py
├── pyproject.toml
└── .env
```

---

## Prerequisites

- Python `3.9+`
- [Poetry](https://python-poetry.org/docs/#installation)
- Apache Cassandra running on port `9042`
- Cloudflare R2 bucket *(optional — falls back to local storage in development)*
- Firebase project *(optional — required for push notifications)*

---

## Getting Started

```bash
# 1. Clone the repository
git clone <repo-url>
cd LMS_BACKEND

# 2. Install dependencies
poetry install

# 3. Activate the virtual environment
poetry shell

# 4. Set up environment variables
cp .env.example .env
# Fill in the required values (see Environment Variables section below)

# 5. Sync Cassandra models
python manage.py sync_cassandra

# 6. Start the development server
python manage.py runserver

# 7. View all registered API endpoints
python manage.py show_urls
```

---

---

## WebSocket

Connect to the chat WebSocket at:

```
ws://<host>/ws/chat/<conversation_id>/
```

Pass the JWT token via the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Architecture

This project follows a **Feature-based + Repository/Service** pattern:

```
ViewSet → Service → Repository → Cassandra
```

- **ViewSet** — handles HTTP request/response, delegates to service
- **Service** — contains business logic, calls repository
- **Repository** — abstracts Cassandra queries, no raw CQL in services
- **Models** — extend base classes from `core/models/` for timestamps, soft delete, and audit logging

---

## Database

This project uses **Apache Cassandra** instead of a relational database. Key differences to be aware of:

| SQL | Cassandra |
|-----|-----------|
| `makemigrations` / `migrate` | `sync_cassandra` |
| Foreign keys | Stored as plain UUID fields |
| `JOIN` queries | Not supported — data is denormalized |
| Arbitrary filtering | Secondary indexes with limitations |

After adding or modifying a model, run:

```bash
python manage.py sync_cassandra
```

---

## Common Commands

| Command | Description |
|---------|-------------|
| `python manage.py runserver` | Start the development server |
| `python manage.py sync_cassandra` | Sync all Cassandra models to the database |
| `python manage.py show_urls` | Print all registered API endpoints |
| `python manage.py shell` | Open the Django interactive shell |
| `poetry add <package>` | Add a new dependency |
| `poetry add --group dev <package>` | Add a development dependency |

---

## License

MIT
