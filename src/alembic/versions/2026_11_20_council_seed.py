"""Начальный список членов Совета для сайта

Revision ID: d6f8b0c2e4a7
Revises: c5e7a9b1d3f6
Create Date: 2026-11-20

Добавляет 20 членов Совета (site_people, kind = COUNCIL) в заданном порядке.
ФИО одинаковое на всех языках, а описание переведено на ru и en. Фото не
добавляются: их загружает маркетинг. Повторно никого не создаёт: человек
пропускается, если член Совета с таким ФИО (uz) уже есть. Новые карточки
встают в конец списка, после уже существующих.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6f8b0c2e4a7"
down_revision: Union[str, Sequence[str], None] = "c5e7a9b1d3f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (ФИО, описание uz, описание ru, описание en)
MEMBERS = [
    (
        "Abdullayev Farrux Xabibulla o‘g‘li",
        "“Bellissimo Pizza International” MChJ ta’sischisi",
        "Учредитель ООО «Bellissimo Pizza International»",
        "Founder of Bellissimo Pizza International LLC",
    ),
    (
        "Abduvosipov Muslimbek Ulug‘bek o‘g‘li",
        "“Oliy Standart Tex” kompaniyasi ta’sischisi",
        "Учредитель компании «Oliy Standart Tex»",
        "Founder of Oliy Standart Tex",
    ),
    (
        "Kamalova Charos G‘anisher qizi",
        "“Teplo Local” MChJ ta’sischisi",
        "Учредитель ООО «Teplo Local»",
        "Founder of Teplo Local LLC",
    ),
    (
        "Abdurazoqov Olloyor Alijon o‘g‘li",
        "“Mehrigiyo Organic Factory” MChJ ta’sischisi",
        "Учредитель ООО «Mehrigiyo Organic Factory»",
        "Founder of Mehrigiyo Organic Factory LLC",
    ),
    (
        "Baxromov Fazliddin Faxriddin o‘g‘li",
        "“Novza Hotel” MChJ direktori",
        "Директор ООО «Novza Hotel»",
        "Director of Novza Hotel LLC",
    ),
    (
        "Rustamov Ollashukur Shuxratovich",
        "“Sofra” MChJ ta’sischisi, rahbari",
        "Учредитель и руководитель ООО «Sofra»",
        "Founder and head of Sofra LLC",
    ),
    (
        "Obidova Xilola Ilxomjon qizi",
        "“Guliston Kapital Standart” MChJ ta’sischisi",
        "Учредитель ООО «Guliston Kapital Standart»",
        "Founder of Guliston Kapital Standart LLC",
    ),
    (
        "Jalilov Behzod Murotovich",
        "“Target International School” NTM rahbari",
        "Руководитель НОУ «Target International School»",
        "Head of Target International School (non-state educational institution)",
    ),
    (
        "Usmanov Mirgulom Xoshim o‘g‘li",
        "“The Kasb xususiy bandlik agentligi” MChJ direktori",
        "Директор ООО «The Kasb xususiy bandlik agentligi» (частное агентство занятости)",
        "Director of The Kasb Private Employment Agency LLC",
    ),
    (
        "Sodiqov Sardor Sodikovich",
        "“Global Education In Karshi” NTM rahbari",
        "Руководитель НОУ «Global Education In Karshi»",
        "Head of Global Education In Karshi (non-state educational institution)",
    ),
    (
        "Karimov Yusufbek Ulug‘bekovich",
        "“Xujayli JBI YUUK” MChJ ta’sischisi",
        "Учредитель ООО «Xujayli JBI YUUK»",
        "Founder of Xujayli JBI YUUK LLC",
    ),
    (
        "Quldoshov Mirzobek Beruniy o‘g‘li",
        "O‘zbekiston Respublikasi Yoshlar ishlari agentligi Yoshlar bandligi va "
        "tadbirkorligiga ko‘maklashish bo‘limi boshlig‘i",
        "Начальник отдела содействия занятости и предпринимательству молодёжи "
        "Агентства по делам молодёжи Республики Узбекистан",
        "Head of the Youth Employment and Entrepreneurship Support Department, "
        "Youth Affairs Agency of the Republic of Uzbekistan",
    ),
    (
        "Baxbergenov Bolatbek Urinbasarovich",
        "“Arz Universal Servis” MChJ ta’sischisi",
        "Учредитель ООО «Arz Universal Servis»",
        "Founder of Arz Universal Servis LLC",
    ),
    (
        "Raxmadjonov A’zamjon Baxtiyorjon o‘g‘li",
        "“Diamond7Group” MChJ ta’sischisi, rahbari",
        "Учредитель и руководитель ООО «Diamond7Group»",
        "Founder and head of Diamond7Group LLC",
    ),
    (
        "Tojimirzayeva Gulbahor Baxodir qizi",
        "“BA ASSOCIATION” assotsiatsiyasi rahbari",
        "Руководитель ассоциации «BA ASSOCIATION»",
        "Head of BA ASSOCIATION",
    ),
    (
        "Abdalniyozov Faxriddin G‘ulomjanovich",
        "“Caravan Leader” oilaviy korxona ta’sischisi",
        "Учредитель семейного предприятия «Caravan Leader»",
        "Founder of Caravan Leader family enterprise",
    ),
    (
        "Kurbanova Diana Kazbekovna",
        "“Franchayzing” uyushmasi rahbari",
        "Руководитель ассоциации «Франчайзинг»",
        "Head of the Franchising Association",
    ),
    (
        "Iminoxunov Nuruddin Abduqahhorovich",
        "“Global Move” MChJ ta’sischisi, direktori",
        "Учредитель и директор ООО «Global Move»",
        "Founder and director of Global Move LLC",
    ),
    (
        "Yakubov Abdulaziz Obidjon o‘g‘li",
        "“Yoshlar ventures” jamg‘armasi direktori",
        "Директор фонда «Yoshlar ventures»",
        "Director of the Yoshlar Ventures fund",
    ),
    (
        "Abdujalolov Muhammad Abdunabi o‘g‘li",
        "“YESS COFFEE” brendi asoschisi",
        "Основатель бренда «YESS COFFEE»",
        "Founder of the YESS COFFEE brand",
    ),
]


def _existing_id(conn, full_name: str):
    return conn.execute(
        sa.text(
            "SELECT p.id FROM site_people p "
            "JOIN site_person_translations t ON t.person_id = p.id "
            "WHERE p.kind = 'COUNCIL' AND t.language = 'uz' AND t.full_name = :name LIMIT 1"
        ),
        {"name": full_name},
    ).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    queue = conn.execute(
        sa.text("SELECT COALESCE(MAX(queue_number), 0) FROM site_people WHERE kind = 'COUNCIL'")
    ).scalar_one()
    for full_name, uz, ru, en in MEMBERS:
        if _existing_id(conn, full_name) is not None:
            continue
        queue += 1
        person_id = conn.execute(
            sa.text(
                "INSERT INTO site_people (kind, queue_number, is_active, created_at, updated_at) "
                "VALUES ('COUNCIL', :queue, true, now(), now()) RETURNING id"
            ),
            {"queue": queue},
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
    for full_name, *_ in MEMBERS:
        person_id = _existing_id(conn, full_name)
        if person_id is not None:
            conn.execute(sa.text("DELETE FROM site_people WHERE id = :id"), {"id": person_id})
    # Номера без пропусков у оставшихся.
    conn.execute(
        sa.text(
            "UPDATE site_people p SET queue_number = r.n FROM ("
            "SELECT id, ROW_NUMBER() OVER (ORDER BY queue_number, id) AS n "
            "FROM site_people WHERE kind = 'COUNCIL') r WHERE p.id = r.id"
        )
    )
