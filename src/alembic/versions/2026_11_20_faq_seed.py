"""Начальные вопросы FAQ для сайта (из text.json)

Revision ID: c5e7a9b1d3f6
Revises: b4d6f8a0c2e5
Create Date: 2026-11-20

Добавляет 6 вопросов на ru / uz / en. Повторно не создаёт: вопрос
пропускается, если FAQ с таким же русским вопросом уже есть. Пункты списка
(«list» в text.json) добавлены в конец ответа строками «• …».
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5e7a9b1d3f6"
down_revision: Union[str, Sequence[str], None] = "b4d6f8a0c2e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FAQS = [{'sort_order': 1,
  'translations': {'uz': {'question': 'Jamg‘arma qanday turdagi moliyaviy yordamlarni taqdim '
                                      'etadi?',
                          'answer': 'Jamg‘arma yosh tadbirkorlarga imtiyozli kredit, '
                                    'subsidiya va BHM asosidagi qarz mablag‘lari orqali '
                                    'moliyaviy yordam ko‘rsatadi. Har bir yo‘nalish bo‘yicha '
                                    'kredit miqdori va foiz stavkasi alohida belgilanadi.'},
                   'ru': {'question': 'Какие виды финансовой помощи предоставляет Фонд?',
                          'answer': 'Фонд оказывает молодым предпринимателям финансовую '
                                    'поддержку в виде льготных кредитов, субсидий и заёмных '
                                    'средств в размере, кратном БРВ. Сумма кредита и '
                                    'процентная ставка устанавливаются отдельно по каждому '
                                    'направлению.'},
                   'en': {'question': 'What types of financial assistance does the Fund '
                                      'provide?',
                          'answer': 'The Fund supports young entrepreneurs through '
                                    'concessional loans, subsidies and borrowed funds based '
                                    'on the base calculation amount (BCA). The loan amount '
                                    'and interest rate are set separately for each area.'}}},
 {'sort_order': 2,
  'translations': {'uz': {'question': 'Qaysi banklar imtiyozli kreditlar taqdim etadi?',
                          'answer': 'Jamg‘arma quyidagi hamkor banklar orqali kreditlar '
                                    'taqdim etadi:\n'
                                    '• Milliy bank\n'
                                    '• Xalq banki\n'
                                    '• Aloqabank\n'
                                    '• Sanoatqurilishbank\n'
                                    '• Mikrokreditbank\n'
                                    '• Asakabank\n'
                                    '• Turonbank\n'
                                    '• Biznesni rivojlantirish banki\n'
                                    '• Agrobank'},
                   'ru': {'question': 'Какие банки выдают льготные кредиты?',
                          'answer': 'Фонд предоставляет кредиты через следующие '
                                    'банки-партнёры:\n'
                                    '• Национальный банк\n'
                                    '• Халк банк\n'
                                    '• Алокабанк\n'
                                    '• Узпромстройбанк\n'
                                    '• Микрокредитбанк\n'
                                    '• Асакабанк\n'
                                    '• Туронбанк\n'
                                    '• Банк развития бизнеса\n'
                                    '• Агробанк'},
                   'en': {'question': 'Which banks provide preferential loans?',
                          'answer': 'The Fund provides loans through the following partner '
                                    'banks:\n'
                                    '• National Bank\n'
                                    '• Xalq Bank\n'
                                    '• Aloqabank\n'
                                    '• Sanoatqurilishbank\n'
                                    '• Microcreditbank\n'
                                    '• Asakabank\n'
                                    '• Turonbank\n'
                                    '• Business Development Bank\n'
                                    '• Agrobank'}}},
 {'sort_order': 3,
  'translations': {'uz': {'question': 'Ushbu Jamg‘armadan kimlar foydalanishi mumkin?',
                          'answer': '18 yoshdan 35 yoshgacha bo‘lgan, tadbirkorlik faoliyati '
                                    'bilan shug‘ullanmoqchi yoki mavjud biznesini '
                                    'kengaytirmoqchi bo‘lgan O‘zbekiston Respublikasi '
                                    'fuqarolari ariza topshirishi mumkin.'},
                   'ru': {'question': 'Кто может воспользоваться услугами Фонда?',
                          'answer': 'Подать заявку могут граждане Республики Узбекистан в '
                                    'возрасте от 18 до 35 лет, которые хотят заняться '
                                    'предпринимательской деятельностью или расширить '
                                    'действующий бизнес.'},
                   'en': {'question': 'Who can use the Fund’s services?',
                          'answer': 'Citizens of the Republic of Uzbekistan aged 18 to 35 who '
                                    'want to start a business or expand an existing one can '
                                    'apply.'}}},
 {'sort_order': 4,
  'translations': {'uz': {'question': 'Ariza qanday tartibda ko‘rib chiqiladi?',
                          'answer': 'Ariza platformaga topshirilgandan so‘ng mas’ul xodimlar '
                                    'tomonidan dastlabki ko‘rib chiqiladi, so‘ng Maxsus '
                                    'Kengash muhokamasiga yuboriladi va yakuniy qaror qabul '
                                    'qilinadi.'},
                   'ru': {'question': 'В каком порядке рассматривается заявка?',
                          'answer': 'После подачи на платформу заявка проходит '
                                    'предварительное рассмотрение ответственными '
                                    'сотрудниками, затем направляется на обсуждение '
                                    'Специального совета, который принимает окончательное '
                                    'решение.'},
                   'en': {'question': 'How is an application reviewed?',
                          'answer': 'Once submitted on the platform, an application is first '
                                    'reviewed by responsible staff, then referred to the '
                                    'Special Council for discussion, where the final decision '
                                    'is made.'}}},
 {'sort_order': 5,
  'translations': {'uz': {'question': 'Ariza topshirish uchun qanday hujjatlar kerak?',
                          'answer': 'Pasport nusxasi, biznes-reja, faoliyat yo‘nalishini '
                                    'tasdiqlovchi hujjatlar va bank rekvizitlari talab '
                                    'qilinadi. To‘liq hujjatlar ro‘yxati ariza shaklida '
                                    'ko‘rsatiladi.'},
                   'ru': {'question': 'Какие документы нужны для подачи заявки?',
                          'answer': 'Требуются копия паспорта, бизнес-план, документы, '
                                    'подтверждающие направление деятельности, и банковские '
                                    'реквизиты. Полный перечень документов указан в форме '
                                    'заявки.'},
                   'en': {'question': 'What documents are required to apply?',
                          'answer': 'A copy of your passport, a business plan, documents '
                                    'confirming your line of business and your bank details '
                                    'are required. The full list of documents is shown in the '
                                    'application form.'}}},
 {'sort_order': 6,
  'translations': {'uz': {'question': 'Kredit necha oy muddatga beriladi?',
                          'answer': 'Kredit muddati tanlangan dastur turiga qarab farq qiladi '
                                    'va odatda 12 oydan 60 oygacha bo‘lgan davrni o‘z ichiga '
                                    'oladi.'},
                   'ru': {'question': 'На какой срок выдаётся кредит?',
                          'answer': 'Срок кредита зависит от выбранной программы и, как '
                                    'правило, составляет от 12 до 60 месяцев.'},
                   'en': {'question': 'For how many months is a loan issued?',
                          'answer': 'The loan term depends on the selected program and '
                                    'usually ranges from 12 to 60 months.'}}}]


def _existing_id(conn, question_ru: str):
    return conn.execute(
        sa.text(
            "SELECT faq_id FROM faq_translations WHERE language = 'ru' AND question = :q LIMIT 1"
        ),
        {"q": question_ru},
    ).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    for faq in FAQS:
        if _existing_id(conn, faq["translations"]["ru"]["question"]) is not None:
            continue
        faq_id = conn.execute(
            sa.text(
                "INSERT INTO faqs (is_active, sort_order, created_at, updated_at) "
                "VALUES (true, :sort, now(), now()) RETURNING id"
            ),
            {"sort": faq["sort_order"]},
        ).scalar_one()
        for lang, t in faq["translations"].items():
            conn.execute(
                sa.text(
                    "INSERT INTO faq_translations (faq_id, language, question, answer) "
                    "VALUES (:faq_id, CAST(:lang AS language), :q, :a)"
                ),
                {"faq_id": faq_id, "lang": lang, "q": t["question"], "a": t["answer"]},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for faq in FAQS:
        faq_id = _existing_id(conn, faq["translations"]["ru"]["question"])
        if faq_id is not None:
            conn.execute(sa.text("DELETE FROM faqs WHERE id = :id"), {"id": faq_id})
