"""
EAN-13 vonalkód ellenőrzése.
"""


def is_valid_ean13(code: str) -> bool:
    """Igaz, ha a *code* érvényes EAN-13 vonalkód.

    Az érvényes kód pontosan 13 ASCII számjegy, amelynek utolsó számjegye
    megegyezik az első 12-ből számított EAN-13 ellenőrző számjeggyel. Betűt,
    szóközt, speciális karaktert tartalmazó, rossz hosszúságú vagy hibás
    ellenőrző számjegyű kód érvénytelen.
    """
    if len(code) != 13 or not (code.isascii() and code.isdigit()):
        return False

    digits = [int(c) for c in code]
    # 1..12 pozíció (1-alapú): páratlan pozíció súlya 1, páros pozícióé 3.
    checksum = sum(
        digit * (3 if (i % 2) else 1)
        for i, digit in enumerate(digits[:12])
    )
    check_digit = (10 - (checksum % 10)) % 10
    return check_digit == digits[12]
