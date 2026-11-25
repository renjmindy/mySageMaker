import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.db import SessionLocal, get_db
from app.deps import current_user
from app.models import ChatSession, Citation, Message, User
from app.rag_client import Citation as CitationChunk
from app.rag_client import RagError, Token, get_rag_client
from app.schemas import SendMessageIn

router = APIRouter(prefix="/sessions", tags=["messages"])


def _history_for(db: Session, session_id: UUID) -> list[dict[str, str]]:
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    return [{"role": m.role, "content": m.content} for m in db.execute(stmt).scalars()]


@router.post("/{session_id}/messages")
async def send_message(
    session_id: UUID,
    payload: SendMessageIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    chat = db.get(ChatSession, session_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")

    user_msg = Message(session_id=session_id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    history = _history_for(db, session_id)
    rag = get_rag_client()

    async def event_stream():
        collected_text: list[str] = []
        collected_citations: list[CitationChunk] = []
        error_message: str | None = None

        try:
            async for chunk in await rag.query(payload.content, history):
                if isinstance(chunk, Token):
                    collected_text.append(chunk.text)
                    yield {"event": "token", "data": chunk.text}
                elif isinstance(chunk, CitationChunk):
                    collected_citations.append(chunk)
                    yield {
                        "event": "citation",
                        "data": json.dumps(
                            {
                                "source": chunk.source,
                                "page": chunk.page,
                                "snippet": chunk.snippet,
                                "score": chunk.score,
                            }
                        ),
                    }
                elif isinstance(chunk, RagError):
                    error_message = chunk.message
                    yield {"event": "error", "data": chunk.message}
                    break
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            yield {"event": "error", "data": error_message}

        full_text = "".join(collected_text)
        persist_db: Session = SessionLocal()
        try:
            assistant_msg = Message(
                session_id=session_id,
                role="assistant",
                content=full_text
                if full_text
                else f"[error] {error_message or 'no response'}",
            )
            persist_db.add(assistant_msg)
            persist_db.flush()
            for c in collected_citations:
                persist_db.add(
                    Citation(
                        message_id=assistant_msg.id,
                        source_doc=c.source,
                        page=c.page,
                        snippet=c.snippet,
                        score=c.score,
                    )
                )
            chat_row = persist_db.get(ChatSession, session_id)
            if chat_row is not None and chat_row.title == "New conversation":
                chat_row.title = payload.content[:80]
            persist_db.commit()
            yield {"event": "done", "data": str(assistant_msg.id)}
        finally:
            persist_db.close()

    return EventSourceResponse(event_stream())


@router.get("/{session_id}/messages")
def list_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    chat = db.get(ChatSession, session_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .options(selectinload(Message.citations))
    )
    return list(db.execute(stmt).scalars())
