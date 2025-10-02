from .custom_context import CustomContext
from os import getenv
from telegram.ext import Application, ContextTypes
from .handler_routes import HANDLERS

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "no token")
context_types = ContextTypes(context=CustomContext)
application = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .context_types(context_types)
    .build()
)
application.add_handlers(HANDLERS)
