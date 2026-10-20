from src.application.mappers import DemandDocumentDataMapper
from src.application.models.demand_document_model import DemandDocumentORM
from src.utils.base_rep.base_rep import BaseRepository


class DemandDocumentRepository(BaseRepository):
    model = DemandDocumentORM
    mapper = DemandDocumentDataMapper
