from telegram.ext import CommandHandler
from .handlers import start


START = CommandHandler("start", start)

HANDLERS = [
    START,
]
