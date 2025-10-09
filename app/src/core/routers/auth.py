from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.params import Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import AuthSession
from src.core.custom_exceptions import InvalidCredentialsException
from src.core.services import AuthSesssionService, UserService
from src.core.dependencies import auth_dep, db_session_dep
from src.core import dtos
import logging
import os

logger = logging.getLogger(__name__)

auth_router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"]
)


async def user_service(session: AsyncSession = Depends(db_session_dep)):
    service: UserService = UserService(session)
    yield service


@auth_router.post("/login")
async def login(
    login_data: dtos.LoginDto,
    user_agent: Annotated[str, Header()],
    user_manager: UserService = Depends(user_service),
    auth_service: AuthSesssionService = Depends(auth_dep)
) -> JSONResponse:
    try:
        auth_session: AuthSession = await auth_service.authenticate(
            user_manager,
            user_agent=user_agent,
            **login_data.model_dump()  # phone_number and password
        )
        response = JSONResponse({"message": "Login successful"})
        response.set_cookie(
            key="token",
            value=auth_session.token,
            expires=auth_session.expires_at,
            domain=f".{os.getenv('APP_DOMAIN', 'localhost')}",
            max_age=int(
                (auth_session.expires_at - datetime.now(timezone.utc))
                .total_seconds()
            ),
            httponly=True,
            samesite="none",
            secure=True,
            path="/"
        )

    except InvalidCredentialsException:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid credentials")
    except Exception:
        logger.exception("Unexpected error during login")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")
    return response


@auth_router.get("/me")
async def get_me(
    token: Annotated[str | None, Cookie()] = None,
    auth_manager: AuthSesssionService = Depends(auth_dep)
) -> dtos.UserDto:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="i need a cookie."
        )
    try:
        session = await auth_manager.get_session(token)
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="i need a cookie"
        )

    response = dtos.UserDto.model_validate(session.user)
    return response


@auth_router.post("/logout")
async def logout(
    token: Annotated[str | None, Cookie()] = None,
    auth_manager: AuthSesssionService = Depends(auth_dep)
) -> JSONResponse:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="i need a cookie."
        )
    try:
        await auth_manager.revoke_session(token)
    except Exception:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="session doesn't exist."
        )

    response = JSONResponse({"message": "Logged out."})
    response.delete_cookie("session_id")

    return response


@auth_router.post("/reset-password")
async def reset_password(
    token: Annotated[str | None, Cookie()] = None,
    auth_manager: AuthSesssionService = Depends(auth_dep)
):
    raise NotImplementedError()
