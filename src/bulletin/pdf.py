"""PDF бюллетеня: все реквизиты, решения членов Совета и QR-код проверки внизу.

Документ собирается из текущих данных при каждом запросе, поэтому всегда
актуален: статус, подписи и срок — на момент выгрузки (время печатается в
документе). QR ведёт на страницу проверки `BULLETIN_VERIFY_BASE_URL/<public_id>`.

Шрифт DejaVu Sans лежит в проекте (src/bulletin/fonts, свободная лицензия):
кириллица и узбекская латиница (Oʻ, gʻ) печатаются одинаково на любом сервере.
"""

from datetime import datetime
from pathlib import Path

import qrcode
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src.bulletin.enums import DECISION_NAMES, TASHKENT_TZ, BulletinStatus
from src.bulletin.mappers import member_status, verify_url
from src.bulletin.models.bulletin_model import BulletinORM

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FONT = "DejaVu"

STATUS_NAMES = {
    BulletinStatus.PENDING: "Ожидает отправки",
    BulletinStatus.PUBLISHED: "Отправлен членам Совета",
    BulletinStatus.PARTIALLY_SIGNED: "Подписан частично",
    BulletinStatus.COMPLETED: "Подписан всеми членами Совета",
    BulletinStatus.EXPIRED: "Срок подписания истёк",
    BulletinStatus.CANCELLED: "Аннулирован",
}
MEMBER_STATUS_NAMES = {
    "NEW": "Не открывал",
    "VIEWED": "Открыл, не подписал",
    "SIGNED": "Подписал",
    "OVERDUE": "Не подписал в срок",
    "CANCELLED": "Не подписал (аннулирован)",
}

QR_SIZE = 38  # мм
LINE = 6  # высота строки, мм


def fmt(value: datetime | None) -> str:
    return value.astimezone(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M") if value else "—"


def file_size(size: int | None) -> str:
    if not size:
        return "—"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} КБ"
    return f"{size / 1024 / 1024:.1f} МБ"


class BulletinPDF(FPDF):
    def __init__(self, number: str):
        super().__init__(format="A4")
        self.number = number
        self.add_font(FONT, "", str(FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font(FONT, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=18)
        self.set_title(f"Бюллетень {number}")
        self.set_author("Yoshlar Fondi")
        self.set_creator("Yoshlar Fondi")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(FONT, size=8)
        self.set_text_color(120)
        self.cell(0, 5, f"Бюллетень {self.number} · стр. {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0)

    def heading(self, text: str) -> None:
        self.ln(3)
        self.set_font(FONT, "B", 11)
        self.cell(0, LINE + 1, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(FONT, size=10)

    def fields(self, rows: list[tuple[str, str]]) -> None:
        self.set_font(FONT, size=10)
        with self.table(
            col_widths=(52, 122),
            text_align="LEFT",
            first_row_as_headings=False,
            line_height=LINE,
            padding=1.5,
        ) as table:
            for label, value in rows:
                row = table.row()
                row.cell(label)
                row.cell(value or "—")


def draw_qr(pdf: FPDF, data: str, x: float, y: float, size: float) -> None:
    """QR векторно, без растровой картинки: чёткий при печати. Тёмные клетки строки
    рисуются сплошными полосами — без швов между соседними клетками."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    cell = size / len(matrix)
    pdf.set_fill_color(0)
    for row_index, row in enumerate(matrix):
        start = None
        for col_index, dark in enumerate([*row, False]):
            if dark and start is None:
                start = col_index
            elif not dark and start is not None:
                width = (col_index - start) * cell
                pdf.rect(x + start * cell, y + row_index * cell, width, cell, style="F")
                start = None


def render_bulletin_pdf(bulletin: BulletinORM, now: datetime) -> bytes:
    number = bulletin.number or f"#{bulletin.id}"
    pdf = BulletinPDF(number)
    pdf.add_page()

    # ---------- шапка ----------
    pdf.set_font(FONT, "B", 9)
    pdf.set_text_color(90)
    pdf.cell(0, 5, "YOSHLAR FONDI", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0)
    pdf.set_font(FONT, "B", 16)
    pdf.cell(0, 9, "Бюллетень члена Совета Фонда", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(FONT, size=11)
    pdf.cell(
        0,
        LINE,
        f"№ {number} от {bulletin.created_at.astimezone(TASHKENT_TZ):%d.%m.%Y}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)

    # ---------- реквизиты ----------
    pdf.heading("Сведения о бюллетене")
    application = bulletin.application
    rows = [
        ("Название", bulletin.name),
        ("Статус", STATUS_NAMES.get(bulletin.status, str(bulletin.status))),
        ("Дата создания", fmt(bulletin.created_at)),
        (
            "Дата отправки",
            fmt(bulletin.published_at)
            if bulletin.published_at
            else f"{fmt(bulletin.send_at)} (плановая)",
        ),
        ("Срок подписания", fmt(bulletin.deadline_at)),
    ]
    if bulletin.completed_at:
        rows.append(("Подписан всеми", fmt(bulletin.completed_at)))
    if bulletin.created_by:
        rows.append(
            ("Создал", bulletin.created_by.full_name or bulletin.created_by.username or "—")
        )
    if application is not None:
        rows.append(
            (
                "Заявка",
                f"№ {application.number or application.id}"
                + (
                    f", {application.applicant_full_name}"
                    if application.applicant_full_name
                    else ""
                ),
            )
        )
    if bulletin.status == BulletinStatus.CANCELLED:
        rows.append(("Аннулирован", fmt(bulletin.cancelled_at)))
        rows.append(("Причина аннулирования", bulletin.cancel_reason or "—"))
    pdf.fields(rows)

    # ---------- описание ----------
    pdf.heading("Описание")
    pdf.multi_cell(0, LINE - 0.5, bulletin.description, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---------- файл ----------
    pdf.heading("Прикреплённый файл")
    if bulletin.file_path:
        pdf.fields(
            [
                ("Имя файла", bulletin.file_name or "—"),
                ("Размер", file_size(bulletin.file_size)),
                ("SHA-256", bulletin.file_sha256 or "—"),
            ]
        )
    else:
        pdf.cell(0, LINE, "Файл не прикреплён", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---------- решения членов Совета ----------
    pdf.heading("Решения членов Совета")
    if not bulletin.signatures:
        pdf.cell(
            0,
            LINE,
            "Бюллетень ещё не отправлен членам Совета",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    else:
        signed = [s for s in bulletin.signatures if s.signed_at is not None]
        agree = sum(1 for s in signed if s.decision and s.decision.value == "AGREE")
        pdf.cell(
            0,
            LINE,
            f"Подписали {len(signed)} из {len(bulletin.signatures)}: «Согласен» — {agree}, "
            f"«Против» — {len(signed) - agree}, не подписали — "
            f"{len(bulletin.signatures) - len(signed)}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)
        pdf.set_font(FONT, size=9)
        with pdf.table(
            col_widths=(8, 62, 32, 34, 38),
            text_align=("CENTER", "LEFT", "LEFT", "LEFT", "LEFT"),
            line_height=LINE - 1,
            padding=1.5,
        ) as table:
            header = table.row()
            for title in ("№", "Член Совета", "Решение", "Дата подписи", "Сертификат ЭЦП"):
                header.cell(title)
            for index, s in enumerate(bulletin.signatures, start=1):
                name = s.member_full_name or (
                    s.council_member.full_name if s.council_member else None
                )
                if s.signed_at is not None:
                    decision = DECISION_NAMES.get(s.decision, "—") if s.decision else "—"
                    certificate = s.cert_serial_number or "—"
                else:
                    decision = MEMBER_STATUS_NAMES.get(
                        member_status(bulletin, s, now).value, "Не подписал"
                    )
                    certificate = "—"
                row = table.row()
                row.cell(str(index))
                row.cell(name or "—")
                row.cell(decision)
                row.cell(fmt(s.signed_at))
                row.cell(certificate)
        pdf.set_font(FONT, size=10)

    # ---------- QR внизу последней страницы ----------
    block = QR_SIZE + 4
    if pdf.get_y() + block > pdf.h - pdf.b_margin:
        pdf.add_page()
    y = pdf.h - pdf.b_margin - QR_SIZE
    x = pdf.l_margin
    pdf.set_draw_color(200)
    pdf.line(pdf.l_margin, y - 4, pdf.w - pdf.r_margin, y - 4)
    url = verify_url(bulletin)
    draw_qr(pdf, url, x, y, QR_SIZE)

    text_x = x + QR_SIZE + 6
    pdf.set_xy(text_x, y + 2)
    pdf.set_font(FONT, "B", 10)
    pdf.cell(0, LINE, "Проверка подлинности", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_font(FONT, size=9)
    pdf.multi_cell(
        pdf.w - pdf.r_margin - text_x,
        5,
        "Отсканируйте QR-код, чтобы проверить документ и актуальный статус подписей "
        f"на сайте Фонда:\n{url}\n\nДокумент сформирован {fmt(now)} (Ташкент).",
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )

    return bytes(pdf.output())
