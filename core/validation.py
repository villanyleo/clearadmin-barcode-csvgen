"""
EAN-13 barcode validation.
"""


def is_valid_ean13(code: str) -> bool:
    """Return True if *code* is a valid EAN-13 barcode.

    A valid code is exactly 13 ASCII digits whose final digit matches the
    EAN-13 check digit computed from the first 12. Anything with letters,
    spaces, special characters, a wrong length, or a bad check digit fails.
    """
    if len(code) != 13 or not (code.isascii() and code.isdigit()):
        return False

    digits = [int(c) for c in code]
    # Positions 1..12 (1-indexed): odd positions weight 1, even positions weight 3.
    checksum = sum(
        digit * (3 if (i % 2) else 1)
        for i, digit in enumerate(digits[:12])
    )
    check_digit = (10 - (checksum % 10)) % 10
    return check_digit == digits[12]
