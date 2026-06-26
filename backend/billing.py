"""UPI billing helpers — build a UPI payment intent link + an inline SVG QR.

No payment gateway required: we generate a standard ``upi://pay`` deep link to
the creator's VPA. On mobile this opens GPay/PhonePe/Paytm etc. The user pays
and submits the UPI transaction reference; an admin approves to unlock Pro.
(For automatic verification you can later plug in Razorpay/Cashfree webhooks.)
"""
from __future__ import annotations

import base64
from urllib.parse import quote

from config import settings


def upi_link(amount: int, note: str, txn_ref: str) -> str:
    pa = quote(settings.upi_vpa or "example@upi")
    pn = quote(settings.upi_payee_name or "Jnana Setu")
    tn = quote(note)
    tr = quote(txn_ref)
    return (
        f"upi://pay?pa={pa}&pn={pn}&am={amount}&cu=INR&tn={tn}&tr={tr}"
    )


def qr_svg_data_uri(data: str) -> str:
    """Return an SVG QR for the given data as a data: URI (no Pillow needed)."""
    try:
        import qrcode
        import qrcode.image.svg as svg

        img = qrcode.make(data, image_factory=svg.SvgPathImage)
        import io

        buf = io.BytesIO()
        img.save(buf)
        svg_bytes = buf.getvalue()
        b64 = base64.b64encode(svg_bytes).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"
    except Exception:
        return ""


def build_order(payment_id: str, amount: int) -> dict:
    note = f"Jnana Setu Pro ({payment_id})"
    link = upi_link(amount, note, payment_id)
    return {
        "payment_id": payment_id,
        "amount": amount,
        "currency": "INR",
        "vpa": settings.upi_vpa,
        "payee_name": settings.upi_payee_name,
        "upi_link": link,
        "qr_svg": qr_svg_data_uri(link),
        "configured": bool(settings.upi_vpa),
        "instructions": (
            "Scan the QR or tap the UPI link to pay, then submit your UPI "
            "transaction reference. Your Pro access is unlocked after approval."
        ),
    }
