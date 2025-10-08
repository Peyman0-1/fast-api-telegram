from uvicorn import Config, Server
from src.core.api import api_app
import os

APP_ENV = os.getenv('APP_ENV', "production")

UVICORN_LOG_LEVEL = "debug" if APP_ENV == "development" else "error"

server_config = Config(
    app=api_app,
    host="0.0.0.0",
    port=8000,
    log_level=UVICORN_LOG_LEVEL
)


async def runserver():
    webserver = Server(server_config)
    await webserver.serve()
