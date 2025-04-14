from typing import Dict, Type, List, Annotated, TypedDict
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import Response, JSONResponse
from fastapi import Cookie
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database.repositories import BaseRepository
from database.models import User, UserRole, AuthSession, AbstractBase
from .. import dtos
from ..services import AuthService
from ..dependencies import auth_dep, db_session_dep


async def authorize(
        session_id: Annotated[str | None, Cookie()] = None,
        auth_service: AuthService = Depends(auth_dep),
) -> AuthSession:
    if not session_id:
        raise HTTPException(
            status_code=401, detail="Authorization cookie is missing."
        )

    try:
        identity: AuthSession = await auth_service.get_session(
            session_id=int(session_id)
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be authorized"
        )
    if not (
        identity.user.role == UserRole.ADMIN or
        identity.user.role == UserRole.SUPERUSER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this route."
        )
    return identity


async def db_repository(
    model_name: str,
    session: AsyncSession = Depends(db_session_dep)
):
    if model_name not in MODELS:
        raise HTTPException(404, "model not found.")
    model: Type[AbstractBase] = MODELS[model_name].get("model")
    db_repo: BaseRepository = BaseRepository(session, model)
    yield db_repo

admin_router = APIRouter(
    prefix="/v1/admin",
    tags=["admin v1"],
    dependencies=[
        Depends(authorize),
    ]
)


class ModelsConfig(TypedDict):
    dto: Type[BaseModel]
    model: Type[AbstractBase]


# register models in this dict
MODELS: Dict[str, ModelsConfig] = {
    "User": {
        "dto": dtos.UserCreateDto,
        "model": User
    },
}


async def get_dto_instance(
    request: Request,
    model_name: str
) -> Type[BaseModel]:
    model_config = MODELS.get(model_name)
    if not model_config:
        raise HTTPException(status_code=404, detail="Model not found")

    dto_class = model_config["dto"]
    data = await request.json()
    return dto_class(**data)


@admin_router.get("/", response_model=Dict[str, List[str]])
async def get_models_name():
    return JSONResponse({
        "models": list(MODELS.keys())
    })


@admin_router.get("/{model_name}/")
async def get_all(
    model_name: str,
    page: int = 1,
    page_size: int = 20,
    db_repository: BaseRepository = Depends(db_repository)
):
    if page_size > 101 or page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
        )

    objects = await db_repository.get_paginated(
        page=page,
        page_size=page_size
    )
    dto: Type[BaseModel] = MODELS[model_name].get("dto")

    result = [dto.model_validate(model) for model in objects]

    return result


@admin_router.post("/{model_name}/")
async def create_new(
    model_name: str,
    request: Request,
    db_repository: BaseRepository = Depends(db_repository)
):
    dto_instance = await get_dto_instance(request, model_name)

    # TODO: it's better that using a manager
    # instead of using directly of dbrepository
    # the manager class must have a base class for rules about functions
    # TODO: improve exeptions
    await db_repository.create(dto_instance.model_dump())

    return Response(status_code=201)


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
    request: Request,
    db_repository: BaseRepository = Depends(db_repository)
):
    try:
        dto = await get_dto_instance(request, model_name)
        result = await db_repository.update(
            id,
            dto.model_dump(exclude_unset=True)
        )
        return MODELS[model_name].get("dto").model_validate(result)

    except SQLAlchemyError:
        raise HTTPException(
            status_code=406,
            detail="there is a problem"
        )


@admin_router.delete("/{model_name}/{id}")
async def delete_model(
    id: int,
    db_repository: BaseRepository = Depends(db_repository)
):
    await db_repository.delete(id)
    return Response()
