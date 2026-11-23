"""Единая точка импорта всех ORM-моделей: нужна там, где используется
только часть моделей (CLI, Alembic, скрипты), чтобы relationship() по
строковым именам находили классы в реестре SQLAlchemy."""

from src.account.models.user_model import UserORM
from src.account.models.user_permission_model import UserPermissionORM
from src.application.models.answer_model import ApplicationFieldFileORM, ApplicationFieldValueORM
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
from src.bulletin.models.bulletin_model import BulletinORM, BulletinSignatureORM
from src.faq.models.faq_model import FaqORM, FaqTranslationORM
from src.news.models.news_model import NewsORM, NewsTranslationORM
from src.product.models.product_model import (
    ProductCategoryORM,
    ProductFieldOptionORM,
    ProductFieldOptionTranslationORM,
    ProductFieldORM,
    ProductORM,
    ProductStageORM,
)
from src.rbac.models.permission_model import PermissionORM, PermissionTranslationORM
from src.rbac.models.role_model import RoleORM, RoleTranslationORM
from src.rbac.models.role_permission_model import RolePermissionORM
from src.website.models.website_model import (
    AboutSectionORM,
    AboutTranslationORM,
    EventORM,
    EventTranslationORM,
    PersonORM,
    PersonTranslationORM,
    SiteContactORM,
    TestimonialORM,
    TestimonialTranslationORM,
)

__all__ = [
    "UserORM",
    "UserPermissionORM",
    "ApplicationORM",
    "ApplicationFieldFileORM",
    "ApplicationFieldValueORM",
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
    "BulletinORM",
    "BulletinSignatureORM",
    "FaqORM",
    "FaqTranslationORM",
    "NewsORM",
    "NewsTranslationORM",
    "EventORM",
    "EventTranslationORM",
    "AboutSectionORM",
    "AboutTranslationORM",
    "PersonORM",
    "PersonTranslationORM",
    "SiteContactORM",
    "TestimonialORM",
    "TestimonialTranslationORM",
    "ProductCategoryORM",
    "ProductORM",
    "ProductStageORM",
    "ProductFieldORM",
    "ProductFieldOptionORM",
    "ProductFieldOptionTranslationORM",
    "PermissionORM",
    "PermissionTranslationORM",
    "RoleORM",
    "RoleTranslationORM",
    "RolePermissionORM",
]
