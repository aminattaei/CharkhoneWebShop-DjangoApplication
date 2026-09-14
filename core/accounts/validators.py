from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_national_id(value):
    """
    Validate Iranian national ID using the official check-digit algorithm.
    """

    if not value.isdigit():
        raise ValidationError(
            _("National ID must contain only digits.")
        )

    if len(value) != 10:
        raise ValidationError(
            _("National ID must contain exactly 10 digits.")
        )

    # Reject IDs with all identical digits
    if len(set(value)) == 1:
        raise ValidationError(
            _("Invalid national ID.")
        )

    digits = [int(digit) for digit in value]

    # Calculate check digit
    checksum = sum(
        digits[i] * (10 - i)
        for i in range(9)
    )

    remainder = checksum % 11
    check_digit = digits[9]

    if remainder < 2:
        is_valid = check_digit == remainder
    else:
        is_valid = check_digit == (11 - remainder)

    if not is_valid:
        raise ValidationError(
            _("Invalid Iranian national ID.")
        )