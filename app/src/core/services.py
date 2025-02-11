from database.repositories import UserRepository
from database.models import User, UserRole
from datetime import timedelta, timezone, datetime
from cache.services import CacheService
from . import Dtos
from os import getenv
import bcrypt
import jwt
import logging

logger = logging.getLogger(__name__)


class UserService():
    db_repository: UserRepository
    user: User | None

    def __init__(self, session, user=None):
        self.db_repository = UserRepository(session)
        self.user = user

    @staticmethod
    def hash_password(password: bytes) -> bytes:
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        return hashed_password

    def check_password(self, password: bytes) -> bool:
        if (not self.user.password):
            return False

        return bcrypt.checkpw(password, self.user.password)

    async def create_user(self, new_user: Dtos.UserCreateDto) -> None:
        if new_user.password:
            new_user.password = self.hash_password(new_user.password)
        await self.db_repository.create(new_user)

    async def get_user(self, phone_number: str) -> User | None:
        self.user = await self.db_repository.get_by_phone(phone_number)
        return self.user


class AuthService():
    SECRET_KEY = getenv('APP_SECRET_KEY')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

    cache_service: CacheService

    def __init__(self):
        self.cache_service = CacheService()

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
        data: dict,
        expires_delta: timedelta = timedelta(
            minutes=REFRESH_TOKEN_EXPIRE_MINUTES
        )
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.SECRET_KEY,
            algorithm=self.ALGORITHM
        )
        await self.cache_service.set(  # first we set refresh to redis
            encoded_jwt,
            expire.__str__(),  # i have no idea taht what should set in value
            expires_delta
        )
        return encoded_jwt

    async def verify_token(self, token: str) -> Dtos.TokenData:
        if (await self.cache_service.is_exists(token)):
            raise jwt.InvalidTokenError("invalid or expired token")

        try:
            decoded_token = jwt.decode(
                token,
                self.SECRET_KEY,
                algorithms=[self.ALGORITHM]
            )
        except jwt.PyJWTError as error:
            raise jwt.InvalidTokenError("invalid or expired token") from error

        return Dtos.TokenData.from_payload(**decoded_token)

    async def authenticate(
        self,
        user_service: UserService,
        phone_number: str,
        password: bytes
    ) -> Dtos.Token:

        await user_service.get_user(phone_number)

        if not user_service.user:
            raise Exception("username or password is incorrect.")

        is_password_match = user_service.check_password(password)

        if not is_password_match:
            raise Exception("username or password is incorrect.")

        refresh_token = await self.create_refresh_token(
            data={"sub": user_service.user.phone_number}
        )
        access_token = self.create_access_token(
            data={
                "sub": user_service.user.phone_number,
                "role": user_service.user.role
            }
        )
        result = Dtos.Token(
            refresh_token=refresh_token,
            access_token=access_token,
            token_type="Bearer"
        )
        return result

    @staticmethod
    def is_authorized(
        token_data: Dtos.TokenData,
        required_role: UserRole
    ) -> bool:
        return token_data.role == required_role.value()
