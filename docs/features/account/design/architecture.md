# Account Module — Architecture

## Overview

The Account module follows a **dual-domain layered architecture** where each account type (Space and Consumer) is a self-contained domain with its own models, repositories, services, serializers, and viewsets, while sharing a common abstract authentication base.

---

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Account Module                        │
│                                                          │
│  ┌──────────────────────┐   ┌────────────────────────┐  │
│  │    Consumer Domain    │   │      Space Domain       │  │
│  │                       │   │                         │  │
│  │  ┌─────────────────┐  │   │  ┌──────────────────┐  │  │
│  │  │ ConsumerViewSet │  │   │  │  SpaceViewSet     │  │  │
│  │  └────────┬────────┘  │   │  └────────┬─────────┘  │  │
│  │           │            │   │           │             │  │
│  │  ┌────────▼────────┐  │   │  ┌────────▼─────────┐  │  │
│  │  │ ConsumerService │  │   │  │  SpaceService     │  │  │
│  │  └────────┬────────┘  │   │  └────────┬─────────┘  │  │
│  │           │            │   │           │             │  │
│  │  ┌────────▼────────┐  │   │  ┌────────▼─────────┐  │  │
│  │  │ ConsumerRepo    │  │   │  │  SpaceRepo        │  │  │
│  │  └────────┬────────┘  │   │  └────────┬─────────┘  │  │
│  └───────────┼───────────┘   └───────────┼─────────────┘  │
│              │                           │                  │
│  ┌───────────▼───────────────────────────▼──────────────┐  │
│  │              AbstractAuthModel (shared base)          │  │
│  │    password · is_verified · is_active · last_login    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
              │                           │
   ┌──────────▼──────────┐    ┌───────────▼───────────┐
   │  account_consumers  │    │    account_spaces      │
   │  (Cassandra table)  │    │  (Cassandra table)     │
   └─────────────────────┘    └────────────────────────┘
```

---

## Components

### AbstractAuthModel (`core/models/abstract_auth.py`)
The shared identity contract inherited by both `Consumer` and `Space`. It is `__abstract__ = True` — no Cassandra table is created for it. Provides: `password`, `is_verified`, `is_active`, `last_login`, `verified_at`, and the `is_authenticated` / `is_anonymous` properties required by DRF's authentication system.

### Consumer Domain (`features/account/consumer/`)
- **Model**: `Consumer` — extends `AbstractAuthModel` with username, email, avatar, role, phone
- **Repository**: `ConsumerRepository` — wraps Cassandra queries on `account_consumers`
- **Service**: `ConsumerService` — registration, login, profile update logic
- **Serializer**: Read/write serializers for API responses and input validation
- **ViewSet**: `ConsumerViewSet` — handles HTTP for consumer profile endpoints
- **Views**: Separate login and register views for clarity
- **Enums**: `ConsumerRole` — `student`, `instructor`, `admin`

### Space Domain (`features/account/space/`)
- **Model**: `Space` — extends `AbstractAuthModel` with name, slug, logo/cover URLs, description
- **Repository**: `SpaceRepository` — wraps Cassandra queries on `account_spaces`
- **Service**: `SpaceService` — registration, login, profile update logic
- **Serializer**: Read/write serializers
- **ViewSet**: `SpaceViewSet`
- **Views**: Separate login and register views

### Authentication (`core/backend/auth/`)
- **`CassandraJWTAuthentication`**: Custom DRF authentication backend. Decodes the JWT, reads the `user_id` claim, and resolves it against both the `Consumer` and `Space` tables. Returns the matched account as the authenticated user.
- **`BaseAuthServices`**: Shared utilities for password hashing and token generation.

---

## API Namespacing

```
/api/v1/consumer/auth/register/    → Consumer registration
/api/v1/consumer/auth/login/       → Consumer login
/api/v1/consumer/profile/          → Consumer profile (GET, PUT)

/api/v1/space/auth/register/       → Space registration
/api/v1/space/auth/login/          → Space login
/api/v1/space/profile/             → Space profile (GET, PUT)
```

Each namespace is independently routed, keeping the two domains cleanly separated at the URL level.

---

## Security

- Passwords are hashed using Django's secure hashing pipeline before storage.
- JWT tokens are signed with the `SECRET_KEY` and carry `user_id` and token type claims.
- The authentication backend does not reveal whether a failed login was due to a wrong email or wrong password (generic error).
- Soft delete ensures tokens for deleted accounts return 401 (user not found during token resolution).
