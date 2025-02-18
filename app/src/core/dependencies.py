from .services import AuthService
from database.config import sessionmaker


async def auth_dep():
    service: AuthService = AuthService(sessionmaker())
    try:
        yield service
    finally:
        await service.db_repository.session.close()
