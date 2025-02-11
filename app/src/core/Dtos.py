from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from database.models import UserRole
from datetime import datetime, timezone
# region User


class UserCreateDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    refresh_token: Optional[str] = None
    token_type: str


class TokenData(BaseModel):
    phone_number: str | None = None
    role: str | None = None
    exp: datetime

    @classmethod
    def from_payload(cls, payload: dict):
        exp_timestampt = payload.get("exp")
        if isinstance(exp_timestampt, int):
            exp_timestampt = datetime.fromtimestamp(
                exp_timestampt, timezone.utc
            )

        data = {
            "phone_number": payload.get("sub"),
            "role": payload.get("role"),
            "exp": exp_timestampt
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
