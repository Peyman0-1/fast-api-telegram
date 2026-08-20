from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import AuthSession
from src.core.custom_exceptions import InvalidCredentialsException
from src.core.services import AuthService, UserService
from src.core.dependencies import auth_dep, db_session_dep
from src.core import dtos
import logging
import os

logger = logging.getLogger(__name__)

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"]
)


async def user_service(session: AsyncSession = Depends(db_session_dep)):
    """Dependency provider for UserService."""
    yield UserService(session)


@auth_router.post("/login")
async def login(
    login_data: dtos.LoginDto,
    user_agent: Annotated[str | None, Header()] = None,
    user_manager: UserService = Depends(user_service),
    auth_service: AuthService = Depends(auth_dep)
) -> JSONResponse:
    """Authenticate user and create session."""
    try:
        auth_session: AuthSession = await auth_service.authenticate(
            user_manager,
            user_agent=user_agent or "unknown",
            **login_data.model_dump()
        )
        response = JSONResponse({"message": "Login successful"})
        
        # Calculate max_age in seconds
        max_age = int((auth_session.expires_at - datetime.now(timezone.utc)).total_seconds())
        
        # Determine secure flag based on environment
        is_production = os.getenv("APP_ENV", "development") == "production"
        app_domain = os.getenv("APP_DOMAIN", "localhost")
        
        response.set_cookie(
            key="token",
            value=auth_session.token,
            max_age=max_age,
            domain=f".{app_domain}" if app_domain != "localhost" else None,
            httponly=True,
            samesite="lax" if not is_production else "none",
            secure=is_production,
            path="/"
        )

    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    except Exception:
        logger.exception("Unexpected error during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error"
        )
        
    return response


@auth_router.get("/me")
async def get_me(
    token: Annotated[str | None, Cookie()] = None,
    auth_manager: AuthService = Depends(auth_dep)
) -> dtos.UserDto:
    """Get current authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing"
        )
    
    try:
        session = await auth_manager.get_session(token)
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return dtos.UserDto.model_validate(session.user)


@auth_router.post("/logout")
async def logout(
    token: Annotated[str | None, Cookie()] = None,
    auth_manager: AuthService = Depends(auth_dep)
) -> JSONResponse:
    """Revoke user session and clear authentication cookie."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing"
        )
    
    try:
        await auth_manager.revoke_session(token)
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session doesn't exist"
        )
    except Exception:
        logger.exception("Unexpected error during logout")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error"
        )

    response = JSONResponse({"message": "Logged out successfully"})
    
    # Delete cookie with matching parameters
    app_domain = os.getenv("APP_DOMAIN", "localhost")
    response.delete_cookie(
        key="token",
        domain=f".{app_domain}" if app_domain != "localhost" else None,
        path="/"
    )

    return response