from enum import Enum
from fastapi import Query
from typing import Dict, Type, List
from typing import TypedDict, Optional, NotRequired
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import Response, JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories import BaseRepository, UserRepository
from src.database.models import User, AbstractBase, UserRole
from src.core import dtos
from src.core.dependencies import authorize_dep, db_session_dep


async def db_repository(
    model_name: str,
    session: AsyncSession = Depends(db_session_dep)
):
    if model_name not in MODELS:
        raise HTTPException(404, "model not found.")
    model: Type[AbstractBase] = MODELS[model_name].get("model")

    special_repo = MODELS[model_name].get("repository")
    if special_repo:
        db_repo = special_repo(session)  # type: ignore
    else:

        db_repo = BaseRepository(session, model)
    yield db_repo

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin v1"],
    dependencies=[
        Depends(authorize_dep([
            UserRole.ADMIN,
            UserRole.SUPERUSER
        ])),
    ]
)


class ModelsConfig(TypedDict):
    dto: Type[BaseModel]
    model: Type[AbstractBase]
    repository: NotRequired[Type[BaseRepository]]


# register models in this dict
MODELS: Dict[str, ModelsConfig] = {
    "user": {
        "dto": dtos.UserCreateDto,
        "model": User,
        "repository": UserRepository
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
    return dto_class(**data)  # type: ignore


@admin_router.get("/", response_model=Dict[str, List[str]])
async def get_models_name():
    return JSONResponse({
        "models": list(MODELS.keys())
    })


class SortOrder(str, Enum):
    ascending = "asc"
    descending = "desc"


@admin_router.get("/{model_name}")
async def get_all(
    model_name: str,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    direction: SortOrder | None = None,
    search: str | None = None,
    search_fields: Optional[List[str]] = Query(None),
    db_repository: BaseRepository = Depends(db_repository)
):
    if page_size > 1001 or page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
        )
    objects = await db_repository.get_paginated(
        page=page,
        page_size=page_size,
        sortby=sort_by,
        direction=direction,
        search=search,
        search_fields=search_fields,
    )
    dto: Type[BaseModel] = MODELS[model_name].get("dto")

    result = [dto.model_validate(model) for model in objects]

    return result


@admin_router.post("/{model_name}")
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
    new_record = await db_repository.create(
        dto_instance.model_dump()  # type: ignore
    )

    return MODELS[model_name].get("dto").model_validate(new_record)


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
            dto.model_dump(exclude_unset=True)  # type: ignore
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
