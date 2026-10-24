"""Единая точка импорта всех ORM-моделей: нужна там, где используется
только часть моделей (CLI, Alembic, скрипты), чтобы relationship() по
строковым именам находили классы в реестре SQLAlchemy."""

from src.account.models.user_model import UserORM
from src.application.models.application_model import ApplicationORM
from src.application.models.bank_model import BankORM
from src.application.models.council_assignment_model import CouncilAssignmentORM
from src.application.models.demand_document_model import DemandDocumentORM
from src.application.models.document_model import ApplicationDocumentORM
from src.application.models.founder_model import ApplicationFounderORM
from src.application.models.photo_model import ApplicationPhotoORM
from src.application.models.resource_allocation_model import ResourceAllocationORM
from src.application.models.scoring_model import ScoringAttemptORM
from src.application.models.status_history_model import StatusHistoryORM
from src.auth.models.refresh_token_model import RefreshTokenORM
from src.rbac.models.permission_model import PermissionORM
from src.rbac.models.role_model import RoleORM
from src.rbac.models.role_permission_model import RolePermissionORM

__all__ = [
    "UserORM",
    "ApplicationORM",
    "BankORM",
    "CouncilAssignmentORM",
    "DemandDocumentORM",
    "ApplicationDocumentORM",
    "ApplicationFounderORM",
    "ApplicationPhotoORM",
    "ResourceAllocationORM",
    "ScoringAttemptORM",
    "StatusHistoryORM",
    "RefreshTokenORM",
    "PermissionORM",
    "RoleORM",
    "RolePermissionORM",
]
