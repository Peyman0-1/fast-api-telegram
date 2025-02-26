from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import AuthSession
from ..services import AuthService, UserService
from ..dependencies import auth_dep, db_session_dep
from .. import dtos
import logging

logger = logging.Logger(__name__)

auth_router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)


async def user_service(session: AsyncSession = Depends(db_session_dep)):
    service: UserService = UserService(session)
    yield service


@auth_router.post("/login/")
async def login(
    login_data: dtos.LoginDto,
    response: Response,
    user_manager: UserService = Depends(user_service),
    auth_service: AuthService = Depends(auth_dep)
) -> Response:
    try:
        auth_session: AuthSession = await auth_service.authenticate(
            user_manager,
            **login_data.model_dump()  # phone_number and password
        )
        response.set_cookie(
            key="session_id",
            value=str(auth_session.id),
            expires=auth_session.expires_at,
            httponly=True,
            samesite="lax",
            path="/"
        )

    except Exception as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=str(e)

        )
    return response


@auth_router.get("/logout/")
async def logout(
    response: Response,
    session_id: Annotated[str | None, Cookie()] = None,
    auth_manager: AuthService = Depends(auth_dep)
):
    if not session_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="i need a cookie."
        )
    try:
        await auth_manager.get_session(int(session_id))
    except Exception:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="session doesn't exist."
        )
    response.delete_cookie("session_id")

    return response
