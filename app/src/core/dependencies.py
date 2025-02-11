from .services import AuthService


async def auth_dep():
    service: AuthService = AuthService()
    try:
        yield service
    finally:
        await service.cache_service.close_redis()
