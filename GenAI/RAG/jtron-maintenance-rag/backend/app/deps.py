from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import COOKIE_NAME, read_session_token
from app.db import get_db
from app.models import User


def current_user(
    jtron_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    if not jtron_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    user_id = read_session_token(jtron_session)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user
