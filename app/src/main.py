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


async def main():
    from core import runserver
    from telegram_bot import application

    async with application:
        await application.start()
        await runserver()


if __name__ == "__main__":
    asyncio.run(main())
