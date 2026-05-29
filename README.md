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
| Face Recognition | InsightFace + FastAPI microservice (`face_service/`) |
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
| Face Recognition | `features/face/` + `face_service/` | Exam proctoring: identity verification & camera monitoring |

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
- Docker *(optional — for running the Face Recognition service)*

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

| Endpoint | Description |
|----------|-------------|
| `ws://<host>/ws/chat/<conversation_id>/` | Real-time chat |
| `ws://<host>/ws/rtc/<room_name>/` | WebRTC signaling |
| `ws://<host>/ws/presence/` | Online presence / attendance |
| `ws://<host>/ws/face/monitor/<exam_id>/` | Real-time face monitoring during exam |

Pass the JWT token as a query parameter:

```
ws://<host>/ws/face/monitor/<exam_id>/?token=<access_token>
```

---

## Face Recognition (Exam Proctoring)

The face recognition feature runs as a **separate microservice** (`face_service/`) using Python 3.11 and InsightFace, because InsightFace is not compatible with Python 3.13 (used by the main Django app).

### Architecture

```
Frontend (camera)
    │
    ├── REST  POST /api/v1/consumer/face/enroll/              ← register face (once)
    ├── REST  GET  /api/v1/consumer/face/enroll/              ← check enrollment status
    ├── REST  POST /api/v1/consumer/face/exams/<id>/verify/   ← one-shot verify
    ├── WS    ws://host/ws/face/monitor/<exam_id>/            ← continuous monitoring
    └── REST  GET  /api/v1/space/face/exams/<id>/logs/        ← teacher: view logs
                       │
               Django (features/face/)
                       │ HTTP
             Face Service (FastAPI, port 8001)
             InsightFace buffalo_s model
```

### Starting the Face Service

**Option A — Docker (recommended):**

```bash
cd face_service
docker build -t lms-face-service .
docker run -p 8001:8001 lms-face-service
```

**Option B — Poetry với Python 3.11:**

```bash
cd face_service

# Yêu cầu Python 3.11 đã được cài sẵn trên máy
poetry env use python3.11
poetry install

poetry run uvicorn main:app --host 0.0.0.0 --port 8001
```

**Option C — Virtualenv thủ công với Python 3.11:**

```bash
cd face_service

python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001
```

**Option D — Conda / pyenv environment hiện tại (dùng `python -m`):**

```bash
cd face_service

# Cài dependencies vào env đang active
python -m pip install insightface onnxruntime opencv-python-headless \
  fastapi "uvicorn[standard]" packaging

# Chạy service (dùng python -m để đảm bảo đúng interpreter)
python -m uvicorn main:app --port 8001
```

> Dùng `python -m uvicorn` thay vì `uvicorn` trực tiếp để tránh xung đột PATH khi có nhiều môi trường Python trên máy.

> **Note:** The first startup downloads the InsightFace `buffalo_s` model (~85 MB) from the internet. Subsequent starts are instant.

### Environment Variables

Add these to your `.env`:

```env
FACE_SERVICE_URL=http://localhost:8001
FACE_VERIFY_THRESHOLD=0.45   # cosine similarity threshold (0.0–1.0, higher = stricter)
```

### Sync Cassandra Tables

After starting the Django server for the first time with this feature:

```bash
python manage.py sync_cassandra
```

This creates two new tables: `face_embeddings` and `face_verification_logs`.

### Frontend Integration

```javascript
// 1. Register the student's face (done once before any exam)
const res = await fetch('/api/v1/consumer/face/enroll/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ image: 'data:image/jpeg;base64,...' }),
})

// 2. Open WebSocket during exam and send frames every 5–10 seconds
const ws = new WebSocket(`ws://host/ws/face/monitor/${examId}/?token=${token}`)

const sendFrame = () => {
  const canvas = document.createElement('canvas')
  // draw video frame to canvas ...
  ws.send(JSON.stringify({ type: 'frame', image: canvas.toDataURL('image/jpeg') }))
}
setInterval(sendFrame, 5000)

// 3. Handle results
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data)
  if (msg.type === 'verification_result') {
    console.log('Camera on:', msg.camera_open)
    console.log('Correct person:', msg.recognized)
    console.log('Multiple faces detected:', msg.multiple_faces)
    console.log('Similarity score:', msg.similarity)
  }
  if (msg.type === 'no_enrollment') {
    alert('Please enroll your face before starting the exam.')
  }
}
```

### What Gets Detected

| Check | Description |
|-------|-------------|
| Camera open | At least one face visible in the frame |
| Identity verified | Face matches the enrolled student (similarity ≥ threshold) |
| Multiple faces | More than one person in front of the camera (cheating alert) |
| Similarity score | `0.0` – `1.0`; higher = more confident match |

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
