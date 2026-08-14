from decimal import Decimal


def _coerce_to_float(value, default=0.0):
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_final_price(price, discount_percent=0):
    price_value = _coerce_to_float(price, default=0.0)
    discount_value = _coerce_to_float(discount_percent, default=0.0)

    discount = Decimal(max(0, min(100, discount_value)))
    price = Decimal(str(price_value))

    return int(price * (100 - discount) / 100)