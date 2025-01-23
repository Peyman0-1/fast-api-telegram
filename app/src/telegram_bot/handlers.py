import logging
from telegram import Update
from .custom_context import CustomContext

logger = logging.getLogger(__name__)


async def start(update: Update, context: CustomContext) -> None:
    logger.info(f"bot is started with : {update.effective_user.id}")

    await context.bot.send_message(update.effective_chat.id, text="bot is on.")
