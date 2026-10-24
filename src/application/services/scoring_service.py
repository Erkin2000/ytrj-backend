"""Скоринг KATM и проверка требований Фонда (eligibility).

Реальный адаптер KATM появится в модуле интеграций и будет выполняться
фоновой задачей (outbox → Celery). Сейчас результат определяется режимом
SCORING_MODE или вносится вручную сотрудником Фонда / Super Admin.
"""

import logging
from typing import Any

from src.account.schemas.user_schema import CurrentUserDTO
from src.application.enums import ApplicationStatus, ScoringResult
from src.application.models.application_model import ApplicationORM
from src.application.schemas.application_schema import (
    ScoringAttemptAddDTO,
    ScoringAttemptDTO,
    ScoringResultRecordDTO,
)
from src.application.services.base import ApplicationBaseService, now
from src.common.responses.exceptions import ScoringNotPendingException
from src.config import settings

logger = logging.getLogger(__name__)


class KATMAdapter:
    """Заглушка интеграции KATM. Возвращает (result, details, error_message)."""

    async def score(
        self, application: ApplicationORM
    ) -> tuple[ScoringResult, dict[str, Any] | None, str | None]:
        mode = settings.SCORING_MODE

        if mode == "auto_pass":
            return ScoringResult.PASSED, {"mode": "auto_pass", "score": 100}, None
        if mode == "auto_fail":
            return (
                ScoringResult.FAILED,
                {
                    "mode": "auto_fail",
                    "check": "credit_history",
                    "reason": "Имитация: отрицательная кредитная история",
                },
                None,
            )
        if mode == "technical_error":
            return ScoringResult.TECHNICAL_ERROR, None, "KATM service unavailable (simulated)"

        raise RuntimeError("manual scoring mode: adapter must not be called")


class EligibilityChecker:
    """Дополнительные требования Фонда помимо KATM. Критерии уточняются
    заказчиком (ТЗ, п. 18.3) — пока все заявки проходят."""

    def check(self, application: ApplicationORM) -> tuple[bool, dict[str, Any]]:
        return True, {"checks": [], "note": "Fund eligibility criteria are not configured yet"}


class ScoringService(ApplicationBaseService):
    adapter = KATMAdapter()
    eligibility = EligibilityChecker()

    async def get_attempts(self, application_id: int) -> list[ScoringAttemptDTO]:
        return await self.db.scoring.get_for_application(application_id)

    async def start(self, application: ApplicationORM, actor: CurrentUserDTO | None) -> None:
        """SUBMITTED → SCORING_IN_PROGRESS и, если режим не manual, запуск проверки."""
        await self.transition(
            application,
            ApplicationStatus.SCORING_IN_PROGRESS,
            event="scoring_started",
            actor=actor,
            comment="Заявка направлена на скоринг KATM",
        )

        if settings.SCORING_MODE == "manual":
            return

        await self._run_adapter(application, actor=None)

    async def retry(self, application: ApplicationORM, actor: CurrentUserDTO) -> None:
        """Повторная обработка после технической ошибки."""
        if application.status != ApplicationStatus.SCORING_IN_PROGRESS:
            raise ScoringNotPendingException()

        await self.add_history(
            application,
            to_status=application.status,
            event="scoring_retry",
            actor=actor,
            comment="Повторный запуск скоринга",
            from_status=application.status,
        )

        if settings.SCORING_MODE == "manual":
            application.scoring_retry_required = False
            application.scoring_error_message = None
            await self.db.flush()
            return

        await self._run_adapter(application, actor=actor)

    async def record_manual_result(
        self,
        application: ApplicationORM,
        data: ScoringResultRecordDTO,
        actor: CurrentUserDTO,
    ) -> None:
        if application.status != ApplicationStatus.SCORING_IN_PROGRESS:
            raise ScoringNotPendingException()

        eligibility_passed = data.eligibility_passed
        details = data.details

        if data.result == ScoringResult.PASSED and eligibility_passed is None:
            eligibility_passed, eligibility_details = self.eligibility.check(application)
            details = {**(details or {}), "eligibility": eligibility_details}

        await self._apply_result(
            application,
            result=data.result,
            eligibility_passed=eligibility_passed,
            details=details,
            error_message=data.error_message,
            actor=actor,
        )

    # ---------- внутреннее ----------

    async def _run_adapter(self, application: ApplicationORM, actor: CurrentUserDTO | None) -> None:
        result, details, error = await self.adapter.score(application)

        eligibility_passed = None
        if result == ScoringResult.PASSED:
            eligibility_passed, eligibility_details = self.eligibility.check(application)
            details = {**(details or {}), "eligibility": eligibility_details}

        await self._apply_result(
            application,
            result=result,
            eligibility_passed=eligibility_passed,
            details=details,
            error_message=error,
            actor=actor,
        )

    async def _apply_result(
        self,
        application: ApplicationORM,
        *,
        result: ScoringResult,
        eligibility_passed: bool | None,
        details: dict[str, Any] | None,
        error_message: str | None,
        actor: CurrentUserDTO | None,
    ) -> None:
        await self.db.scoring.add(
            ScoringAttemptAddDTO(
                application_id=application.id,
                result=result,
                eligibility_passed=eligibility_passed,
                details=details,
                error_message=error_message,
                recorded_by_id=actor.id if actor else None,
            )
        )

        if result == ScoringResult.TECHNICAL_ERROR:
            # Техническая ошибка ≠ бизнес-отказ: заявка остаётся в ожидании повтора.
            application.scoring_retry_required = True
            application.scoring_error_message = error_message
            await self.db.flush()
            await self.add_history(
                application,
                to_status=application.status,
                event="scoring_technical_error",
                actor=actor,
                comment=error_message or "Техническая ошибка KATM, требуется повторная обработка",
                from_status=application.status,
            )
            logger.warning(
                "KATM technical error for application %s: %s", application.number, error_message
            )
            return

        application.scoring_retry_required = False
        application.scoring_error_message = None

        if result == ScoringResult.FAILED:
            await self.transition(
                application,
                ApplicationStatus.SCORING_FAILED,
                event="scoring_failed",
                actor=actor,
                comment="Скоринг KATM не пройден",
            )
            return

        if not eligibility_passed:
            await self.transition(
                application,
                ApplicationStatus.ELIGIBILITY_FAILED,
                event="eligibility_failed",
                actor=actor,
                comment="Не соответствует требованиям Фонда",
            )
            return

        await self.transition(
            application,
            ApplicationStatus.READY_FOR_BANK,
            event="scoring_passed",
            actor=actor,
            comment="Скоринг KATM и требования Фонда пройдены",
        )

        # Заявка автоматически уходит в банк, выбранный заявителем. Если банк
        # к этому моменту деактивирован или не подходит по типу субъекта, заявка
        # остаётся в READY_FOR_BANK, и банк назначает Фонд (send-to-bank).
        bank = application.bank
        if (
            bank is not None
            and bank.is_active
            and application.subject_type in bank.allowed_subject_types
        ):
            application.sent_to_bank_at = now()
            await self.transition(
                application,
                ApplicationStatus.SENT_TO_BANK,
                event="sent_to_bank",
                actor=None,
                comment=f"Заявка направлена в банк: {bank.name}",
            )
