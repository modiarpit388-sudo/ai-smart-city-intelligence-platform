"""Password rules. Change the values below to make the policy easier or stricter."""
import re

MIN_LENGTH = 8
REQUIRE_UPPER = True     # A-Z
REQUIRE_LOWER = True     # a-z
REQUIRE_DIGIT = True     # 0-9
REQUIRE_SPECIAL = True   # anything that is not a letter or digit, e.g.  @ # $ % ! ? & * _ -


def check_password(pw: str):
    """Return None when the password is acceptable, otherwise a readable error message."""
    pw = pw or ""
    needs = []
    if len(pw) < MIN_LENGTH:
        needs.append(f"at least {MIN_LENGTH} characters")
    if REQUIRE_UPPER and not re.search(r"[A-Z]", pw):
        needs.append("an uppercase letter (A-Z)")
    if REQUIRE_LOWER and not re.search(r"[a-z]", pw):
        needs.append("a lowercase letter (a-z)")
    if REQUIRE_DIGIT and not re.search(r"\d", pw):
        needs.append("a digit (0-9)")
    if REQUIRE_SPECIAL and not re.search(r"[^A-Za-z0-9]", pw):
        needs.append("a special character (e.g. @ # $ % !)")
    if not needs:
        return None
    return "Password must contain " + ", ".join(needs[:-1]) + (" and " if len(needs) > 1 else "") + needs[-1] + "."
