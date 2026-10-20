from math import ceil
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Base
from src.utils.base_rep.mappers.base import DataMapper


class BaseRepository:
    model: type[Base]
    mapper: type[DataMapper]
    session: AsyncSession

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_filtered(self, *filter, **filter_by) -> list[BaseModel | Any]:
        query = select(self.model).filter(*filter).filter_by(**filter_by)
        result = await self.session.execute(query)
        return [self.mapper.map_to_domain_entity(model) for model in result.scalars().all()]

    async def get_all(self, *args, **kwargs) -> list[BaseModel | Any]:
        return await self.get_filtered()

    async def get_one_or_none(self, **filter_by) -> BaseModel | None | Any:
        query = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(query)
        model = result.scalars().one_or_none()
        if model is None:
            return None
        return self.mapper.map_to_domain_entity(model)

    async def get_orm_one_or_none(self, **filter_by) -> Base | None:
        query = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(query)
        return result.scalars().one_or_none()

    async def exists(self, *filter, **filter_by) -> bool:
        query = select(func.count()).select_from(self.model).filter(*filter).filter_by(**filter_by)
        return bool(await self.session.scalar(query))

    async def add(self, data: BaseModel) -> BaseModel | Any:
        stmt = insert(self.model).values(**data.model_dump()).returning(self.model)
        result = await self.session.execute(stmt)
        model = result.scalars().one()
        return self.mapper.map_to_domain_entity(model)

    async def edit(self, data: BaseModel, exclude_unset: bool = False, **filter_by) -> None:
        values = data.model_dump(exclude_unset=exclude_unset)
        if not values:
            return
        stmt = update(self.model).filter_by(**filter_by).values(**values)
        await self.session.execute(stmt)

    async def delete(self, **filter_by) -> None:
        stmt = delete(self.model).filter_by(**filter_by)
        await self.session.execute(stmt)

    async def paginate(
        self,
        stmt: Select,
        page: int | None,
        per_page: int | None,
        mapper=None,
    ) -> dict:
        """Общий формат постраничного ответа: items + pagination."""
        mapper = mapper or self.mapper.map_to_domain_entity

        total = (
            await self.session.scalar(
                select(func.count()).select_from(stmt.order_by(None).subquery())
            )
            or 0
        )

        if page and per_page:
            stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        result = await self.session.scalars(stmt)
        items = [mapper(model) for model in result.unique().all()]

        return {
            "items": items,
            "pagination": {
                "page": page or 1,
                "per_page": per_page or total,
                "total": total,
                "pages": ceil(total / per_page) if per_page else 1,
            },
        }
