import logging
import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)
app = FastAPI(title="Hello Word API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


class HelloResponse(BaseModel):
    message: str
    source: str


@lru_cache
def get_firestore_client():
    import firebase_admin
    from firebase_admin import firestore

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    firebase_app = firebase_admin.initialize_app(
        options={"projectId": project_id} if project_id else None
    )
    return firestore.client(app=firebase_app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_model=HelloResponse)
def hello():
    if os.getenv("FIREBASE_ENABLED", "false").lower() != "true":
        return HelloResponse(message="hello word", source="local")

    try:
        document = get_firestore_client().collection("messages").document("hello").get(
            timeout=5, retry=None
        )
    except Exception as exc:
        logger.exception("Cannot read messages/hello from Firestore")
        raise HTTPException(status_code=503, detail="Firebase unavailable") from exc

    message = (document.to_dict() or {}).get("text")
    if not isinstance(message, str) or not message.strip():
        raise HTTPException(
            status_code=503,
            detail="Create Firestore document messages/hello with a non-empty text field",
        )
    return HelloResponse(message=message, source="firestore")
