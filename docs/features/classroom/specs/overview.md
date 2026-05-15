# Classroom Module — Overview

## Purpose

The Classroom module is the core learning unit of the LMS platform. It allows teachers (Space accounts) to create and manage classrooms, add students, and control access. Students (Consumer accounts) join classrooms and access all content published within them.

## Business Context

A classroom is the primary organizational boundary in the LMS. All content (exams, announcements, resources) belongs to a classroom. Membership in a classroom determines what a student can see and do. Teachers own classrooms and control membership and content lifecycle.

## Key Capabilities

### 1. Classroom Creation and Management
Space accounts create classrooms with a name, description, and optional student cap. Each classroom has a status (`active` / `inactive`) that controls student access.

### 2. Membership Management
Teachers can add or remove students from a classroom. Membership records store cached display name and avatar for efficient member list queries without cross-table lookups.

### 3. Shareable Invite Links
Each classroom can have a shareable invite link generated via the Sharing module. Students who access the link are automatically added as members. The link can have an expiry date and usage limit.

### 4. Classroom Discovery
Students can list all classrooms they are members of. Teachers can list all classrooms they own.

### 5. Soft Delete
Classrooms support soft deletion. Deleted classrooms are hidden from all queries but retained in Cassandra for audit purposes.

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Teachers (Space) | Create and manage classrooms; control student access |
| Students (Consumer) | Join classrooms; access classroom content |
| Platform | Ensure classroom ownership is enforced; prevent unauthorized access |
