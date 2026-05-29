"""
Face Recognition Microservice — FastAPI + InsightFace

Endpoints:
  POST /detect  — detect faces, return count (camera open check)
  POST /enroll  — extract embedding from a clear face image
  POST /verify  — compare frame against a stored embedding

Run: uvicorn main:app --host 0.0.0.0 --port 8001
Requires Python 3.10 / 3.11 + insightface + onnxruntime-cpu
"""

import base64
import json
import logging
from io import BytesIO
from typing import Optional

# noinspection PyUnresolvedReferences
import cv2
# noinspection PyUnresolvedReferences
import numpy as np
# noinspection PyUnresolvedReferences
from fastapi import FastAPI, HTTPException
# noinspection PyUnresolvedReferences
from pydantic import BaseModel

logger = logging.getLogger("face_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LMS Face Recognition Service")

_face_app = None


def get_face_app():
    global _face_app
    if _face_app is None:
        # noinspection PyUnresolvedReferences
        from insightface.app import FaceAnalysis  # noqa: PLC0415
        _face_app = FaceAnalysis(
            name="buffalo_s",  # buffalo_s: nhẹ hơn, buffalo_l: chính xác hơn
            providers=["CPUExecutionProvider"],
        )
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded (buffalo_s)")
    return _face_app


@app.on_event("startup")
async def startup():
    get_face_app()


def decode_image(b64_data: str) -> np.ndarray:
    """Decode base64 image string → BGR numpy array."""
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    raw = base64.b64decode(b64_data)
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Cannot decode image")
    return img


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-8))


# ── Request / Response schemas ──────────────────────────────────────────────

class ImageRequest(BaseModel):
    image: str  # base64-encoded image (data:image/jpeg;base64,... or raw)


class DetectResponse(BaseModel):
    camera_open: bool
    face_count: int
    faces: list[dict]  # [{bbox, det_score}]


class EnrollRequest(BaseModel):
    image: str


class EnrollResponse(BaseModel):
    embedding: list[float]  # 512-dim vector


class VerifyRequest(BaseModel):
    image: str
    embedding: list[float]  # stored enrollment embedding
    threshold: float = 0.45  # cosine similarity threshold


class VerifyResponse(BaseModel):
    camera_open: bool
    recognized: bool
    multiple_faces: bool
    face_count: int
    similarity: float


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/detect", response_model=DetectResponse)
def detect(req: ImageRequest):
    """Detect faces — used to check if camera is on and count faces."""
    img = decode_image(req.image)
    fa = get_face_app()
    faces = fa.get(img)
    result = []
    for face in faces:
        result.append({
            "bbox": face.bbox.tolist(),
            "det_score": float(face.det_score),
        })
    return DetectResponse(
        camera_open=len(faces) > 0,
        face_count=len(faces),
        faces=result,
    )


@app.post("/enroll", response_model=EnrollResponse)
def enroll(req: EnrollRequest):
    """Extract face embedding from a clear enrollment photo."""
    img = decode_image(req.image)
    fa = get_face_app()
    faces = fa.get(img)
    if not faces:
        raise HTTPException(status_code=422, detail="No face detected in enrollment image")
    if len(faces) > 1:
        raise HTTPException(status_code=422, detail="Multiple faces detected — use a single-person photo")
    embedding = faces[0].normed_embedding.tolist()
    return EnrollResponse(embedding=embedding)


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    """Verify identity: compare live frame against stored embedding."""
    img = decode_image(req.image)
    fa = get_face_app()
    faces = fa.get(img)

    if not faces:
        logger.info("VERIFY | ❌ Không phát hiện khuôn mặt (camera_open=False)")
        return VerifyResponse(
            camera_open=False,
            recognized=False,
            multiple_faces=False,
            face_count=0,
            similarity=0.0,
        )

    # Use the face with highest detection score
    best = max(faces, key=lambda f: f.det_score)
    similarity = cosine_similarity(req.embedding, best.normed_embedding.tolist())
    recognized = similarity >= req.threshold

    if recognized:
        logger.info(
            f"VERIFY | ✅ Khuôn mặt KHỚP | similarity={similarity:.4f} | threshold={req.threshold} | faces={len(faces)}"
        )
    else:
        logger.info(
            f"VERIFY | ❌ Khuôn mặt KHÔNG KHỚP | similarity={similarity:.4f} | threshold={req.threshold} | faces={len(faces)}"
        )

    return VerifyResponse(
        camera_open=True,
        recognized=recognized,
        multiple_faces=len(faces) > 1,
        face_count=len(faces),
        similarity=round(similarity, 4),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
