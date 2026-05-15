# Account Module — Entities

---

## 1. AbstractAuthModel

**Purpose**: Abstract base class shared by Consumer and Space. Defines the common authentication contract. No Cassandra table is created for this entity.

**Key Attributes**:

| Attribute | Type | Description |
|---|---|---|
| `password` | Text | Securely hashed password |
| `is_verified` | Boolean | Whether the account has been verified |
| `is_active` | Boolean | Whether the account is active |
| `last_login` | DateTime | Timestamp of the last successful login |
| `verified_at` | DateTime | Timestamp when the account was verified |

**Inherited from `BaseTimeStampModel`**:

| Attribute | Type | Description |
|---|---|---|
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last update timestamp |
| `is_deleted` | Boolean | Soft delete flag |
| `deleted_at` | DateTime | Soft delete timestamp |

**Properties**:
- `is_authenticated` → always `True` (required by DRF)
- `is_anonymous` → always `False`

---

## 2. Consumer

**Purpose**: Represents a student on the platform. Stored in the `account_consumers` Cassandra table.

**Table**: `account_consumers`

**Key Attributes**:

| Attribute | Type | Index | Description |
|---|---|---|---|
| `uid` | UUID | Primary key | Unique identifier, generated on creation |
| `username` | Text | Yes | Unique username |
| `email` | Text | Yes | Unique email address |
| `full_name` | Text | No | Display name |
| `phone` | Text | No | Phone number |
| `avatar_url` | Text | No | URL to profile avatar |
| `role` | Text | Yes | `student` \| `instructor` \| `admin` |
| *(AbstractAuthModel fields)* | | | See above |

**Relationships**:
- Referenced by `ClassroomMember.member_id` when joining a classroom
- Referenced by `Conversation.direct_a_id` / `direct_b_id` in direct chats

---

## 3. ConsumerRole (Enum)

**Purpose**: Classifies consumer accounts within the student context.

| Value | Description |
|---|---|
| `student` | Default — can join classrooms and view published content |
| `instructor` | Can create content in a consumer context |
| `admin` | Full consumer-context access |

---

## 4. Space

**Purpose**: Represents a teacher or educational organization on the platform. Stored in the `account_spaces` Cassandra table.

**Table**: `account_spaces`

**Key Attributes**:

| Attribute | Type | Index | Description |
|---|---|---|---|
| `uid` | UUID | Primary key | Unique identifier |
| `email` | Text | Yes | Unique email address |
| `full_name` | Text | No | Owner's personal name |
| `name` | Text | No | Organization or space display name |
| `slug` | Text | Yes | URL-friendly unique identifier (e.g., `prof-nguyen`) |
| `description` | Text | No | Space description |
| `logo_url` | Text | No | Logo image URL |
| `cover_url` | Text | No | Cover/banner image URL |
| `is_active` | Boolean | No | Whether this space is active |
| *(AbstractAuthModel fields)* | | | See above |

**Relationships**:
- Referenced by `Classroom.teacher_id` for all classrooms this space owns
- Referenced by `ClassroomMember.member_id` when the space joins its own classroom as teacher
