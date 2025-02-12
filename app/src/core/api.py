from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram_bot import application
import logging
from .routers import auth, admin


logger = logging.getLogger(__name__)
fast_api = FastAPI()

# region add the routes in this region #
fast_api.include_router(auth.auth_router)
fast_api.include_router(admin.admin_router)

# endregion -------------------------- #


@fast_api.get("/")
def index():
    return Response("OK")


@fast_api.post("/webhook")
async def get_webhook(request: Request):
    update = Update.de_json(data=await request.json(), bot=application.bot)

    await application.update_queue.put(update)

    return Response("OK")
