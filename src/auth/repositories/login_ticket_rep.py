from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, update

from src.auth.models.login_ticket_model import LoginTicketORM


class LoginTicketRepository:
    model = LoginTicketORM

    def __init__(self, session):
        self.session = session

    async def add(self, ticket_hash: str, user_id: int, expires_at: datetime) -> None:
        await self.session.execute(
            insert(self.model).values(
                ticket_hash=ticket_hash, user_id=user_id, expires_at=expires_at
            )
        )

    async def consume(self, ticket_hash: str) -> int | None:
        """Атомарно гасит билет и возвращает user_id; None — билета нет,
        он просрочен или уже использован (повторный обмен невозможен)."""
        now = datetime.now(UTC)
        stmt = (
            update(self.model)
            .where(
                self.model.ticket_hash == ticket_hash,
                self.model.used_at.is_(None),
                self.model.expires_at > now,
            )
            .values(used_at=now)
            .returning(self.model.user_id)
        )
        return await self.session.scalar(stmt)

    async def purge_stale(self, older_than: timedelta = timedelta(days=1)) -> None:
        await self.session.execute(
            delete(self.model).where(self.model.expires_at < datetime.now(UTC) - older_than)
        )
