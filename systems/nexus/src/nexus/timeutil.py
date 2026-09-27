from __future__ import annotations
from decimal import Decimal, InvalidOperation

def timestamp_to_ns(value: str | int | float) -> tuple[int, bool]:
    """Parse epoch seconds/ms/us/ns or decimal epoch seconds without discarding fractions."""
    s = str(value).strip()
    if not s:
        raise ValueError("empty timestamp")
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"invalid timestamp: {value!r}") from e
    fractional = d != d.to_integral_value()
    mag = abs(d)
    if mag < Decimal("1e11"):      # seconds
        ns = int(d * Decimal("1e9"))
    elif mag < Decimal("1e14"):    # milliseconds
        ns = int(d * Decimal("1e6"))
    elif mag < Decimal("1e17"):    # microseconds
        ns = int(d * Decimal("1e3"))
    else:                             # nanoseconds
        ns = int(d)
    return ns, fractional
