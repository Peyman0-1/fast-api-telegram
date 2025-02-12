from redis.asyncio import Redis
import os
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


HOST = os.getenv("REDIS_HOST")
PORT = int(os.getenv("REDIS_PORT"))
DB = int(os.getenv("REDIS_DB"))


class CacheService():
    redis: Redis

    def __init__(self):
        self.redis = Redis(host=HOST, port=PORT, db=DB)

    @staticmethod
    def calculate_timedelta(exp: datetime) -> timedelta:
        utc_now = datetime.now(timezone.utc)
        delta = exp - utc_now
        return delta

    async def set(self, key: str, value: str, exp: timedelta):
        try:
            await self.redis.set(key, value, ex=exp)
        except Exception as e:
            logger.exception(e)

    async def get(self, key: str) -> Optional[str]:
        try:
            value = await self.redis.get(key)
            return value if value else None

        except Exception as e:
            logger.exception(e)
            return None

    async def delete(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.exception(e)

    async def is_exists(self, key: str) -> bool:
        try:
            result = await self.redis.exists(key)
            return (result > 0)
        except Exception as e:
            logger.exception(e)
            return False

    async def close_redis(self):
        try:
            await self.redis.close()
        except Exception as e:
            logger.exception(e)
            raise e
