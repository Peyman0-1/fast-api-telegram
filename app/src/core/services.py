import string
import random
from database.repositories import UserRepository, TokenRepository
from database.models import User, Token, UserRole
from datetime import timedelta, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from . import Dtos
from os import getenv
import bcrypt
import jwt
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

        return bcrypt.checkpw(password, self.user.password)

    async def create_user(self, new_user: Dtos.UserCreateDto) -> Dtos.UserDto:
        if new_user.password:
            new_user.password = self.hash_password(new_user.password)

        new_user = await self.db_repository.create(new_user)
        return Dtos.UserDto(new_user.model_validate(new_user))

    async def get_user(self, phone_number: str) -> User | None:
        user = await self.db_repository.get_by_phone(phone_number)
        return user


class AuthService():
    SECRET_KEY = getenv('APP_SECRET_KEY')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

    db_repository: TokenRepository

    def __init__(self, session: AsyncSession):
        self.db_repository = TokenRepository(session)

    def create_access_token(
        self,
        data: dict,
        expires_delta: timedelta = timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    async def create_refresh_token(
        self,
        user_id: int,
        expires_delta: timedelta = timedelta(
            minutes=REFRESH_TOKEN_EXPIRE_MINUTES
        )
    ) -> str:
        choices = string.ascii_letters + string.digits
        new_token = ''.join(random.choice(choices) for i in range(32))

        await self.db_repository.create(
            {
                "user_id": user_id,
                "token": new_token,
                "expires_at": datetime.now(timezone.utc) + expires_delta
            }
        )

        return new_token

    async def expire_refresh_token(self, token: str):
        if token.startswith("Token"):
            token = token.replace("Token ", "")
        else:
            raise Exception("token is unsupported.")

        token: Token = await self.db_repository.get_by_token(token)

        if not token:
            raise Exception("there is no token found.")

        await self.db_repository.delete(token.id)

    async def verify_token(self, token: str) -> Dtos.TokenData:
        if token.startswith("Bearer"):
            token = token.replace("Bearer ", "")
            try:
                decoded_token = jwt.decode(
                    token,
                    self.SECRET_KEY,
                    algorithms=[self.ALGORITHM]
                )
                return Dtos.TokenData.from_payload(**decoded_token)

            except jwt.PyJWTError as error:
                raise jwt.InvalidTokenError(
                    "invalid or expired token") from error

        elif token.startswith("Token"):
            token = token.replace("Token ", "")
            user_token = await self.db_repository.get_by_token(token)
            if not user_token:
                raise Exception("Token is Invalid.")
            if user_token.expires_at < datetime.now(timezone.utc):
                raise Exception("Token is Expired.")

            return Dtos.TokenData(
                phone_number=user_token.user.phone_number,
                role=user_token.user.role,
                exp=user_token.expires_at
            )

        else:
            raise Exception("Invalid Authentication Method.")

    async def authenticate(
        self,
        user_service: UserService,
        phone_number: str,
        password: bytes
    ) -> Dtos.TokenResponseDto:

        user = await user_service.get_user(phone_number)

        if not user:
            raise Exception("username or password is incorrect.")

        is_password_match = user_service.check_password(user, password)

        if not is_password_match:
            raise Exception("username or password is incorrect.")

        refresh_token = await self.create_refresh_token(
            user_id=user.id,
            expires_delta=timedelta(
                minutes=self.REFRESH_TOKEN_EXPIRE_MINUTES
            )
        )
        access_token = self.create_access_token(
            data={
                "sub": user.phone_number,
                "role": user.role
            }
        )
        result = Dtos.TokenResponseDto(
            refresh_token=refresh_token,
            refresh_token_type="Token",
            access_token=access_token,
            access_token_type="Bearer",
        )
        return result

    @staticmethod
    def is_authorized(
        token_data: Dtos.TokenData,
        required_role: UserRole
    ) -> bool:
        return token_data.role == required_role.value()
