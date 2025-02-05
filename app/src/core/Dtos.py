from typing import Optional
from pydantic import BaseModel, Field, field_validator
from database.models import UserRole

# region User


class UserCreateDto(BaseModel):
    telegram_id: int
    telegram_username: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=15)
    role: Optional[UserRole] = None
    first_name: Optional[str] = Field(None, max_length=64)
    last_name: Optional[str] = Field(None, max_length=64)
    password: Optional[bytes] = None

    @field_validator('password')
    def encode_password(cls, v):
        if isinstance(v, str):
            return v.encode('utf-8')
        return v


class UserDto(BaseModel):
    id: int
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=15)
    role: Optional[UserRole] = None
    first_name: Optional[str] = Field(None, max_length=64)
    last_name: Optional[str] = Field(None, max_length=64)
# endregion
# region Token


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    phone_number: str | None = None
    role: str | None = None

    @classmethod
    def from_payload(cls, payload: dict):
        data = {
            "phone_number": payload.get("sub"),
            "role": payload.get("role")
        }
        return cls(**data)
# endregion


class LoginDto(BaseModel):
    phone_number: str
    password: bytes

    @field_validator('password')
    def encode_password(cls, v):
        if isinstance(v, str):
            return v.encode('utf-8')
        return v
