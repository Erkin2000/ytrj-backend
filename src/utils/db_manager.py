from src.account.repositories.user_rep import UserRepository
from src.application.repositories.application_rep import ApplicationRepository
from src.application.repositories.bank_rep import BankRepository
from src.application.repositories.council_assignment_rep import CouncilAssignmentRepository
from src.application.repositories.demand_document_rep import DemandDocumentRepository
from src.application.repositories.document_rep import ApplicationDocumentRepository
from src.application.repositories.founder_rep import ApplicationFounderRepository
from src.application.repositories.photo_rep import ApplicationPhotoRepository
from src.application.repositories.resource_allocation_rep import ResourceAllocationRepository
from src.application.repositories.scoring_rep import ScoringAttemptRepository
from src.application.repositories.status_history_rep import StatusHistoryRepository
from src.auth.repositories.refresh_token_rep import RefreshTokenRepository
from src.rbac.repositories.permission_rep import PermissionRepository
from src.rbac.repositories.role_rep import RoleRepository


class DBManager:
    """Unit of work: одна сессия на запрос, репозитории поверх неё."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()

        self.user = UserRepository(self.session)
        self.role = RoleRepository(self.session)
        self.permission = PermissionRepository(self.session)
        self.refresh_token = RefreshTokenRepository(self.session)

        self.bank = BankRepository(self.session)
        self.application = ApplicationRepository(self.session)
        self.application_photo = ApplicationPhotoRepository(self.session)
        self.application_document = ApplicationDocumentRepository(self.session)
        self.application_founder = ApplicationFounderRepository(self.session)
        self.status_history = StatusHistoryRepository(self.session)
        self.scoring = ScoringAttemptRepository(self.session)
        self.council_assignment = CouncilAssignmentRepository(self.session)
        self.demand_document = DemandDocumentRepository(self.session)
        self.resource_allocation = ResourceAllocationRepository(self.session)

        return self

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def flush(self):
        await self.session.flush()
