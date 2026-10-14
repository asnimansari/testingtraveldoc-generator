"""ICAO 9303 TD3 (passport) MRZ: build and validate."""
import re


def check_digit(s: str) -> str:
    total = 0
    for i, ch in enumerate(s):
        v = int(ch) if ch.isdigit() else 0 if ch == "<" else ord(ch) - 55
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def _name(s: str) -> str:
    return re.sub(r"[^A-Z]+", "<", s.upper()).strip("<")


def build(doc_no, issuer, surname, given, nationality, dob, sex, expiry, personal=""):
    """dob/expiry are date objects. Returns (line1, line2)."""
    line1 = f"P<{issuer}{_name(surname)}<<{_name(given)}".ljust(44, "<")[:44]
    doc = doc_no.ljust(9, "<")
    pers = personal.ljust(14, "<")
    d, e = dob.strftime("%y%m%d"), expiry.strftime("%y%m%d")
    body = doc + check_digit(doc) + nationality + d + check_digit(d) + sex + e + check_digit(e) + pers + check_digit(pers)
    composite = body[0:10] + body[13:20] + body[21:43]
    return line1, body + check_digit(composite)


def validate(line2: str) -> dict:
    """Which check digits in line 2 are correct."""
    return {
        "passport_no": check_digit(line2[0:9]) == line2[9],
        "dob": check_digit(line2[13:19]) == line2[19],
        "expiry": check_digit(line2[21:27]) == line2[27],
        "personal_no": check_digit(line2[28:42]) == line2[42],
        "composite": check_digit(line2[0:10] + line2[13:20] + line2[21:43]) == line2[43],
    }
