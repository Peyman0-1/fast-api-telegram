from sqlalchemy.orm import DeclarativeBase
from enum import Enum
from sqlalchemy import Enum as AlchemyEnum
from sqlalchemy import String, BigInteger, DateTime, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    USER = "user"


class BaseModel(DeclarativeBase):
    pass


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True
    )
    telegram_username: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        nullable=True
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True
    )
    role: Mapped[UserRole] = mapped_column(
        AlchemyEnum(UserRole),
        default=UserRole.USER,
        nullable=False
    )
    first_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True
    )
    last_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False
    )
    password: Mapped[bytes | None] = mapped_column(
        LargeBinary(60),
        unique=False,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id{self.telegram_id},\
              username={self.tlegram_username})>"
