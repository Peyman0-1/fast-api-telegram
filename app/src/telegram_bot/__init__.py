from .custom_context import CustomContext
from os import getenv
from telegram.ext import Application, ContextTypes
from .handler_routes import HANDLERS

TOKEN = getenv("TELEGRAM_TOKEN")
context_types = ContextTypes(context=CustomContext)
application = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .context_types(context_types)
    .build()
)
application.add_handlers(HANDLERS)
