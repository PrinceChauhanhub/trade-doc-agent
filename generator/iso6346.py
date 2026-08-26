# generator/iso6346.py
"""ISO 6346 container number check digit."""

_LETTER_VALUES = {}
_value = 10
for _char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    if _value in (11, 22, 33):
        _value += 1
    _LETTER_VALUES[_char] = _value
    _value += 1


def check_digit(owner_serial: str) -> int:
    """Compute the check digit for the first 10 chars of a container number."""
    if len(owner_serial) != 10:
        raise ValueError("expected 4 letters + 6 digits")

    total = 0
    for i, char in enumerate(owner_serial.upper()):
        value = _LETTER_VALUES[char] if char.isalpha() else int(char)
        total += value * (2 ** i)
    return total % 11 % 10


def make_container_number(prefix: str, serial: int) -> str:
    """Build a valid container number, e.g. MSCU1234565."""
    body = f"{prefix}{serial:06d}"
    return f"{body}{check_digit(body)}"


def is_valid(container_number: str) -> bool:
    if len(container_number) != 11:
        return False
    return check_digit(container_number[:10]) == int(container_number[10])