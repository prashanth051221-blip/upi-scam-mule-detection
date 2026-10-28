"""Formatting filters: Indian rupee grouping, percentages, scores."""

from __future__ import annotations

import math

from django import template

register = template.Library()


def _indian(n: int) -> str:
    s = str(abs(n))
    if len(s) <= 3:
        out = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        out = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + out


@register.filter
def inr(value):
    """12345678 -> ₹1,23,45,678"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "–"
    if math.isnan(v):
        return "–"
    return "₹" + _indian(int(round(v)))


@register.filter
def inr_short(value):
    """Compact rupees: ₹4.2 lakh, ₹1.3 crore."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "–"
    if v >= 1e7:
        return f"₹{v / 1e7:.2f} crore"
    if v >= 1e5:
        return f"₹{v / 1e5:.1f} lakh"
    return "₹" + _indian(int(round(v)))


@register.filter
def num(value):
    try:
        return _indian(int(round(float(value))))
    except (TypeError, ValueError):
        return "–"


@register.filter
def pct(value, digits=1):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "–"
    if math.isnan(v):
        return "–"
    return f"{v * 100:.{int(digits)}f}%"


@register.filter
def dec(value, digits=3):
    try:
        return f"{float(value):.{int(digits)}f}"
    except (TypeError, ValueError):
        return "–"


@register.filter
def level_class(level):
    return {"High": "lv-high", "Medium": "lv-med", "Medium (ring)": "lv-ring",
            "Low": "lv-low", "Warm-up": "lv-warm"}.get(str(level), "lv-low")


@register.filter
def get(d, key):
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.filter
def replace_us(s):
    return str(s).replace("_", " ")


@register.filter
def strip_prefix(s):
    """'4. Hybrid (RF + graph + IF score)' -> 'Hybrid (RF + graph + IF score)'"""
    s = str(s)
    return s.split(". ", 1)[1] if ". " in s[:5] else s


@register.filter
def width(value, scale=100):
    try:
        return f"{max(0.0, min(100.0, float(value) * 100 / float(scale))):.1f}"
    except (TypeError, ValueError):
        return "0"


_SCAM_LABELS = {
    "qr scam": "QR scam", "sim swap": "SIM swap", "fake refund call": "Fake refund call",
    "screen share": "Screen-share drain", "fake merchant collect": "Fake-merchant collect",
    "mule layering": "Mule layering", "normal": "Normal",
}


@register.filter
def scam_label(s):
    key = str(s).replace("_", " ").strip().lower()
    return _SCAM_LABELS.get(key, key.capitalize())
