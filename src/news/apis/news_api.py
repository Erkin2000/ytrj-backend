"""Новости сайта: публичная лента и ведение новостей отделом маркетинга."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from src.common.dependencies import CurrentUserDep, DBDep, PaginationDep, require_permission
from src.common.responses.exceptions import (
    InvalidPhotoException,
    NewsNotFoundException,
    NewsPhotoNotFoundException,
    NewsScheduleException,
    PhotoTooLargeException,
)
from src.common.responses.response import ResponseBuilder
from src.common.swagger.responses import (
    COMMON_ERRORS,
    PUBLIC_ERRORS,
    error_examples,
    paginated_example,
    success_example,
)
from src.news.schemas.news_schema import (
    NEWS_TRANSLATIONS_EXAMPLE,
    NewsCreateForm,
    NewsFilterDTO,
    NewsUpdateDTO,
)
from src.news.services.news_service import NewsService
from src.rbac.permissions import Action, Module

PHOTO = {"name": "opening.jpg", "content_type": "image/jpeg", "size": 184320}
PUBLIC_EXAMPLE = {
    "id": 7,
    "translations": NEWS_TRANSLATIONS_EXAMPLE,
    "date": "2026-11-20",
    "published_at": "2026-11-20T05:00:00Z",
    "photo": {"url": "/api/v1/news/7/photo", **PHOTO},
}
NEWS_EXAMPLE = {
    "id": 7,
    "translations": NEWS_TRANSLATIONS_EXAMPLE,
    "date": "2026-11-20",
    "state": "SCHEDULED",
    "publish_at": "2026-11-25T05:00:00Z",
    "photo": {"url": "/api/v1/marketing/news/7/photo", **PHOTO},
    "created_by": {"id": 12, "full_name": "Marketing Operator", "username": "marketing1"},
    "updated_by": {"id": 12, "full_name": "Marketing Operator", "username": "marketing1"},
    "created_at": "2026-11-20T09:00:00Z",
    "updated_at": "2026-11-20T09:00:00Z",
}
NOT_FOUND = {404: error_examples(NewsNotFoundException)}
PHOTO_ERRORS = {400: error_examples(InvalidPhotoException, PhotoTooLargeException)}

public_router = APIRouter(prefix="/news", tags=["Новости: сайт"])
router = APIRouter(prefix="/marketing/news", tags=["Новости: управление (маркетинг)"])

FilterDep = Annotated[NewsFilterDTO, Depends()]


# ---------- сайт ----------


@public_router.get(
    "",
    summary="Лента новостей сайта (опубликованные), новые сверху",
    description=(
        "Без авторизации. Отложенные новости появляются в ленте сами, когда наступает "
        "время публикации. Фото — по `photo.url`."
    ),
    responses={200: paginated_example(PUBLIC_EXAMPLE, "News retrieved."), **PUBLIC_ERRORS},
)
async def get_public_news(db: DBDep, pagination: PaginationDep):
    data = await NewsService(db).get_public_page(pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="News retrieved.")


@public_router.get(
    "/{news_id}",
    summary="Новость для сайта",
    description="Без авторизации. Черновик и ещё не опубликованная новость — 404.",
    responses={
        200: success_example(PUBLIC_EXAMPLE, "News found."),
        **PUBLIC_ERRORS,
        **NOT_FOUND,
    },
)
async def get_public_news_item(news_id: int, db: DBDep):
    data = await NewsService(db).get_public_detail(news_id)
    return ResponseBuilder.success(data=data, message="News found.")


@public_router.get(
    "/{news_id}/photo",
    summary="Фото опубликованной новости",
    description="Без авторизации.",
    response_class=FileResponse,
    responses={404: error_examples(NewsNotFoundException, NewsPhotoNotFoundException)},
)
async def get_public_news_photo(news_id: int, db: DBDep):
    path, content_type, name = await NewsService(db).public_photo(news_id)
    return FileResponse(
        path,
        media_type=content_type,
        filename=name,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------- маркетинг ----------

read_dep = Depends(require_permission(Module.NEWS, Action.READ))
create_dep = Depends(require_permission(Module.NEWS, Action.CREATE))
update_dep = Depends(require_permission(Module.NEWS, Action.UPDATE))
delete_dep = Depends(require_permission(Module.NEWS, Action.DELETE))


@router.get(
    "",
    summary="Все новости: черновики, отложенные и опубликованные",
    dependencies=[read_dep],
    responses={200: paginated_example(NEWS_EXAMPLE, "News retrieved."), **COMMON_ERRORS},
)
async def get_news_list(db: DBDep, pagination: PaginationDep, filters: FilterDep):
    data = await NewsService(db).get_page(filters, pagination.page, pagination.per_page)
    return ResponseBuilder.success(data=data, message="News retrieved.")


@router.post(
    "",
    status_code=201,
    summary="Создать новость (multipart/form-data): сразу, в выбранное время или черновик",
    description=(
        "Заголовок и текст — на трёх языках: `title_ru`, `title_uz`, `title_en`, `text_ru`, "
        "`text_uz`, `text_en`. `status=PUBLISHED` — новость сразу на сайте; "
        "`status=SCHEDULED` + `publish_at` — появится на сайте в это время; `status=DRAFT` — "
        "черновик. Фото `photo` (JPEG / PNG / WEBP) необязательно."
    ),
    dependencies=[create_dep],
    responses={
        201: success_example(NEWS_EXAMPLE, "News created."),
        **COMMON_ERRORS,
        400: error_examples(NewsScheduleException, InvalidPhotoException, PhotoTooLargeException),
    },
)
async def create_news(
    db: DBDep,
    user: CurrentUserDep,
    form: Annotated[NewsCreateForm, Form(media_type="multipart/form-data")],
):
    data = await NewsService(db).create(user, form)
    return ResponseBuilder.success(data=data, message="News created.", status_code=201)


@router.get(
    "/{news_id}",
    summary="Новость по ID",
    dependencies=[read_dep],
    responses={200: success_example(NEWS_EXAMPLE, "News found."), **COMMON_ERRORS, **NOT_FOUND},
)
async def get_news(news_id: int, db: DBDep):
    data = await NewsService(db).get_detail(news_id)
    return ResponseBuilder.success(data=data, message="News found.")


@router.patch(
    "/{news_id}",
    summary="Изменить переводы, дату, публикацию новости",
    description=(
        "`status=PUBLISHED` — опубликовать сейчас (у уже опубликованной дата публикации "
        "не меняется); `SCHEDULED` + `publish_at` — перенести публикацию; `DRAFT` — снять "
        "с сайта. Фото — `PUT` / `DELETE /{news_id}/photo`."
    ),
    dependencies=[update_dep],
    responses={
        200: success_example(NEWS_EXAMPLE, "News updated."),
        **COMMON_ERRORS,
        **NOT_FOUND,
        400: error_examples(NewsScheduleException),
    },
)
async def update_news(news_id: int, data: NewsUpdateDTO, db: DBDep, user: CurrentUserDep):
    news = await NewsService(db).update(user, news_id, data)
    return ResponseBuilder.success(data=news, message="News updated.")


@router.delete(
    "/{news_id}",
    summary="Удалить новость вместе с фото",
    description="Чтобы только убрать новость с сайта, переведите её в `DRAFT`.",
    dependencies=[delete_dep],
    responses={200: success_example(None, "News deleted."), **COMMON_ERRORS, **NOT_FOUND},
)
async def delete_news(news_id: int, db: DBDep):
    await NewsService(db).delete(news_id)
    return ResponseBuilder.success(message="News deleted.")


@router.get(
    "/{news_id}/photo",
    summary="Фото новости (любой, в том числе черновика)",
    dependencies=[read_dep],
    response_class=FileResponse,
    responses={
        **COMMON_ERRORS,
        404: error_examples(NewsNotFoundException, NewsPhotoNotFoundException),
    },
)
async def get_news_photo(news_id: int, db: DBDep):
    path, content_type, name = await NewsService(db).photo(news_id)
    return FileResponse(
        path, media_type=content_type, filename=name, content_disposition_type="inline"
    )


@router.put(
    "/{news_id}/photo",
    summary="Загрузить или заменить фото новости",
    dependencies=[update_dep],
    responses={
        200: success_example(NEWS_EXAMPLE, "Photo uploaded."),
        **COMMON_ERRORS,
        **NOT_FOUND,
        **PHOTO_ERRORS,
    },
)
async def set_news_photo(
    news_id: int,
    db: DBDep,
    user: CurrentUserDep,
    photo: Annotated[UploadFile, File(description="JPEG / PNG / WEBP.")],
):
    data = await NewsService(db).set_photo(user, news_id, photo)
    return ResponseBuilder.success(data=data, message="Photo uploaded.")


@router.delete(
    "/{news_id}/photo",
    summary="Удалить фото новости",
    dependencies=[update_dep],
    responses={
        200: success_example({**NEWS_EXAMPLE, "photo": None}, "Photo deleted."),
        **COMMON_ERRORS,
        404: error_examples(NewsNotFoundException, NewsPhotoNotFoundException),
    },
)
async def delete_news_photo(news_id: int, db: DBDep, user: CurrentUserDep):
    data = await NewsService(db).delete_photo(user, news_id)
    return ResponseBuilder.success(data=data, message="Photo deleted.")
