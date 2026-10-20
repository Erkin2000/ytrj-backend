from src.application.mappers import ResourceAllocationDataMapper
from src.application.models.resource_allocation_model import ResourceAllocationORM
from src.utils.base_rep.base_rep import BaseRepository


class ResourceAllocationRepository(BaseRepository):
    model = ResourceAllocationORM
    mapper = ResourceAllocationDataMapper
