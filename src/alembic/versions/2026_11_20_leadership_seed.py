"""Начальный список руководства для сайта

Revision ID: e7a9c1d3f5b8
Revises: d6f8b0c2e4a7
Create Date: 2026-11-20

Добавляет 10 сотрудников руководства (site_people, kind = LEADERSHIP) в заданном
порядке. ФИО одинаковое на всех языках, а должность переведена на ru и en. Фото
не добавляются: их загружает маркетинг. Повторно никого не создаёт: человек
пропускается, если в руководстве уже есть запись с таким ФИО (uz). Новые
карточки встают в конец списка, после уже существующих.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a9c1d3f5b8"
down_revision: Union[str, Sequence[str], None] = "d6f8b0c2e4a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KIND = "LEADERSHIP"

CHIEF_SPECIALIST = ("Bosh mutaxassis", "Главный специалист", "Chief Specialist")
HEAD_OF_DEPARTMENT = ("Bo‘lim boshlig‘i", "Начальник отдела", "Head of Department")
PROJECT_MANAGER = ("Loyiha rahbari", "Руководитель проекта", "Project Manager")

# (ФИО, (должность uz, ru, en))
MEMBERS = [
    ("Qurbonova Zilola Xo‘jamqul qizi", CHIEF_SPECIALIST),
    ("Omonov Shaxzod Baxtiyor o‘g‘li", HEAD_OF_DEPARTMENT),
    (
        "Eshnazarov Mehriddin Xayriddinovich",
        (
            "Bo‘lim boshlig‘i — bosh hisobchi",
            "Начальник отдела — главный бухгалтер",
            "Head of Department — Chief Accountant",
        ),
    ),
    ("Jurayev Yokubjon Farxod o‘g‘li", HEAD_OF_DEPARTMENT),
    ("Ikromova Shaxzoda Nazirjon qizi", CHIEF_SPECIALIST),
    ("Sadullayev Lazizjon Baxriddin o‘g‘li", CHIEF_SPECIALIST),
    ("Mardiyev Alisher Dilshod o‘g‘li", PROJECT_MANAGER),
    ("Sadikov Umid Saxibxanovich", CHIEF_SPECIALIST),
    (
        "Mamatqulov Shoxrux Kudratjon o‘g‘li",
        ("Bosh yuriskonsult", "Главный юрисконсульт", "Chief Legal Counsel"),
    ),
    ("Haydarova Dilbar Zafaraliyevna", PROJECT_MANAGER),
]


def _existing_id(conn, full_name: str):
    return conn.execute(
        sa.text(
            "SELECT p.id FROM site_people p "
            "JOIN site_person_translations t ON t.person_id = p.id "
            "WHERE p.kind = CAST(:kind AS site_person_kind) AND t.language = 'uz' AND t.full_name = :name LIMIT 1"
        ),
        {"kind": KIND, "name": full_name},
    ).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    queue = conn.execute(
        sa.text("SELECT COALESCE(MAX(queue_number), 0) FROM site_people WHERE kind = CAST(:kind AS site_person_kind)"),
        {"kind": KIND},
    ).scalar_one()
    for full_name, (uz, ru, en) in MEMBERS:
        if _existing_id(conn, full_name) is not None:
            continue
        queue += 1
        person_id = conn.execute(
            sa.text(
                "INSERT INTO site_people (kind, queue_number, is_active, created_at, updated_at) "
                "VALUES (CAST(:kind AS site_person_kind), :queue, true, now(), now()) RETURNING id"
            ),
            {"kind": KIND, "queue": queue},
        ).scalar_one()
        for lang, description in (("ru", ru), ("uz", uz), ("en", en)):
            conn.execute(
                sa.text(
                    "INSERT INTO site_person_translations "
                    "(person_id, language, full_name, description) "
                    "VALUES (:pid, CAST(:lang AS language), :name, :description)"
                ),
                {"pid": person_id, "lang": lang, "name": full_name, "description": description},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for full_name, _ in MEMBERS:
        person_id = _existing_id(conn, full_name)
        if person_id is not None:
            conn.execute(sa.text("DELETE FROM site_people WHERE id = :id"), {"id": person_id})
    # Номера без пропусков у оставшихся.
    conn.execute(
        sa.text(
            "UPDATE site_people p SET queue_number = r.n FROM ("
            "SELECT id, ROW_NUMBER() OVER (ORDER BY queue_number, id) AS n "
            "FROM site_people WHERE kind = CAST(:kind AS site_person_kind)) r WHERE p.id = r.id"
        ),
        {"kind": KIND},
    )
