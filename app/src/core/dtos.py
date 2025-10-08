from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic import model_validator, field_validator
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

    @field_validator('password', mode='before')
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


class ResetPasswordDto(BaseModel):
    old_password: bytes
    new_password: bytes
    new_password_repeat: bytes

    @field_validator(
        'old_password',
        'new_password',
        'confirm_new_password',
        mode='before'
    )
    def encode_passwords(cls, v):
        if isinstance(v, str):
            return v.encode('utf-8')
        return v

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.new_password != self.new_password_repeat:
            raise ValueError("New password and confirmation do not match.")
        return self


class LoginDto(BaseModel):
    phone_number: str
    password: bytes

    @field_validator('password', mode='before')
    def encode_password(cls, v):
        if isinstance(v, str):
            return v.encode('utf-8')
        return v
# endregion
