from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic import model_validator, field_validator
from src.database.models import UserRole
import re

# region Auth


class UserCreateDto(BaseModel):
    """DTO for creating a new user."""
    id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=32)
    phone_number: str = Field(..., max_length=15, pattern=r'^\+?[1-9]\d{1,14}$')
    role: Optional[UserRole] = None
    first_name: Optional[str] = Field(None, max_length=64)
    last_name: Optional[str] = Field(None, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format (E.164)."""
        # Remove any whitespace or dashes
        cleaned = re.sub(r'[\s\-]', '', v)
        if not re.match(r'^\+?[1-9]\d{1,14}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

    @model_validator(mode='after')
    def validate_contact_info(self):
        """Ensure at least one contact method is provided."""
        if not self.telegram_id and not self.phone_number:
            raise ValueError('At least one contact method (telegram_id or phone_number) is required')
        return self


class UserDto(BaseModel):
    """DTO for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=15)
    role: Optional[UserRole] = None
    first_name: Optional[str] = Field(None, max_length=64)
    last_name: Optional[str] = Field(None, max_length=64)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ResetPasswordDto(BaseModel):
    """DTO for password reset."""
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_repeat: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate new password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

    @model_validator(mode='after')
    def check_passwords_match(self):
        """Ensure new passwords match."""
        if self.new_password != self.new_password_repeat:
            raise ValueError("New password and confirmation do not match.")
        if self.old_password == self.new_password:
            raise ValueError("New password must be different from old password")
        return self


class LoginDto(BaseModel):
    """DTO for user login."""
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    password: str = Field(..., min_length=8)

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format (E.164)."""
        cleaned = re.sub(r'[\s\-]', '', v)
        if not re.match(r'^\+?[1-9]\d{1,14}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned


# endregion


def simplify_schema_for_admin(schema: dict[str, Any]) -> dict[str, Any]:
    """Simplify OpenAPI schema for admin panel display."""
    defs = schema.get("$defs", {})
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    simple = {}

    for name, prop in props.items():
        field = {}
        field["required"] = name in required

        # Handle anyOf
        variant = None
        nullable = False
        if "anyOf" in prop:
            for p in prop["anyOf"]:
                if p.get("type") != "null":
                    variant = p
                else:
                    nullable = True
        else:
            variant = prop
            if prop.get("type") == "null":
                nullable = True
                variant = {}

        if variant:
            if "$ref" in variant:
                ref_name = variant["$ref"].split("/")[-1]
                ref_def = defs.get(ref_name, {})
                if "enum" in ref_def:
                    field["type"] = "enum"
                    field["choices"] = ref_def["enum"]
                else:
                    field["type"] = ref_def.get("type", "string")
            else:
                field["type"] = variant.get("type")

            # Copy constraints from variant
            for key in ["maxLength", "format", "pattern"]:
                if key in variant:
                    field[key] = variant[key]

        field["nullable"] = nullable

        simple[name] = field

    return simple