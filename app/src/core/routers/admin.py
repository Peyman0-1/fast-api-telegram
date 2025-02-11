from typing import Dict, Type, List, Annotated
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi import Header
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import sessionmaker
from database.repositories import BaseRepository
from database.models import User, UserRole
from database.models import BaseModel as DbBaseModel
from jwt import InvalidTokenError
from .. import Dtos
from ..services import AuthService
from ..dependencies import auth_dep


async def authorize(
        authorization: Annotated[str | None, Header()] = None,
        auth_service: AuthService = Depends(auth_dep)
):
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Authorization header missing."
        )

    try:
        identity: Dtos.TokenData = await auth_service.verify_token(
            token=authorization.replace("Bearer ", "")
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is invalid."
        )

    if not (
        auth_service.is_authorized(identity, UserRole.ADMIN) or
        auth_service.is_authorized(identity, UserRole.SUPERUSER)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You hav'nt access to this route."
        )


async def db_repository(model_name: str):
    if model_name not in MODELS:
        raise HTTPException(404, "model not found.")
    model: DbBaseModel = MODELS[model_name].get("model")
    session: AsyncSession = sessionmaker()
    db_repo: BaseRepository = BaseRepository(session, model)
    try:
        yield db_repo
    finally:
        await session.close()

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[
        Depends(authorize),
    ]
)

# register models in this dict
MODELS: Dict[str, Dict[str, Type[BaseModel] | Type[DbBaseModel]]] = {
    "User": {
        "dto": Dtos.UserCreateDto,
        "model": User
    },
}


@admin_router.get("/", response_model=Dict[str, List[str]])
async def get_models_name():
    return {
        "models": list(MODELS.keys())
    }


@admin_router.get("/{model_name}/")
async def get_all(
    model_name: str,
    page: int = 1,
    page_size: int = 20,
    db_repository: BaseRepository = Depends(db_repository)
):
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if not (page_size in range(1, 101)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
        )

    objects = await db_repository.get_paginated(
        page=page,
        page_size=page_size
    )
    dto: BaseModel = MODELS[model_name].get("dto")

    result = [dto.model_validate(model) for model in objects]

    return result


@admin_router.post("/{model_name}/")
async def create_new(
    new_model: BaseModel,
    db_repository: BaseRepository = Depends(db_repository)
):

    await db_repository.create(new_model.model_dump())

    return Response()


@admin_router.get("/{model_name}/{id}")
async def get_model(
    model_name: str,
    id: int,
    db_repository: BaseRepository = Depends(db_repository)
):
    db_object = await db_repository.get_by_id(id)
    if not db_object:
        raise HTTPException(status_code=404, detail="Not found")

    dto = MODELS[model_name].get('dto')

    return dto.model_validate(db_object)


@admin_router.put("/{model_name}/{id}")
async def update_model(
    model_name: str,
    id: int,
    update_model: BaseModel,
    db_repository: BaseRepository = Depends(db_repository)
):
    try:
        result = await db_repository.update(id, update_model.model_dump())

    except SQLAlchemyError:
        raise HTTPException(
            status_code=406,
            detail="there is a problem"
        )

    return MODELS[model_name].get("dto").model_validate(result)


@admin_router.delete("/{model_name}/{id}")
async def delete_model(
    model_name: str,
    id: int,
    db_repository: BaseRepository = Depends(db_repository)
):
    await db_repository.delete(id)
    return Response()
