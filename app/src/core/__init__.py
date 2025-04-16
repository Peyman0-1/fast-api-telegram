from uvicorn import Config, Server
from .api import fast_api


server_config = Config(
    app=fast_api,
    host="0.0.0.0",
    port=8000
)


async def runserver():
    webserver = Server(server_config)
    await webserver.serve()
