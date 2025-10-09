from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Cookie, Depends, HTTPException, status
from src.database.models import AuthSession, UserRole
from src.core.services import AuthSesssionService
from src.database.config import SessionFactory


async def db_session_dep():
    async with SessionFactory() as session:
        yield session


async def auth_dep(session: AsyncSession = Depends(db_session_dep)):
    service: AuthSesssionService = AuthSesssionService(session)
    yield service


def session_authorize_dep(acceptable_roles: List[UserRole]):
    async def _authorize(
            token: Annotated[str | None, Cookie()] = None,
            auth_service: AuthSesssionService = Depends(auth_dep),
    ) -> AuthSession:
        if not token:
            raise HTTPException(
                status_code=401, detail="Authorization cookie is missing."
            )

        try:
            identity: AuthSession = await auth_service.get_session(
                token=token
            )

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You must be authorized"
            )
        if identity.user.role not in acceptable_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this route."
            )
        return identity

    return _authorize
