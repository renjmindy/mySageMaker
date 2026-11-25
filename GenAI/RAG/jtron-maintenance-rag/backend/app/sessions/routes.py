from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import current_user
from app.models import ChatSession, Message, User
from app.schemas import SessionCreate, SessionDetail, SessionOut, SessionRename

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_owned(db: Session, session_id: UUID, user: User) -> ChatSession:
    chat = db.get(ChatSession, session_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    return chat


@router.get("", response_model=list[SessionOut])
def list_sessions(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[ChatSession]:
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(db.execute(stmt).scalars())


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ChatSession:
    chat = ChatSession(user_id=user.id, title=payload.title or "New conversation")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ChatSession:
    stmt = (
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .options(selectinload(ChatSession.messages).selectinload(Message.citations))
    )
    chat = db.execute(stmt).scalar_one_or_none()
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    return chat


@router.patch("/{session_id}", response_model=SessionOut)
def rename_session(
    session_id: UUID,
    payload: SessionRename,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ChatSession:
    chat = _get_owned(db, session_id, user)
    chat.title = payload.title
    db.commit()
    db.refresh(chat)
    return chat


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    chat = _get_owned(db, session_id, user)
    db.delete(chat)
    db.commit()
