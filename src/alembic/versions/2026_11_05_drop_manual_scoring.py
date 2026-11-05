"""Удаление ручных действий Фонда: ввод результата скоринга и отправка в банк

Revision ID: a4c6e8f0b2d4
Revises: f3b5d7e9a1c3
Create Date: 2026-11-05

- право scoring.approve удаляется; выдачи ролям и пользователям уходят каскадно;
- заявки, ожидавшие ручной отправки в банк (COUNCIL_APPROVED), уходят в банк,
  выбранный заявителем (SENT_TO_BANK), с записью в истории.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4c6e8f0b2d4"
down_revision: Union[str, Sequence[str], None] = "f3b5d7e9a1c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'scoring.approve'"))

    op.execute(
        sa.text(
            """
            INSERT INTO application_status_history
                (application_id, from_status, to_status, event, comment)
            SELECT a.id, a.status, 'SENT_TO_BANK', 'sent_to_bank',
                   'Заявка направлена в банк: ' || b.name
            FROM applications a JOIN banks b ON b.id = a.bank_id
            WHERE a.status = 'COUNCIL_APPROVED'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE applications SET status = 'SENT_TO_BANK', sent_to_bank_at = now()
            WHERE status = 'COUNCIL_APPROVED' AND bank_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError("Irreversible: removed manual Fund actions cannot be restored")
