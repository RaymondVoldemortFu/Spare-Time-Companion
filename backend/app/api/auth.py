from datetime import timedelta

from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.crud import repositories as repo
from app.models.domain import InviteCode, User, now_utc
from app.schemas.api import InviteCreate, LoginRequest, RegisterRequest, TokenResponse
from app.services.invites import generate_invite_code


router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user={"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    user = repo.users.by_email(session, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError("bad_credentials", "Invalid email or password", 401)
    return _token_for(user)


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, session: SessionDep) -> TokenResponse:
    if repo.users.by_email(session, payload.email):
        raise AppError("email_exists", "Email is already registered", 409)
    if not repo.invites.consume(session, payload.invite_code):
        raise AppError("bad_invite", "Invite code is invalid or exhausted", 403)
    user = repo.users.create(
        session,
        User(
            email=payload.email,
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
            role="user",
        ),
    )
    return _token_for(user)


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}


@router.post("/invites")
def create_invite(payload: InviteCreate, session: SessionDep, admin: AdminUser) -> dict:
    code = generate_invite_code()
    while repo.invites.by_code(session, code):
        code = generate_invite_code()
    invite = repo.invites.create(
        session,
        InviteCode(
            code=code,
            max_uses=payload.max_uses,
            created_by=admin.id,
            expires_at=now_utc() + timedelta(hours=payload.ttl_hours),
        ),
    )
    return {
        "id": invite.id,
        "code": invite.code,
        "max_uses": invite.max_uses,
        "used_count": invite.used_count,
        "expires_at": invite.expires_at,
        "is_active": invite.is_active,
    }


@router.get("/invites")
def list_invites(session: SessionDep, _: AdminUser) -> list[dict]:
    return [
        {
            "id": invite.id,
            "code": invite.code,
            "max_uses": invite.max_uses,
            "used_count": invite.used_count,
            "is_active": invite.is_active,
            "expires_at": invite.expires_at,
            "available": invite.is_active
            and invite.used_count < invite.max_uses
            and invite.expires_at > now_utc(),
        }
        for invite in repo.invites.list(session, limit=200)
    ]
