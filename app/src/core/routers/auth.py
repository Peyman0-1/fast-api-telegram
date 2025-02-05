from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import sessionmaker
from ..services import AuthService, UserService
from .. import Dtos
import logging

logger = logging.Logger(__name__)

auth_router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)


async def user_service():
    session: AsyncSession = sessionmaker()
    service: UserService = UserService(session)

    try:
        yield service
    finally:
        await session.close()


async def auth_service():
    yield AuthService()


@auth_router.post("/login/")
async def login(
    login_data: Dtos.LoginDto,
    user_manager: UserService = Depends(user_service),
    auth_manager: AuthService = Depends(auth_service)
) -> Dtos.Token:
    try:
        token: Dtos.Token = await auth_manager.authenticate(
            user_manager,
            **login_data.model_dump()
        )

    except Exception as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=str(e)

        )
    return JSONResponse(token.model_dump())


@auth_router.get("/logout/")
async def logout(tokens_data: Dtos.Token):
    # add refresh and access tokens in blacklist(Redis)

    raise NotImplementedError()


@auth_router.get("/refresh/")
async def refresh() -> Dtos.Token:
    raise NotImplementedError()
