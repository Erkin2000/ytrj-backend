"""PDF акта выполненных работ (dalolatnoma) в форме, принятой в Фонде.

«TASDIQLAYMAN» руководителя, заголовок, дата и город, вводная часть с реквизитами
договора и периодом, таблица выполненных работ, заключительные абзацы, строки
подписей «Topshiruvchi» / «Qabul qiluvchi» (после подписи — штамп E-IMZO с владельцем
и серийным номером сертификата), приложение со скриншотами и QR-код проверки.

Пока акт не подписан руководителем, на каждой странице — водяной знак «QORALAMA».
Подписанный акт формируется один раз, сохраняется на диск и больше не меняется.
"""

from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image

from src.act.enums import ActSignerRole, ActStatus
from src.act.mappers import verify_url
from src.act.models.act_model import ActORM, ActSignatureORM
from src.act.text import short_name, uz_date, uz_period, uz_quoted_date
from src.bulletin.enums import TASHKENT_TZ
from src.bulletin.pdf import draw_qr
from src.config import settings

FONTS_DIR = Path(__file__).resolve().parent.parent / "bulletin" / "fonts"
FONT = "DejaVu"
LINE = 6
BODY = 11
QR_SIZE = 32
COLS = (12, 88, 32, 33)  # t/r, mazmun, muddat, izoh — 165 мм


def fmt(value: datetime) -> str:
    return value.astimezone(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M")


class ActPDF(FPDF):
    def __init__(self, number: str, draft: bool):
        super().__init__(format="A4")
        self.number = number
        self.draft = draft
        self.add_font(FONT, "", str(FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font(FONT, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
        # Поля как в шаблоне Word: слева 30, справа 15, сверху и снизу 20 мм.
        self.set_margins(30, 20, 15)
        self.set_auto_page_break(True, margin=20)
        self.set_title(f"Dalolatnoma {number}")
        self.set_author("Yoshlar Fondi")
        self.set_creator("Yoshlar Fondi")

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def header(self) -> None:
        if not self.draft:
            return
        with self.local_context(fill_opacity=0.08, text_color=(0, 0, 0)):
            self.set_font(FONT, "B", 80)
            width = self.get_string_width("QORALAMA")
            cx, cy = self.w / 2, self.h / 2
            with self.rotation(35, x=cx, y=cy):
                self.text(cx - width / 2, cy + 10, "QORALAMA")
        self.set_font(FONT, size=BODY)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(FONT, size=8)
        self.set_text_color(120)
        self.cell(0, 5, f"Dalolatnoma {self.number} · {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(0)

    def para(self, text: str, *, indent: bool = True, after: float = 1.5) -> None:
        self.set_font(FONT, size=BODY)
        prefix = "        " if indent else ""
        self.multi_cell(0, LINE, prefix + text, align="J", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(after)


def _stamp(pdf: ActPDF, signature: ActSignatureORM, x: float, width: float) -> None:
    """Штамп электронной подписи под строкой подписи."""
    pdf.set_x(x)
    pdf.set_font(FONT, size=7.5)
    pdf.set_text_color(30, 64, 175)
    pdf.set_draw_color(30, 64, 175)
    lines = (
        "ERI (E-IMZO) bilan imzolangan\n"
        f"{signature.cert_full_name or signature.signer_full_name or '—'}\n"
        f"Sertifikat: {signature.cert_serial_number or '—'}\n"
        f"Vaqti: {fmt(signature.signed_at)}"
    )
    pdf.multi_cell(width, 3.6, lines, border=1, padding=1.2, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0)
    pdf.set_draw_color(0)


def _signature_line(pdf: ActPDF, label: str, name: str, signature: ActSignatureORM | None) -> None:
    pdf.set_font(FONT, size=BODY)
    pdf.cell(45, LINE, label)
    pdf.cell(55, LINE, "_______________", align="C")
    pdf.cell(0, LINE, short_name(name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if signature is not None:
        _stamp(pdf, signature, pdf.l_margin + 45, 75)
    pdf.ln(4)


def _image_height(path: Path, width: float) -> float:
    with Image.open(path) as image:
        w, h = image.size
    return width * h / w if w else width


def render_act_pdf(act: ActORM, now: datetime) -> bytes:
    contract = act.contract
    number = act.number or f"#{act.id}"
    signed = act.status == ActStatus.SIGNED
    pdf = ActPDF(number, draft=not signed)
    pdf.add_page()

    signatures = {s.role: s for s in act.signatures}
    contractor_sig = signatures.get(ActSignerRole.CONTRACTOR)
    approver_sig = signatures.get(ActSignerRole.APPROVER)
    customer = settings.ACT_CUSTOMER_NAME
    approver_short = short_name(contract.approver_name)

    # ---------- «TASDIQLAYMAN» ----------
    block_x = pdf.l_margin + 90
    block_w = pdf.content_width - 90
    pdf.set_xy(block_x, pdf.get_y())
    pdf.set_font(FONT, "B", BODY)
    pdf.cell(block_w, LINE, "“TASDIQLAYMAN”", align="C", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_font(FONT, size=BODY)
    pdf.multi_cell(
        block_w,
        LINE - 0.5,
        f"{customer} {contract.approver_title}",
        align="C",
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)
    pdf.set_x(block_x)
    pdf.cell(
        block_w,
        LINE,
        f"_______________ {approver_short}",
        align="C",
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )
    pdf.set_font(FONT, size=8)
    pdf.cell(block_w, 4, "(FISh)", align="C", new_x=XPos.LEFT, new_y=YPos.NEXT)
    if approver_sig is not None:
        _stamp(pdf, approver_sig, block_x, block_w)
    pdf.set_x(block_x)
    pdf.set_font(FONT, size=BODY)
    pdf.cell(
        block_w,
        LINE + 2,
        uz_quoted_date(act.act_date),
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(6)

    # ---------- заголовок ----------
    pdf.set_font(FONT, "B", BODY + 1)
    pdf.cell(
        0,
        LINE,
        "Bajarilgan ishlarni qabul qilish va topshirish",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.cell(0, LINE + 1, "DALOLATNOMASI", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)
    pdf.set_font(FONT, size=BODY)
    pdf.cell(pdf.content_width / 2, LINE, uz_date(act.act_date))
    pdf.cell(0, LINE, settings.ACT_CITY, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ---------- вводная часть ----------
    pdf.para(
        f"Mazkur dalolatnoma {customer} {contract.approver_title} {approver_short} keyingi "
        "o‘rinlarda “Buyurtmachi” deb yuritiladi va fuqaro "
        f"{contract.contractor_name} keyingi o‘rinlarda “Ijrochi” deb yuritiladi, tomonidan tuzildi."
    )
    pdf.para(
        "Ijrochi taraflar o‘rtasida tuzilgan "
        f"{contract.signed_on:%d.%m.%Y}dagi {contract.number}-sonli fuqarolik huquqiy tusdagi "
        f"shartnomasiga muvofiq {uz_period(act.period_from, act.period_to)} Buyurtmachi "
        f"tomonidan topshirilgan {act.intro} bo‘yicha quyidagi xizmatlarni bajardi:",
        after=3,
    )

    # ---------- таблица работ ----------
    pdf.set_font(FONT, size=10)
    with pdf.table(
        col_widths=COLS,
        text_align=("CENTER", "JUSTIFY", "CENTER", "CENTER"),
        line_height=5,
        padding=1.5,
        repeat_headings=1,
    ) as table:
        header = table.row()
        pdf.set_font(FONT, "B", 10)
        for title in ("t/r", "Bajarilgan ishning mazmuni", "Ish bajarilgan muddat", "Izoh"):
            header.cell(title, align="CENTER")
        pdf.set_font(FONT, size=10)
        for index, item in enumerate(act.items, start=1):
            row = table.row()
            row.cell(str(index))
            row.cell(item.content)
            row.cell(item.period_text)
            row.cell(item.note or "")
    pdf.ln(4)

    # ---------- заключение и подписи ----------
    pdf.para(
        "Ijrochi yuqorida bajarilgan ishlar (xizmatlar)ni topshirdi, o‘z navbatida Buyurtmachi "
        "ushbu ishlar (xizmatlar)ni qabul qilib oldi."
    )
    pdf.para(
        "Mazkur dalolatnomaga muvofiq qabul qilib olingan ishlar Ijrochiga xizmat haqi to‘lash "
        "uchun asos sifatida qabul qilinadi.",
        after=8,
    )
    if pdf.get_y() + 60 > pdf.h - pdf.b_margin:
        pdf.add_page()
    _signature_line(pdf, "“Topshiruvchi”", contract.contractor_name, contractor_sig)
    _signature_line(pdf, "“Qabul qiluvchi”", contract.approver_name, approver_sig)

    # ---------- приложение ----------
    if act.attachments:
        from src.act.storage import ActFileStorage

        storage = ActFileStorage()
        pdf.add_page()
        pdf.set_font(FONT, "B", BODY)
        pdf.multi_cell(0, LINE, act.appendix_title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        width = pdf.content_width
        for index, attachment in enumerate(act.attachments, start=1):
            path = storage.absolute_path(attachment.file_path)
            img_w = width
            img_h = _image_height(path, img_w)
            max_h = 150
            if img_h > max_h:
                img_w = img_w * max_h / img_h
                img_h = max_h
            needed = img_h + (LINE * 2 if attachment.url else LINE) + 6
            if pdf.get_y() + needed > pdf.h - pdf.b_margin:
                pdf.add_page()
            x = pdf.l_margin + (width - img_w) / 2
            pdf.image(str(path), x=x, y=pdf.get_y(), w=img_w, h=img_h)
            pdf.set_y(pdf.get_y() + img_h + 1.5)
            pdf.set_font(FONT, "B", 10)
            pdf.multi_cell(
                0,
                5,
                f"{index}. {attachment.caption}",
                align="C",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            if attachment.url:
                pdf.set_font(FONT, size=8.5)
                pdf.set_text_color(90)
                pdf.cell(0, 4.5, attachment.url, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(0)
            pdf.ln(5)

    # ---------- QR проверки ----------
    block = QR_SIZE + 6
    if pdf.get_y() + block > pdf.h - pdf.b_margin:
        pdf.add_page()
    y = pdf.h - pdf.b_margin - QR_SIZE
    x = pdf.l_margin
    pdf.set_draw_color(200)
    pdf.line(pdf.l_margin, y - 4, pdf.w - pdf.r_margin, y - 4)
    pdf.set_draw_color(0)
    url = verify_url(act)
    draw_qr(pdf, url, x, y, QR_SIZE)
    text_x = x + QR_SIZE + 6
    pdf.set_xy(text_x, y + 1)
    pdf.set_font(FONT, "B", 9.5)
    pdf.cell(0, 5, "Hujjatni tekshirish", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_font(FONT, size=8.5)
    state = (
        f"Rahbar tomonidan imzolangan: {fmt(act.signed_at)}."
        if signed and act.signed_at
        else "QORALAMA: hujjat hali rahbar tomonidan imzolanmagan."
    )
    pdf.multi_cell(
        pdf.w - pdf.r_margin - text_x,
        4.5,
        f"QR-kodni skanerlang yoki havolani oching:\n{url}\n{state}\n"
        f"Hujjat shakllantirilgan: {fmt(now)} (Toshkent).",
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )
    return bytes(pdf.output())
