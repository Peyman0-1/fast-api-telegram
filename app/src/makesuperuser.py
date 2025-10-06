import os
import asyncio
import logging
from dotenv import load_dotenv


load_dotenv()
APP_ENV = os.getenv('APP_ENV', "production")

logging.basicConfig(
    level=(logging.DEBUG if APP_ENV == "development" else logging.ERROR),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run():
    from src.database.config import SessionFactory
    from src.core.dtos import UserCreateDto, UserRole
    from src.core.services import UserService

    phone_number = input("Enter a phone Number:")
    password = input("Enter a password:")

    async with SessionFactory() as sf:
        user_service = UserService(sf)
        user = UserCreateDto(
            phone_number=phone_number,
            password=password,
            role=UserRole.SUPERUSER
        )  # type: ignore
        await user_service.create_user(user)
        logger.info("User has been created.")

asyncio.run(run())
