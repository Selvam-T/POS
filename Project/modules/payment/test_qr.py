# show_qr.py
# not ideal long-term but just a quick test to confirm QR generation + display works in our environment.
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import config


amount = 1.01
reference = "Vijay pos testing"   # alphanumeric only is safest


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


def build_paynow_payload(amount_value, ref_value):
    editable = "0"   # amount not editable if POS already calculated it
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

    additional_data = tlv("01", ref_value)

    payload = ""
    payload += tlv("00", "01")                          # Payload Format Indicator
    payload += tlv("01", "12")                          # Dynamic QR
    payload += tlv("26", merchant_account_info)         # Merchant Account Info
    payload += tlv("52", str(config.mcc))               # MCC
    payload += tlv("53", currency_numeric)              # Currency
    payload += tlv("54", f"{amount_value:.2f}")         # Amount
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
    footer_h = 60

    canvas = Image.new("RGB", (width, height + footer_h), "white")
    canvas.paste(img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = height + (footer_h - text_h) // 2

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

    margin = 30
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

    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "..", "..", "assets", "images", config.logo)
    logo_path = os.path.normpath(logo_path)

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

def main():
    payload, expiry = build_paynow_payload(amount, reference)
    print("Payload:")
    print(payload)
    print("\nExpiry:", expiry)

    img = generate_qr_image(payload, expiry)
    img = overlay_logo(img)
    img = add_qr_card(img)

    out_path = os.path.abspath("paynow_qr.png")
    img.save(out_path)
    print("\nSaved:", out_path)

    img.show()


if __name__ == "__main__":
    main()