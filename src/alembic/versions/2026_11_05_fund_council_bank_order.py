"""workflow: scoring -> Fund -> Council -> Bank (bank is the last stage)

Revision ID: f3b5d7e9a1c3
Revises: e2a4c6e8f0b2
Create Date: 2026-11-05 12:00:00

* application_status: + FUND_REVIEW, FUND_REJECTED (old values stay for history).
* applications: fund_decided_by_id, fund_decided_at, fund_reject_reason.
* In-flight applications are moved to the new order; every move is written to
  application_status_history (event "workflow_migrated"):
      READY_FOR_BANK / SENT_TO_BANK / BANK_REVIEW / BANK_APPROVED -> FUND_REVIEW
      DEMAND_DOCUMENT_CREATED / RESOURCE_ALLOCATION               -> COMPLETED
      COUNCIL_REVIEW / COUNCIL_APPROVED                           -> unchanged
  Applications that will go through the bank again (moved to FUND_REVIEW, or
  still in COUNCIL_REVIEW / COUNCIL_APPROVED) get the old bank stage fields
  cleared — the previous bank decision remains in the history.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3b5d7e9a1c3"
down_revision: Union[str, Sequence[str], None] = "e2a4c6e8f0b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TO_FUND = ("READY_FOR_BANK", "SENT_TO_BANK", "BANK_REVIEW", "BANK_APPROVED")
TO_COMPLETED = ("DEMAND_DOCUMENT_CREATED", "RESOURCE_ALLOCATION")
BANK_AGAIN = ("COUNCIL_REVIEW", "COUNCIL_APPROVED")

CLEAR_BANK_STAGE = """
    sent_to_bank_at = NULL,
    bank_accepted_by_id = NULL,
    bank_accepted_at = NULL,
    bank_decision = NULL,
    bank_decision_reason = NULL,
    bank_decided_by_id = NULL,
    bank_decided_at = NULL
"""


def _history(statuses: tuple[str, ...], to_status: str | None, comment: str) -> None:
    """Запись в историю для каждой заявки в statuses (to_status=None — статус не меняется)."""
    target = "status" if to_status is None else f"CAST('{to_status}' AS application_status)"
    op.execute(
        sa.text(
            f"""
            INSERT INTO application_status_history
                (application_id, from_status, to_status, event, comment)
            SELECT id, status, {target}, 'workflow_migrated', :comment
            FROM applications
            WHERE status::text = ANY(:statuses)
            """
        ).bindparams(comment=comment, statuses=list(statuses))
    )


def upgrade() -> None:
    # Новые значения enum должны быть закоммичены до использования.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE application_status ADD VALUE IF NOT EXISTS 'FUND_REVIEW'")
        op.execute("ALTER TYPE application_status ADD VALUE IF NOT EXISTS 'FUND_REJECTED'")

    op.add_column("applications", sa.Column("fund_decided_by_id", sa.Integer(), nullable=True))
    op.add_column(
        "applications",
        sa.Column("fund_decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("applications", sa.Column("fund_reject_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_applications_fund_decided_by_id_users",
        "applications",
        "users",
        ["fund_decided_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- перенос заявок в новый порядок ---
    _history(
        TO_FUND,
        "FUND_REVIEW",
        "Новый порядок обработки (Фонд → Совет → банк): заявка передана на рассмотрение Фонда. "
        "Прежнее решение банка сохранено в истории; банк рассмотрит заявку после Совета.",
    )
    op.execute(
        sa.text(
            f"UPDATE applications SET status = 'FUND_REVIEW', {CLEAR_BANK_STAGE} "
            "WHERE status::text = ANY(:statuses)"
        ).bindparams(statuses=list(TO_FUND))
    )

    _history(
        TO_COMPLETED,
        "COMPLETED",
        "Новый порядок обработки: банк и Совет одобрили заявку — процесс завершён.",
    )
    op.execute(
        sa.text(
            "UPDATE applications SET status = 'COMPLETED', "
            "completed_at = COALESCE(completed_at, now()) "
            "WHERE status::text = ANY(:statuses)"
        ).bindparams(statuses=list(TO_COMPLETED))
    )

    # Заявки у Совета: банк теперь рассматривает их после Совета.
    op.execute(
        sa.text(
            """
            INSERT INTO application_status_history
                (application_id, from_status, to_status, event, comment)
            SELECT id, status, status, 'workflow_migrated', :comment
            FROM applications
            WHERE status::text = ANY(:statuses) AND bank_decision IS NOT NULL
            """
        ).bindparams(
            comment=(
                "Новый порядок обработки: после решения Совета заявка будет направлена в банк. "
                "Прежнее решение банка сохранено в истории."
            ),
            statuses=list(BANK_AGAIN),
        )
    )
    op.execute(
        sa.text(
            f"UPDATE applications SET {CLEAR_BANK_STAGE} "
            "WHERE status::text = ANY(:statuses) AND bank_decision IS NOT NULL"
        ).bindparams(statuses=list(BANK_AGAIN))
    )


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible: applications were moved to the Fund → Council → Bank order "
        "(see application_status_history, event 'workflow_migrated')."
    )
