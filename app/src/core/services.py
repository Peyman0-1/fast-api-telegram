from src.database.repositories import UserRepository, AuthSessionRepository
from src.database.models import User, AuthSession
from datetime import timedelta, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.custom_exceptions import InvalidCredentialsException
from src.core import dtos
import bcrypt
import logging

logger = logging.getLogger(__name__)


class UserService():
    db_repository: UserRepository

    def __init__(self, session: AsyncSession):
        self.db_repository = UserRepository(session)

    @staticmethod
    def hash_password(password: bytes) -> bytes:
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        return hashed_password

    def check_password(self, user: User, password: bytes) -> bool:
        if (not user.password):
            return False

        return bcrypt.checkpw(password, user.password)

    async def reset_pasword(
        self,
            phone_number: str,
            data: dtos.ResetPasswordDto
    ):
        # user = await self.get_user(phone_number)
        raise NotImplementedError()

    async def create_user(self, new_user: dtos.UserCreateDto) -> dtos.UserDto:
        new_user = await self.db_repository.create(
            new_user.model_dump()
        )  # type: ignore
        return dtos.UserDto.model_validate(new_user)

    async def get_user(self, phone_number: str) -> User | None:
        user = await self.db_repository.get_by_phone(phone_number)
        return user


class AuthSesssionService():
    SESSION_EXPIRE_DELTA = timedelta(days=7)

    db_repository: AuthSessionRepository

    def __init__(self, session: AsyncSession):
        self.db_repository = AuthSessionRepository(session)

    async def create_session(
        self,
        user_id: int,
        user_agent: str | None,
        expires_delta: timedelta = SESSION_EXPIRE_DELTA
    ) -> AuthSession:

        new_session: AuthSession = await self.db_repository.create(
            {
                "user_id": user_id,
                "user_agent": user_agent,
                "expires_at": datetime.now(timezone.utc) + expires_delta
            }
        )
        return new_session

    async def revoke_session(self, token: str):
        session = await self.db_repository.get_session_by_token(token)
        if session:
            await self.db_repository.update(
                session.id,
                obj_in={
                    "is_active": False
                }
            )

    # TODO: we need a revoke_old_sessions function
    # to terminate all old session after changing password

    async def get_session(self, token: str) -> AuthSession:
        session = await self.db_repository.get_session_by_token(token)
        if not session or not session.is_active:
            raise InvalidCredentialsException("You're unauthorized.")

        if session.expires_at < datetime.now(timezone.utc):
            raise InvalidCredentialsException("Session expired.")

        return session

    async def authenticate(
        self,
        user_service: UserService,
        user_agent: str,
        phone_number: str,
        password: bytes
    ) -> AuthSession:

        user = await user_service.get_user(phone_number)

        if not user:
            raise InvalidCredentialsException(
                "username or password is incorrect.")

        is_password_match = user_service.check_password(user, password)

        if not is_password_match:
            raise InvalidCredentialsException(
                "username or password is incorrect.")

        session = await self.create_session(
            user.id,
            user_agent,
        )
        return session
