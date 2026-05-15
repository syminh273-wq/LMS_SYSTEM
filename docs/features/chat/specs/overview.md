# Chat Module — Overview

## Purpose

The Chat module provides real-time messaging between platform users via WebSocket (Django Channels), with a REST API for conversation management and message history. It supports classroom-wide group channels and 1-to-1 direct messages.

## Business Context

Every classroom has a dedicated group chat channel where teacher and students communicate. Users can also exchange direct messages with each other. Messages support text and file attachments (image, video, audio, PDF, file) via the Resource module. The WebSocket connection keeps clients in sync in real time.

## Key Capabilities

### 1. Two Conversation Types
- **Channel**: A group chat tied to a classroom. Created alongside the classroom. All classroom members participate.
- **Direct**: A 1-to-1 conversation between any two users. Identified uniquely by a sorted pair of user UIDs to prevent duplicate conversations.

### 2. Real-Time Messaging via WebSocket
Clients connect to a per-conversation WebSocket endpoint. Messages sent via WebSocket are broadcast to all connected participants in real time. The REST API serves as a fallback for sending and always provides message history.

### 3. Rich Message Types
Messages support `text`, `image`, `video`, `audio`, `pdf`, and `file` types. File messages reference a resource uploaded via the Resource module. Display data (URL, name, size) is cached on the message record.

### 4. Reply Threading
Messages can reference another message via `reply_to_uid`, enabling threaded reply context in the UI.

### 5. Soft Delete
Messages support soft deletion — they are hidden from queries but retained in Cassandra.

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Teachers (Space) | Communicate with students in classroom channel |
| Students (Consumer) | Ask questions, receive announcements, direct message peers |
| Platform | Real-time delivery, message persistence, WebSocket lifecycle |
