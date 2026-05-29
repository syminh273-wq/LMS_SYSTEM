"""
WebSocket consumer for real-time face presence monitoring during meeting rooms.

Frontend connects to:
  ws://host/ws/face/meeting/<room_uid>/?token=<jwt>

Protocol (client → server):
  { "type": "frame", "image": "<base64>" }

Protocol (server → client):
  { "type": "verification_result", "camera_open": bool, "recognized": bool,
    "multiple_faces": bool, "face_count": int, "similarity": float }
  { "type": "no_enrollment" }
  { "type": "error", "message": "..." }
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class MeetingRoomMonitorConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get("user", AnonymousUser())
        self.room_uid = self.scope["url_route"]["kwargs"]["room_uid"]

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return

        is_participant = await self._check_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        await self.accept()
        logger.info(f"Meeting room monitor connected: user={self.user.uid} room={self.room_uid}")

    async def disconnect(self, close_code):
        logger.info(f"Meeting room monitor disconnected: user={getattr(self.user, 'uid', '?')} room={self.room_uid}")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        if payload.get("type") == "frame":
            image = payload.get("image")
            if not image:
                await self._send_error("image field is required")
                return
            await self._process_frame(image)
        else:
            await self._send_error(f"Unknown message type: {payload.get('type')}")

    @database_sync_to_async
    def _check_participant(self) -> bool:
        from features.course.meeting_room.services.meeting_room_participant_service import MeetingRoomParticipantService
        svc = MeetingRoomParticipantService()
        return svc.is_participant(self.room_uid, self.user.uid)

    @database_sync_to_async
    def _run_verify_presence(self, image_b64: str) -> dict:
        from features.face.services import FaceRecognitionService
        svc = FaceRecognitionService()
        return svc.verify_presence(
            student_id=self.user.uid,
            image_b64=image_b64,
        )

    async def _process_frame(self, image_b64: str):
        try:
            result = await self._run_verify_presence(image_b64)
        except Exception as exc:
            logger.error(f"Presence check error: {exc}")
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
