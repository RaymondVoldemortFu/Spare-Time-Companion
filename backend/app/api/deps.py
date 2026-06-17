from typing import Annotated

from fastapi import Depends, Header
from sqlmodel import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.crud.repositories import users
from app.db import get_session
from app.models.domain import User


SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep, authorization: Annotated[str | None, Header()] = None
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("unauthorized", "Missing bearer token", 401)
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise AppError("unauthorized", "Invalid bearer token", 401) from exc
    user = users.get(session, payload["sub"])
    if not user or not user.is_active:
        raise AppError("unauthorized", "User is inactive or not found", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise AppError("forbidden", "Admin permission required", 403)
    return user


AdminUser = Annotated[User, Depends(require_admin)]

