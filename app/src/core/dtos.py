from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from src.database.models import UserRole

# region Auth


class UserCreateDto(BaseModel):
    id: Optional[int] = None
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=15)
    role: Optional[UserRole] = None
    first_name: Optional[str] = Field(None, max_length=64)
    last_name: Optional[str] = Field(None, max_length=64)
# endregion


class LoginDto(BaseModel):
    phone_number: str
    password: bytes

    @field_validator('password')
    def encode_password(cls, v):
        if isinstance(v, str):
            return v.encode('utf-8')
        return v
# endregion
