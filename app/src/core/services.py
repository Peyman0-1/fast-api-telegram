from src.database.repositories import UserRepository, AuthSessionRepository
from src.database.models import User, AuthSession
from datetime import timedelta, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from .custom_exceptions import InvalidCredentialsException
from . import dtos
import bcrypt
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related operations."""
    
    def __init__(self, session: AsyncSession):
        self.db_repository = UserRepository(session)

    @staticmethod
    def hash_password(password: str | bytes) -> bytes:
        """Hash password using bcrypt."""
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt())

    def check_password(self, user: User, password: str | bytes) -> bool:
        """Verify password against stored hash."""
        if not user.password:
            return False

        # Encode password if it's a string
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        # Handle stored password (could be str or bytes)
        db_password = user.password
        if isinstance(db_password, str):
            db_password = db_password.encode('utf-8')

        return bcrypt.checkpw(password, db_password)

    async def create_user(self, new_user: dtos.UserCreateDto) -> dtos.UserDto:
        """Create new user with hashed password."""
        user_data = new_user.model_dump()
        
        # Hash password before storing
        if "password" in user_data and user_data["password"]:
            user_data["password"] = self.hash_password(user_data["password"])
            
        created_user = await self.db_repository.create(user_data)
        return dtos.UserDto.model_validate(created_user)

    async def get_user(self, phone_number: str) -> User | None:
        """Retrieve user by phone number."""
        return await self.db_repository.get_by_phone(phone_number)


class AuthService:
    """Service for authentication and session management."""
    
    SESSION_EXPIRE_DELTA = timedelta(days=7)

    def __init__(self, session: AsyncSession):
        self.db_repository = AuthSessionRepository(session)

    async def create_session(
        self,
        user_id: int,
        user_agent: str | None,
        expires_delta: timedelta = SESSION_EXPIRE_DELTA
    ) -> AuthSession:
        """Create new authentication session."""
        new_session = await self.db_repository.create({
            "user_id": user_id,
            "user_agent": user_agent,
            "expires_at": datetime.now(timezone.utc) + expires_delta
        })
        return new_session

    async def revoke_session(self, token: str):
        """Revoke authentication session by token."""
        session = await self.db_repository.get_session_by_token(token)
        
        # Raise exception if session doesn't exist
        if not session:
            raise InvalidCredentialsException("Session doesn't exist")
            
        await self.db_repository.update(session.id, {"is_active": False})

    async def get_session(self, token: str) -> AuthSession:
        """Retrieve and validate authentication session."""
        session = await self.db_repository.get_session_by_token(token)
        
        if not session or not session.is_active:
            raise InvalidCredentialsException("Invalid or inactive session")

        if session.expires_at and session.expires_at < datetime.now(timezone.utc):
            raise InvalidCredentialsException("Session expired")

        return session

    async def authenticate(
        self,
        user_service: UserService,
        user_agent: str,
        phone_number: str,
        password: str | bytes
    ) -> AuthSession:
        """Authenticate user with phone number and password."""
        user = await user_service.get_user(phone_number)
        
        if not user:
            raise InvalidCredentialsException("Username or password is incorrect")

        if not user_service.check_password(user, password):
            raise InvalidCredentialsException("Username or password is incorrect")

        session = await self.create_session(user.id, user_agent)
        return session