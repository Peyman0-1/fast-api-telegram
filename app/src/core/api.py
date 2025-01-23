from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram_bot import application
import logging

logger = logging.getLogger(__name__)
fast_api = FastAPI()


@fast_api.get("/")
def index():
    return Response("OK")


@fast_api.post("/webhook")
async def get_webhook(request: Request):
    update = Update.de_json(data=await request.json(), bot=application.bot)

    await application.update_queue.put(update)

    return Response("OK")
