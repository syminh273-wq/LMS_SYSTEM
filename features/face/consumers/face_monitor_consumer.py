"""
WebSocket consumer for real-time face monitoring during exams.

Frontend connects to:
  ws://host/ws/face/monitor/<exam_uid>/?token=<jwt>

Protocol (client → server):
  { "type": "frame", "image": "<base64>" }   — periodic frame (every 5-10s)

Protocol (server → client):
  { "type": "session_info", "camera_required": bool }
  { "type": "verification_result", "camera_open": bool, "recognized": bool,
    "multiple_faces": bool, "face_count": int, "similarity": float }
  { "type": "error", "message": "..." }
  { "type": "no_enrollment" }
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class FaceMonitorConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get("user", AnonymousUser())
        self.exam_id = self.scope["url_route"]["kwargs"]["exam_uid"]

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        self.camera_required = await self._load_camera_required()

        await self.accept()
        await self.send(json.dumps({
            "type": "session_info",
            "camera_required": self.camera_required,
        }))
        logger.info(
            f"Face monitor connected: student={self.user.uid} exam={self.exam_id} "
            f"camera_required={self.camera_required}"
        )

    async def disconnect(self, close_code):
        logger.info(f"Face monitor disconnected: student={getattr(self.user, 'uid', '?')} exam={self.exam_id}")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        msg_type = payload.get("type")

        if msg_type == "frame":
            image = payload.get("image")
            if not image:
                await self._send_error("image field is required")
                return
            await self._process_frame(image)
        else:
            await self._send_error(f"Unknown message type: {msg_type}")

    @database_sync_to_async
    def _load_camera_required(self) -> bool:
        from features.course.exam.repositories import ExamRepository
        repo = ExamRepository()
        exam = repo.get_by_uid(self.exam_id)
        return bool(exam.camera_required) if exam else False

    @database_sync_to_async
    def _run_verify(self, image_b64: str) -> dict:
        from features.face.services import FaceRecognitionService
        svc = FaceRecognitionService()
        return svc.verify(
            student_id=self.user.uid,
            exam_id=self.exam_id,
            image_b64=image_b64,
        )

    async def _process_frame(self, image_b64: str):
        try:
            result = await self._run_verify(image_b64)
        except Exception as exc:
            logger.error(f"Verification error: {exc}")
            await self._send_error("Face service unavailable")
            return

        if result.get("error") == "no_enrollment":
            await self.send(json.dumps({"type": "no_enrollment"}))
            return

        await self.send(json.dumps({
            "type": "verification_result",
            "camera_open": result["camera_open"],
            "recognized": result["recognized"],
            "multiple_faces": result["multiple_faces"],
            "face_count": result["face_count"],
            "similarity": result["similarity"],
        }))

    async def _send_error(self, message: str):
        await self.send(json.dumps({"type": "error", "message": message}))
