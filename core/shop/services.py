from decimal import Decimal


def _coerce_to_decimal(value, default=Decimal("0")):
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return default


def calculate_final_price(price, discount_percent=0):
    price_value = _coerce_to_decimal(price, default=Decimal("0"))
    discount_value = _coerce_to_decimal(discount_percent, default=Decimal("0"))

    discount = Decimal(max(0, min(100, int(discount_value))))
    final = price_value * (Decimal("100") - discount) / Decimal("100")

    return final
