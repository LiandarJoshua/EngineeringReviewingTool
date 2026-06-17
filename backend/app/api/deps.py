from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db as _get_db

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        yield session

# Re-export auth dependencies so routes can import from one place
from app.api.routes.auth import require_auth, get_current_user  # noqa: E402
