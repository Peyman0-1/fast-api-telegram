from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from .services import AuthService
from src.database.config import SessionFactory


async def db_session_dep():
    async with SessionFactory() as session:
        yield session


async def auth_dep(session: AsyncSession = Depends(db_session_dep)):
    service: AuthService = AuthService(session)
    yield service
