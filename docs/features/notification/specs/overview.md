# Notification Module — Overview

## Purpose

The Notification module provides two Firebase-backed channels for delivering real-time signals to users: **Firebase Cloud Messaging (FCM)** for push notifications to mobile and web clients, and **Firebase Realtime Database** for pub/sub state synchronization. Both channels are accessed through a unified abstraction layer.

## Business Context

The LMS platform needs to notify users of events (new exam published, message received, classroom update) even when they are not actively using the app. FCM handles device-level push notifications for background delivery. Firebase Realtime Database handles low-latency state updates for online presence and activity feeds.

## Key Capabilities

### 1. FCM Push Notifications
Send structured push notifications to individual device tokens, topic subscribers, or conditional audiences. Supports both data-only messages (handled by the app) and display notifications (shown by the OS even when the app is in the background).

### 2. Firebase Realtime Database Pub/Sub
Publish and subscribe to real-time state at arbitrary paths. Supports two write modes:
- `set_message` — overwrite state at a path (e.g., presence: online/offline)
- `push_message` — append a new event to a list with an auto-generated key (e.g., activity feed)

### 3. Unified Entry Point
`NotificationService` is the single entry point for all notification operations. Callers select a provider (`realtime_db` or `fcm`) and call the appropriate method. The underlying Firebase client is initialized lazily and once per process.

### 4. Interface Segregation
`RealtimeInterface` and `PushNotificationInterface` are separate. This prevents callers from accidentally calling `send_notification` on a Realtime DB service or `set_message` on an FCM service.

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Platform features (Exam, Chat) | Trigger notifications on key events |
| Mobile/web clients | Receive push notifications; subscribe to real-time state |
| Developers | Clear, tested abstraction — no direct Firebase SDK calls in feature code |
