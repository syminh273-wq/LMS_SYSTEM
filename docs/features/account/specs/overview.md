# Account Module — Overview

## Purpose

The Account module is the identity and authentication backbone of the LMS platform. It manages two distinct account types — **Space** (teachers) and **Consumer** (students) — each with their own authentication flows, profile structures, and permission scopes.

## Business Context

The LMS platform serves two fundamentally different user groups:

- **Space accounts** represent teachers or educational organizations. They own classrooms, create content, manage students, and have full control over their learning environment.
- **Consumer accounts** represent students. They join classrooms, access published content, and participate in learning activities.

Each account type has distinct data requirements and access boundaries. A Space cannot access another Space's classrooms, and a Consumer can only see content from classrooms they have joined.

## Key Capabilities

### 1. Dual Account Architecture
Two separate models — `Space` and `Consumer` — each with their own registration, login, and profile management flows. Both inherit from a shared `AbstractAuthModel` that provides common authentication fields and behaviors.

### 2. JWT-Based Authentication
All authentication is stateless via JWT tokens. Access tokens expire in 60 minutes; refresh tokens expire in 1 day. The `CassandraJWTAuthentication` backend resolves the token to the correct account type on each request.

### 3. Space Identity and Branding
Space accounts support organizational branding fields (`name`, `slug`, `logo_url`, `cover_url`) allowing teachers to represent themselves as an educational brand on the platform.

### 4. Consumer Roles
Consumer accounts carry a `role` field (`student`, `instructor`, `admin`) that allows differentiated behavior within the consumer context.

### 5. Soft Delete
Both account types support soft deletion — records are marked with `is_deleted = True` and `deleted_at` timestamp rather than being permanently removed, preserving audit history.

### 6. Verification Lifecycle
Both account types track `is_verified` and `verified_at`, allowing the platform to enforce identity validation before granting access to protected resources.

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Teachers (Space accounts) | Secure login, branded profile, classroom management |
| Students (Consumer accounts) | Easy registration, access to joined classrooms |
| Platform operators | Maintain identity integrity, prevent duplicate accounts |
