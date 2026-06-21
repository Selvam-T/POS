import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import config

# This QR is a generic merchant PayNow identifier only. It does not include an
# amount, so customers enter the cashier-confirmed value in their banking app.

QR_CARD_MARGIN = 30



def pad2(n):
    return str(n).zfill(2)


def tlv(tag, value):
    return f"{tag}{pad2(len(value))}{value}"


def crc16_ccitt_false(data: str) -> str:
    crc = 0xFFFF
    for ch in data:
        crc ^= (ord(ch) << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def get_currency_numeric(currency_code: str) -> str:
    mapping = {
        "SGD": "702",
    }
    return mapping[currency_code.upper()]


def get_proxy_type_value(proxy_type: str) -> str:
    # Based on public PayNow examples:
    # 0 = mobile, 2 = UEN
    proxy_type = proxy_type.upper()
    if proxy_type == "UEN":
        return "2"
    if proxy_type == "MOBILE":
        return "0"
    raise ValueError("Unsupported paynow_proxy_type. Use 'UEN' or 'MOBILE'.")


def make_expiry_yyyymmdd():
    # Common public examples use YYYYMMDD for expiry
    dt = datetime.now() + timedelta(seconds=getattr(config, "expiry_seconds", 300))
    return dt.strftime("%Y%m%d")


def build_paynow_payload(ref_value: str | None = None):
    """Build a generic PayNow dynamic QR payload without embedding an amount.

    The visual output intentionally mirrors `test_qr.py`; only tag 54
    (transaction amount) is omitted so customers enter the amount manually.
    """
    editable = "0"
    expiry = make_expiry_yyyymmdd()
    currency_numeric = get_currency_numeric(config.currency)
    proxy_type_value = get_proxy_type_value(config.paynow_proxy_type)

    merchant_account_info = (
        tlv("00", "SG.PAYNOW") +
        tlv("01", proxy_type_value) +
        tlv("02", str(config.paynow_proxy_value)) +
        tlv("03", editable) +
        tlv("04", expiry)
    )

    if ref_value is None:
        ref_value = getattr(config, "merchant_name", "")

    additional_data = tlv("01", str(ref_value))

    payload = ""
    payload += tlv("00", "01")                          # Payload Format Indicator
    payload += tlv("01", "12")                          # Dynamic QR
    payload += tlv("26", merchant_account_info)         # Merchant Account Info
    payload += tlv("52", str(config.mcc))               # MCC
    payload += tlv("53", currency_numeric)              # Currency
    payload += tlv("58", config.country_code)           # Country
    payload += tlv("59", config.merchant_name[:25])     # Merchant Name
    payload += tlv("60", config.merchant_city[:15])     # Merchant City
    payload += tlv("62", additional_data)               # Reference / bill number

    payload_for_crc = payload + "6304"
    crc = crc16_ccitt_false(payload_for_crc)
    return payload_for_crc + crc, expiry


def get_qr_error_level(level: str):
    level = (level or "M").upper()
    mapping = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    return mapping.get(level, qrcode.constants.ERROR_CORRECT_M)


def add_footer_text(img, text):
    img = img.convert("RGB")
    width, height = img.size

    measure = ImageDraw.Draw(Image.new("RGB", (1, 1), "white"))
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = ImageFont.load_default()

    bbox = measure.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    footer_gap = QR_CARD_MARGIN

    canvas = Image.new("RGB", (width, height + footer_gap + text_h), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)

    x = (width - text_w) // 2
    y = height + footer_gap - bbox[1]

    draw.text((x, y), text, fill="#8F1F7C", font=font)
    return canvas


def generate_qr_image(payload, expiry_text):
    qr = qrcode.QRCode(
        version=None,
        error_correction=get_qr_error_level(config.error_correction),
        box_size=config.box_size,
        border=config.border,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="#8F1F7C",
        back_color="white"
    ).convert("RGB")
    img = add_footer_text(img, f"Valid till {datetime.strptime(expiry_text, '%Y%m%d').strftime('%b %d, %Y')}")
    return img

def add_qr_card(qr_img):
    qr_img = qr_img.convert("RGBA")

    margin = QR_CARD_MARGIN
    radius = 30

    new_w = qr_img.width + margin * 2
    new_h = qr_img.height + margin * 2

    card = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 0))

    mask = Image.new("L", (new_w, new_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, new_w - 1, new_h - 1),
        radius=radius,
        fill=255
    )

    white_bg = Image.new("RGBA", (new_w, new_h), "white")
    card = Image.composite(white_bg, card, mask)

    card.paste(qr_img, (margin, margin), qr_img)

    return card

def overlay_logo(qr_img):

    logo_path = os.path.join(config.ASSETS_DIR, 'images', config.logo)

    logo = Image.open(logo_path).convert("RGBA")

    qr_w, qr_h = qr_img.size

    logo_size = int(qr_w * 0.25)

    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    pos = (
        (qr_w - logo_size) // 2,
        (qr_h - logo_size) // 2
    )

    qr_img = qr_img.convert("RGBA")
    qr_img.paste(logo, pos, mask=logo)

    return qr_img


def generate_qr_pixmap(ref_value: str | None = None, target_size: int = 250):
    """Return a PyQt5 QPixmap containing the generated QR code card.

    - Mirrors the card rendered by `test_qr.py`.
    - Fits the card within `target_size` while preserving aspect and alpha.
    """
    try:
        from PyQt5.QtGui import QImage, QPixmap
    except Exception:
        raise RuntimeError("PyQt5 is required to produce a QPixmap")

    payload, expiry = build_paynow_payload(ref_value)
    img = generate_qr_image(payload, expiry)
    img = overlay_logo(img)
    card = add_qr_card(img)

    if target_size:
        w, h = card.size
        scale = min(target_size / w, target_size / h)
        resized_size = (max(1, round(w * scale)), max(1, round(h * scale)))
        card = card.resize(resized_size, Image.LANCZOS)

    # Convert PIL image to QPixmap
    rgba = card.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888)
    pix = QPixmap.fromImage(qimg)
    return pix

# End of module. Use `generate_qr_pixmap()` from application code to obtain a QPixmap.
