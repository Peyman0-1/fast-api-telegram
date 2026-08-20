from typing import Tuple, TypeVar, Generic, Type, Optional, List, Dict, Any
from .models import AbstractBase, User, AuthSession, get_utc_now
from sqlalchemy import select, delete, and_, cast, String, func, insert, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import bcrypt

T = TypeVar('T', bound=AbstractBase)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
        self.logger = logging.getLogger(__name__)

    async def get_by_id(self, id: int) -> Optional[T]:
        return await self.session.get(
            entity=self.model,
            ident=id
        )

    async def get_all(self) -> List[T]:
        all_data = await self.session.execute(select(self.model))
        result = all_data.scalars().all()
        return list(result)

    async def get_paginated(
        self,
        page: int,
        page_size: int,
        sortby: Optional[str] = None,
        direction: Optional[str] = None,
        search: Optional[str] = None,
        search_fields: list[str] | None = None,
        exact_filter: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[T], int]:
        offset = (page - 1) * page_size
        try:
            query = select(self.model)

            if exact_filter:
                for field, value in exact_filter.items():
                    col = getattr(self.model, field, None)
                    if col is not None:
                        query = query.where(col == value)

            if search and search_fields:
                conditions = []
                for field in search_fields:
                    col = getattr(self.model, field, None)
                    if col is not None:
                        conditions.append(
                            cast(col, String).ilike(f"%{search}%")
                        )
                if conditions:
                    query = query.where(or_(*conditions))

            count_query = select(func.count()).select_from(query.subquery())
            total_count_result = await self.session.execute(count_query)
            total_count = total_count_result.scalar() or 0

            if sortby:
                col = getattr(self.model, sortby, None)
                if col is not None:
                    if direction and direction.lower() == "desc":
                        query = query.order_by(col.desc())
                    else:
                        query = query.order_by(col.asc())

            query = query.offset(offset).limit(page_size)

            result = await self.session.execute(query)

            return list(result.scalars().all()), total_count

        except SQLAlchemyError as e:
            self.logger.exception(
                "Database error occurred during object retrieval"
            )
            raise e

    async def create(self, obj_in: dict) -> T:
        obj = self.model(**obj_in)
        self.session.add(obj)
        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.exception(
                "Database error occurred during object creation."
            )
            await self.session.rollback()
            raise e
        else:
            await self.session.refresh(obj)
        return obj

    async def update(self, id: int, obj_in: dict) -> Optional[T]:
        obj = await self.session.get(
            entity=self.model,
            ident=id
        )

        if not obj:
            return None

        for key, value in obj_in.items():
            setattr(obj, key, value)

        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.exception(
                "Database error occurred during updating object."
            )
            await self.session.rollback()
            raise e
        else:
            await self.session.refresh(obj)

        return obj

    async def delete(self, id: int) -> bool:
        obj = await self.session.get(entity=self.model, ident=id)
        if not obj:
            return False

        try:
            await self.session.delete(obj)
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.exception(
                "Database error occurred during object deletion."
            )
            await self.session.rollback()
            raise e
        return True

    async def bulk_delete(self, list_ids: List[int]) -> None:
        if len(list_ids) == 0:
            return
        try:
            await self.session.execute(
                delete(self.model).where(self.model.id.in_(list_ids))
            )
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.exception(
                "Database error occurred during bulk object deletion."
            )
            await self.session.rollback()
            raise e

    async def bulk_add(self, objects: List[dict]) -> None:
        try:
            stmt = insert(self.model).values(objects)
            await self.session.execute(stmt)
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.exception(
                "Database error occurred during bulk object creation."
            )
            await self.session.rollback()
            raise e


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=User)

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        user = await self.session.execute(
            select(User).filter(User.phone_number == phone_number)
        )
        return user.scalar()

    async def create(self, obj_in: dict) -> User:
        # Hash password if present
        if obj_in.get("password"):
            password = obj_in["password"]
            # Encode to bytes if it's a string
            if isinstance(password, str):
                password = password.encode('utf-8')
            obj_in["password"] = bcrypt.hashpw(password, bcrypt.gensalt())
        return await super().create(obj_in)

    async def update(self, id: int, obj_in: dict) -> Optional[User]:
        # Hash password if present and different from current
        if obj_in.get("password"):
            user = await self.get_by_id(id)
            if user:
                new_password = obj_in["password"]
                # Encode new password to bytes if it's a string
                if isinstance(new_password, str):
                    new_password = new_password.encode('utf-8')
                
                # Get current password as bytes
                current_password = user.password
                if isinstance(current_password, str):
                    current_password = current_password.encode('utf-8')
                
                # Only hash if password is different
                if current_password != new_password:
                    obj_in["password"] = bcrypt.hashpw(new_password, bcrypt.gensalt())
        
        return await super().update(id, obj_in)


class AuthSessionRepository(BaseRepository[AuthSession]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=AuthSession)

    async def get_session(self, session_id: int) -> Optional[AuthSession]:
        result = await self.session.execute(
            select(AuthSession)
            .options(joinedload(AuthSession.user))
            .where(
                and_(
                    AuthSession.id == session_id,
                    AuthSession.is_active.is_(True)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_session_by_token(self, token: str) -> Optional[AuthSession]:
        result = await self.session.execute(
            select(AuthSession)
            .options(joinedload(AuthSession.user))
            .where(
                and_(
                    AuthSession.token == token,
                    AuthSession.is_active.is_(True)
                )
            )
        )
        return result.scalar_one_or_none()