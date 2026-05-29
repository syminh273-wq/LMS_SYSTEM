"""
Calls the Face Recognition Microservice (FastAPI + InsightFace).
Django does not import insightface directly — all heavy lifting is delegated.
"""
import logging
from datetime import datetime

import requests
from django.conf import settings

from features.face.models import FaceEmbedding, FaceVerificationLog

logger = logging.getLogger(__name__)

FACE_SERVICE_URL = getattr(settings, "FACE_SERVICE_URL", "http://localhost:8001")
VERIFY_THRESHOLD = getattr(settings, "FACE_VERIFY_THRESHOLD", 0.45)


class FaceRecognitionService:

    # ── Enrollment ─────────────────────────────────────────────────────────

    def enroll(self, student_id, image_b64: str) -> FaceEmbedding:
        """
        Extract embedding from photo and save to DB.
        Replaces any existing active embedding for this student.
        """
        resp = requests.post(
            f"{FACE_SERVICE_URL}/enroll",
            json={"image": image_b64},
            timeout=30,
        )
        if resp.status_code != 200:
            raise ValueError(resp.json().get("detail", "Enrollment failed"))

        embedding = resp.json()["embedding"]

        # Deactivate old embeddings
        existing = FaceEmbedding.objects.filter(student_id=student_id).allow_filtering()
        for old in existing:
            old.update(is_active=False)

        record = FaceEmbedding.create(
            student_id=student_id,
            embedding_json=FaceEmbedding.set_embedding(embedding),
            enrolled_at=datetime.now(),
            is_active=True,
        )
        return record

    def get_active_embedding(self, student_id) -> list[float] | None:
        records = (
            FaceEmbedding.objects
            .filter(student_id=student_id)
            .allow_filtering()
        )
        for r in records:
            if r.is_active:
                return r.get_embedding()
        return None

    # ── Verification ───────────────────────────────────────────────────────

    def verify(self, student_id, exam_id, image_b64: str) -> dict:
        """
        Verify a live frame. Logs the result to DB and returns the result dict.
        """
        embedding = self.get_active_embedding(student_id)

        if embedding is None:
            result = {
                "camera_open": False,
                "recognized": False,
                "multiple_faces": False,
                "face_count": 0,
                "similarity": 0.0,
                "error": "no_enrollment",
            }
            self._log(student_id, exam_id, result)
            return result

        resp = requests.post(
            f"{FACE_SERVICE_URL}/verify",
            json={
                "image": image_b64,
                "embedding": embedding,
                "threshold": VERIFY_THRESHOLD,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise ValueError("Face service error: " + str(resp.text))

        result = resp.json()
        self._log(student_id, exam_id, result)
        return result

    def detect_only(self, image_b64: str) -> dict:
        """Lightweight check: is camera open + how many faces."""
        resp = requests.post(
            f"{FACE_SERVICE_URL}/detect",
            json={"image": image_b64},
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError("Face service error")
        return resp.json()

    # ── Logging ────────────────────────────────────────────────────────────

    def _log(self, student_id, exam_id, result: dict):
        try:
            FaceVerificationLog.create(
                exam_id=exam_id,
                student_id=student_id,
                camera_open=result.get("camera_open", False),
                recognized=result.get("recognized", False),
                multiple_faces=result.get("multiple_faces", False),
                face_count=result.get("face_count", 0),
                similarity=result.get("similarity", 0.0),
                verified_at=datetime.now(),
            )
        except Exception as e:
            logger.warning(f"Failed to save verification log: {e}")

    def get_exam_logs(self, exam_id) -> list:
        logs = FaceVerificationLog.objects.filter(exam_id=exam_id)
        return list(logs)

    # ── Classroom session ──────────────────────────────────────────────────

    SESSION_TTL_HOURS = 8

    def verify_for_classroom(self, student_id, classroom_uid, image_b64: str) -> dict:
        """
        Verify identity for classroom entry.
        On success, stamps is_verified=True on the ClassroomMember row.
        """
        from features.course.classroom.models import ClassroomMember

        embedding = self.get_active_embedding(student_id)

        if embedding is None:
            return {
                "camera_open": False,
                "recognized": False,
                "multiple_faces": False,
                "face_count": 0,
                "similarity": 0.0,
                "is_verified": False,
                "error": "no_enrollment",
            }

        resp = requests.post(
            f"{FACE_SERVICE_URL}/verify",
            json={
                "image": image_b64,
                "embedding": embedding,
                "threshold": VERIFY_THRESHOLD,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise ValueError("Face service error: " + str(resp.text))

        result = resp.json()
        is_verified = bool(result.get("recognized"))

        if is_verified:
            try:
                ClassroomMember.objects(
                    member_id=student_id,
                    classroom_uid=classroom_uid,
                ).update(is_verified=True, verified_at=datetime.now())
            except Exception as exc:
                logger.warning(f"Failed to stamp classroom verification: {exc}")

        result["is_verified"] = is_verified
        return result

    def get_classroom_session(self, student_id, classroom_uid) -> dict:
        """
        Return the current session status for a student in a classroom.
        A session is valid for SESSION_TTL_HOURS hours after verified_at.
        """
        from features.course.classroom.models import ClassroomMember

        try:
            records = ClassroomMember.objects.filter(
                member_id=student_id,
                classroom_uid=classroom_uid,
            ).limit(1)
            for member in records:
                if not member.is_verified or not member.verified_at:
                    break
                age_hours = (datetime.now() - member.verified_at).total_seconds() / 3600
                if age_hours < self.SESSION_TTL_HOURS:
                    return {
                        "is_verified": True,
                        "verified_at": member.verified_at.isoformat(),
                    }
        except Exception as exc:
            logger.warning(f"get_classroom_session error: {exc}")

        return {"is_verified": False, "verified_at": None}

    def verify_presence(self, student_id, image_b64: str) -> dict:
        """
        Lightweight presence check during live class (no session write, no exam log).
        Used by the classroom WebSocket monitor.
        """
        embedding = self.get_active_embedding(student_id)

        if embedding is None:
            return {
                "camera_open": False,
                "recognized": False,
                "multiple_faces": False,
                "face_count": 0,
                "similarity": 0.0,
                "error": "no_enrollment",
            }

        resp = requests.post(
            f"{FACE_SERVICE_URL}/verify",
            json={
                "image": image_b64,
                "embedding": embedding,
                "threshold": VERIFY_THRESHOLD,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise ValueError("Face service error: " + str(resp.text))

        return resp.json()
