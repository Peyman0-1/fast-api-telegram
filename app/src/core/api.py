import logging
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from src.core.routers import auth, admin
from src.telegram_bot import application
from telegram import Update
import os

logger = logging.getLogger(__name__)
fast_api = FastAPI()


# region add the routes in this region #
fast_api.include_router(auth.auth_router)
fast_api.include_router(admin.admin_router)

APP_DOMAIN = os.getenv('APP_DOMAIN', 'localhost')
FRONTEND_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1",
    "https://127.0.0.1",
    "http://localhost",
    f"http://{APP_DOMAIN}",
    f"https://{APP_DOMAIN}",
    f"http://www.{APP_DOMAIN}",
    f"https://www.{APP_DOMAIN}",
]
ALLOWED_HOSTS = [
    APP_DOMAIN,
    f"www.{APP_DOMAIN}",
    "localhost",
    "127.0.0.1",
]

fast_api.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
fast_api.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)
# endregion -------------------------- #


@fast_api.get("/")
def index():
    return Response("OK")


@fast_api.post("/webhook")
async def get_webhook(request: Request):
    update = Update.de_json(data=await request.json(), bot=application.bot)

    await application.update_queue.put(update)

    return Response("OK")
