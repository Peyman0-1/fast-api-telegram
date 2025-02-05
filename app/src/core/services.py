from database.repositories import UserRepository
from database.models import User, UserRole
from datetime import timedelta, timezone, datetime
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

    async def get_user(self, phone_number: str) -> None:
        self.user = await self.db_repository.get_by_phone(phone_number)


class AuthService():
    SECRET_KEY = getenv('APP_SECRET_KEY')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

    @classmethod
    def create_access_token(
        cls,
        data: dict,
        expires_delta: timedelta = timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def create_refresh_token(
        cls,
        data: dict,
        expires_delta: timedelta = timedelta(
            minutes=REFRESH_TOKEN_EXPIRE_MINUTES
        )
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @staticmethod
    async def verify_token(cls, token: str) -> Dtos.TokenData:
        try:
            decoded_token = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
        except jwt.PyJWTError as error:
            raise jwt.InvalidTokenError("invalid or expired token") from error
        # TODO: Check decoded_token in Redis it needs await
        # if the token not in the redis blacklist be continue
        return Dtos.TokenData.from_payload(**decoded_token)

    @classmethod
    async def authenticate(
        cls,
        user_service: UserService,
        phone_number: str,
        password: bytes
    ) -> Dtos.Token:

        await user_service.get_user(phone_number)

        if not user_service.user:
            return

        is_password_match = user_service.check_password(password)

        if not is_password_match:
            raise Exception()

        refresh_token = cls.create_refresh_token(
            data={"sub": user_service.user.phone_number}
        )
        access_token = cls.create_access_token(
            data={
                "sub": user_service.user.phone_number,
                "role": user_service.user.role
            }
        )
        result = Dtos.Token(
            refresh_token=refresh_token,
            access_token=access_token,
            token_type="bearer"
        )
        return result

    @classmethod
    def is_authorized(
        cls,
        token_data: Dtos.TokenData,
        required_role: UserRole
    ) -> bool:
        return token_data.role == required_role.value()
