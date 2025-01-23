from typing import TypeVar, Generic, Type, Optional, List
from base_model import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import logging

T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
        self.logger = logging.getLogger(__name__)

    async def get_by_id(self, id: int) -> Optional[T]:
        return await self.session.get(
            entity=self.model,
            id=id
        )

    async def get_all(self) -> List[T]:
        result = await self.session.execute(self.model.select())
        return result

    async def create(self, obj_in: dict) -> T:
        obj = self.model(**obj_in)
        self.session.add(obj)
        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(e)
            await self.session.rollback()
        else:
            await self.session.refresh()

    async def update(self, id: int, obj_in: dict) -> Optional[T]:
        obj = await self.session.get(
            entity=self.model,
            id=id
        )

        if not obj:
            return None

        for key, value in obj_in.items():
            setattr(obj, key, value)

        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(e)
            await self.session.rollback()
        else:

            await self.session.refresh(obj)

        return obj

    async def delete(self, id: int) -> bool:
        obj = await self.session.get(entity=T, id=id)
        if not obj:
            return False

        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(e)
            await self.session.rollback()
        else:
            await self.session.delete(obj)
        return True
