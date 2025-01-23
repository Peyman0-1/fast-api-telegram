from base_app import BaseApp
from uvicorn import Config, Server
from .api import fast_api


class CoreApp(BaseApp):
    name = "core"
    server_conf: Config | None = None

    async def setup(self):
        self.server_conf = Config(
            app=fast_api,
            host="127.0.0.1",
            port=8000
        )

    async def run(self):
        webserver = Server(self.server_conf)
        await webserver.serve()
