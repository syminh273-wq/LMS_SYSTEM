# Voice Setting API Documentation

Module này quản lý cấu hình Voice (TTS) cho người dùng, bao gồm việc bật/tắt voice, chọn loại giọng nói và ngôn ngữ.

**Base URL**: `/api/v1/account/voice-settings/`

---

## 1. Lấy cấu hình Voice hiện tại
Trả về cấu hình của người dùng đang đăng nhập. Nếu chưa có, hệ thống sẽ tự động tạo cấu hình mặc định.

- **Endpoint**: `GET /`
- **Auth**: Required (Bearer Token)
- **Response**: `200 OK`
```json
{
    "user_id": "uuid-v7-string",
    "user_type": "consumer", // hoặc "space"
    "voice_name": "vi-VN-HoaiMyNeural",
    "is_voice_enabled": true,
    "language": "vi-VN",
    "updated_at": "2026-06-04T11:22:00Z"
}
```

---

## 2. Cập nhật cấu hình Voice
Cập nhật một hoặc nhiều trường trong cấu hình voice.

- **Endpoint**: `PATCH /`
- **Auth**: Required (Bearer Token)
- **Request Body**:
```json
{
    "voice_name": "en-US-JennyNeural",
    "is_voice_enabled": false,
    "language": "en-US"
}
```
- **Response**: `200 OK` (Trả về object đã cập nhật)

---

## 3. Lấy danh sách Voice khả dụng
Trả về danh sách các giọng nói được hệ thống hỗ trợ.

- **Endpoint**: `GET /available-voices/`
- **Auth**: Required (Bearer Token)
- **Response**: `200 OK`
```json
[
    {
        "id": "vi-VN-HoaiMyNeural",
        "name": "Vietnamese - Hoai My (Female)"
    },
    ...
]
```

---

## 4. Nghe thử Voice (Preview)
Tạo file audio nghe thử cho một giọng nói cụ thể.

- **Endpoint**: `POST /preview/`
- **Auth**: Required (Bearer Token)
- **Request Body**:
```json
{
    "voice_name": "vi-VN-HoaiMyNeural",
    "text": "Đây là bản nghe thử giọng nói." (Optional, default provided)
}
```
- **Response**: `200 OK`
```json
{
    "url": "https://public-domain.com/previews/voice_vi-VN-HoaiMyNeural_abc123.mp3",
    "voice_name": "vi-VN-HoaiMyNeural",
    "text": "Đây là bản nghe thử giọng nói."
}
```

---

## Danh sách Voice Constants (Backend)

| ID | Description |
|---|---|
| `vi-VN-HoaiMyNeural` | Vietnamese (Female) |
| `vi-VN-NamMinhNeural` | Vietnamese (Male) |
| `en-US-AriaNeural` | English US (Female) |
| `en-US-GuyNeural` | English US (Male) |
| `en-US-JennyNeural` | English US (Female) |
| `en-GB-SoniaNeural` | English UK (Female) |
| `en-GB-RyanNeural` | English UK (Male) |
| `zh-CN-XiaoxiaoNeural` | Chinese (Female) |
| `zh-CN-YunjianNeural` | Chinese (Male) |
