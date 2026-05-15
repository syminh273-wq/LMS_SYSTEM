# Sharing Module — Overview

## Purpose

The Sharing module generates and manages shareable short-code links that point to any resource in the LMS system. It provides a generic, reusable linking mechanism that any module can use without implementing its own invite or sharing logic.

## Business Context

The primary use case is classroom invitations — a teacher generates a link, shares it with students, and students who access the link are automatically added as classroom members. The module is designed generically so additional resource types (events, files, channels) can be linked in the future without code changes.

## Key Capabilities

### 1. Generic Resource Linking
A link is associated with a `resource_type` and `resource_id`. The type determines how the link is processed when accessed (e.g., `classroom` → add member). New resource types require only a new handler, not new API endpoints.

### 2. Access Control
Links support optional `expired_at` (time-based expiry) and `max_usage` (usage-count-based expiry). Both can be combined. A link with neither constraint is permanent and unlimited.

### 3. Usage Tracking
`used_count` is incremented on every successful link access. This allows teachers to see how many students joined via the invite link.

### 4. Action System
Each link carries an `action` field that instructs the platform what to do when the link is accessed (e.g., `join` for classrooms). This decouples the link from the specific handler.

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Teachers (Space) | Generate invite links for classrooms |
| Students (Consumer) | Access links to join classrooms |
| Other modules | Use the Sharing module to generate links for their resources |
