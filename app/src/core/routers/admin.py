from enum import Enum
from fastapi import Query
from typing import Dict, Type, List, Annotated
from typing import TypedDict, NotRequired
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import Response, JSONResponse
from fastapi import Cookie
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.repositories import BaseRepository, UserRepository
from src.database.models import User, UserRole, AuthSession, AbstractBase
from src.core import dtos
from src.core.services import AuthService
from src.core.dependencies import auth_dep, db_session_dep
import math
import json
import logging

logger = logging.getLogger(__name__)


async def authorize(
    token: Annotated[str | None, Cookie(alias="auth_token")] = None,
    auth_service: AuthService = Depends(auth_dep),
) -> AuthSession:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization cookie is missing."
        )

    try:
        identity: AuthSession = await auth_service.get_session(token=token)
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
    except Exception as e:
        logger.error(f"Authorization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authorization error."
        )

    if identity.user.role != UserRole.SUPERUSER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this route."
        )
    return identity


async def db_repository(
    model_name: str,
    session: AsyncSession = Depends(db_session_dep)
) -> BaseRepository:
    if model_name not in MODELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found."
        )
    
    model: Type[AbstractBase] = MODELS[model_name]["model"]
    special_repo = MODELS[model_name].get("repository")
    
    if special_repo:
        db_repo = special_repo(session)
    else:
        db_repo = BaseRepository(session, model)
    
    return db_repo


admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin v1"],
    dependencies=[Depends(authorize)],
)


class ModelsConfig(TypedDict):
    dto: Type[BaseModel]
    model: Type[AbstractBase]
    repository: NotRequired[Type[BaseRepository]]
    protected_fields: NotRequired[List[str]]


MODELS: Dict[str, ModelsConfig] = {
    "user": {
        "dto": dtos.UserCreateDto,
        "model": User,
        "repository": UserRepository,
        "protected_fields": ["password_hash", "is_superuser"],
    },
}


async def get_dto_instance(
    request: Request,
    model_name: str
) -> BaseModel:
    model_config = MODELS.get(model_name)
    if not model_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    dto_class = model_config["dto"]
    data = await request.json()
    return dto_class(**data)


@admin_router.get("/", response_model=Dict[str, List[str]])
async def get_models_name():
    return JSONResponse({"models": list(MODELS.keys())})


class SortOrder(str, Enum):
    ascending = "asc"
    descending = "desc"


@admin_router.get("/{model_name}", response_model=dtos.PaginationDto)
async def get_all(
    model_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    sort_by: str | None = None,
    direction: SortOrder | None = None,
    search: str | None = None,
    search_fields: List[str] | None = Query(None),
    exact_filter: str | None = Query(
        None, description="JSON: {'field_name': 'value'}"
    ),
    db_repository: BaseRepository = Depends(db_repository)
):
    model_config = MODELS.get(model_name)
    if not model_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The model is not found."
        )

    filters_dict: Dict | None = None
    if exact_filter:
        try:
            raw_filters = json.loads(exact_filter)
            dto_class = model_config.get("dto")
            allowed_fields = dto_class.model_fields.keys()
            protected_fields = set(model_config.get("protected_fields", []))
            
            filters_dict = {
                k: v for k, v in raw_filters.items()
                if k in allowed_fields 
                and k not in protected_fields
                and v is not None
            }
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The filter JSON is malformed."
            )

    objects, total_count = await db_repository.get_paginated(
        page=page,
        page_size=page_size,
        sortby=sort_by,
        direction=direction,
        search=search,
        search_fields=search_fields,
        exact_filter=filters_dict
    )

    dto: Type[BaseModel] = MODELS[model_name]["dto"]
    data_items = [dto.model_validate(model) for model in objects]
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
    
    return {
        "items": data_items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@admin_router.post("/{model_name}", status_code=status.HTTP_201_CREATED)
async def create_new(
    model_name: str,
    request: Request,
    db_repository: BaseRepository = Depends(db_repository)
):
    dto_instance = await get_dto_instance(request, model_name)
    
    try:
        new_record = await db_repository.create(
            dto_instance.model_dump()
        )
        return MODELS[model_name]["dto"].model_validate(new_record)
    except IntegrityError as e:
        logger.error(f"Integrity error during create: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists or constraint violated."
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during create: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred."
        )


@admin_router.get("/{model_name}/{id}")
async def get_model(
    model_name: str,
    id: int,
    db_repository: BaseRepository = Depends(db_repository)
):
    db_object = await db_repository.get_by_id(id)
    if not db_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )

    dto = MODELS[model_name]["dto"]
    return dto.model_validate(db_object)


@admin_router.patch("/{model_name}/{id}")
async def update_model(
    model_name: str,
    id: int,
    request: Request,
    db_repository: BaseRepository = Depends(db_repository)
):
    dto = await get_dto_instance(request, model_name)
    
    try:
        result = await db_repository.update(
            id,
            dto.model_dump(exclude_unset=True)
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found"
            )
        return MODELS[model_name]["dto"].model_validate(result)

    except IntegrityError as e:
        logger.error(f"Integrity error during update: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Record already exists or constraint violated."
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred."
        )


@admin_router.delete("/{model_name}/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_name: str,
    id: int,
    db_repository: BaseRepository = Depends(db_repository)
):
    try:
        deleted = await db_repository.delete(id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found"
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except SQLAlchemyError as e:
        logger.error(f"Database error during delete: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred."
        )