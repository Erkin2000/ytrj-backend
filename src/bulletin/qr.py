"""QR-код страницы проверки бюллетеня (SVG, без зависимости от Pillow)."""

import io

import qrcode
import qrcode.image.svg


def qr_svg(data: str) -> bytes:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
        image_factory=qrcode.image.svg.SvgPathFillImage,
    )
    qr.add_data(data)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image().save(buffer)
    return buffer.getvalue()
