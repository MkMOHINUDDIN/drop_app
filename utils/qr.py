"""QR code generation utilities."""

import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_qr_png(url, box_size=10, border=2):
    """
    Generate a QR code PNG image for the given URL.
    Returns a BytesIO buffer positioned at the start.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer
