from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import sessionmaker
from jwt import InvalidTokenError
from ..services import AuthService, UserService
from ..dependencies import auth_dep
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


@auth_router.post("/login/")
async def login(
    login_data: Dtos.LoginDto,
    user_manager: UserService = Depends(user_service),
    auth_service: AuthService = Depends(auth_dep)
) -> Dtos.Token:
    try:
        token: Dtos.Token = await auth_service.authenticate(
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
    # remove access token from redis

    raise NotImplementedError()


@auth_router.get("/refresh/")
async def refresh(
    authorization: Annotated[str | None, Header()] = None,
    user_manager: UserService = Depends(user_service),
    auth_service: AuthService = Depends(auth_dep)
) -> Dtos.Token:
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Authorization header missing."
        )

    try:
        token_data: Dtos.TokenData = await auth_service.verify_token(
            token=authorization.replace("Bearer ", "")
        )
        user = await user_manager.get_user(token_data.phone_number)

    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is invalid."
        )
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is invalid."
        )

    access_token = auth_service.create_access_token(
        data={
            "sub": user_manager.user.phone_number,
            "role": user_manager.user.role
        }
    )
    return Dtos.Token(access_token=access_token, token_type="Bearer")
