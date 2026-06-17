"""JWT authentication.

Single admin account configured via env vars ADMIN_EMAIL / ADMIN_PASSWORD.
POST /auth/login  → access token (30 days)
GET  /auth/me     → current user info
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import get_settings

router   = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2  = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

TOKEN_EXPIRE_DAYS = 30
ALGORITHM         = "HS256"


# ── Pydantic models ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    email:        str


class UserInfo(BaseModel):
    email: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_token(email: str) -> str:
    expire  = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _verify_token(token: Optional[str]) -> Optional[str]:
    """Return email from token or None if invalid."""
    if not token:
        return None
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return data.get("sub")
    except JWTError:
        return None


def _check_credentials(email: str, password: str) -> bool:
    admin_email    = getattr(settings, "admin_email", "admin@local.dev")
    admin_password = getattr(settings, "admin_password", "")
    if not admin_password:
        return False
    return email.lower() == admin_email.lower() and password == admin_password


# ── Public dependency ─────────────────────────────────────────────────────────

async def get_current_user(token: Optional[str] = Depends(_oauth2)) -> Optional[str]:
    """Returns the email of the authenticated user, or None if unauthenticated."""
    return _verify_token(token)


async def require_auth(token: Optional[str] = Depends(_oauth2)) -> str:
    """Use as a Depends() on protected routes. Raises 401 if not authenticated."""
    email = _verify_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if not _check_credentials(form.username, form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_token(form.username)
    return TokenResponse(access_token=token, email=form.username)


@router.get("/me", response_model=UserInfo)
async def me(email: str = Depends(require_auth)):
    return UserInfo(email=email)
