from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from apps.gateway.middleware.auth import require_auth
from apps.gateway.services.message_service import MessageService
from apps.gateway.services.session_service import SessionService


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"], dependencies=[Depends(require_auth)])


class CreateSessionRequest(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=200)


class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.get("")
async def list_sessions(req: Request, limit: int = 50):
    user = req.state.user
    service = SessionService()
    return await service.list_sessions(user["user_id"], limit=limit)


@router.post("")
async def create_session(req: Request, body: CreateSessionRequest):
    user = req.state.user
    service = SessionService()
    session = await service.create_session(user["user_id"], title=body.title)
    req.state.session_id = session["session_id"]
    return session


@router.get("/active")
async def get_active(req: Request):
    user = req.state.user
    service = SessionService()
    session_id = await service.get_active_session(user["user_id"])
    return {"session_id": session_id}


class SetActiveRequest(BaseModel):
    session_id: str


@router.post("/active")
async def set_active(req: Request, body: SetActiveRequest):
    user = req.state.user
    service = SessionService()
    session = await service.get_session(body.session_id)
    if not session or session.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    await service.set_active_session(user["user_id"], body.session_id)
    req.state.session_id = body.session_id
    return {"status": "ok"}


@router.get("/{session_id}")
async def get_session(req: Request, session_id: str):
    user = req.state.user
    service = SessionService()
    session = await service.get_session(session_id)
    if not session or session.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}")
async def update_session(req: Request, session_id: str, body: UpdateSessionRequest):
    user = req.state.user
    service = SessionService()
    session = await service.get_session(session_id)
    if not session or session.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    await service.update_title(session_id, body.title)
    return {"status": "ok"}


@router.get("/{session_id}/messages")
async def list_messages(req: Request, session_id: str, limit: int = 50):
    user = req.state.user
    session_service = SessionService()
    session = await session_service.get_session(session_id)
    if not session or session.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    message_service = MessageService()
    return await message_service.list_messages(session_id, limit=limit)

