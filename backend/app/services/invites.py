import secrets
import string


ALPHABET = string.ascii_uppercase + string.digits


def generate_invite_code(groups: int = 3, group_size: int = 4) -> str:
    parts = [
        "".join(secrets.choice(ALPHABET) for _ in range(group_size))
        for _ in range(groups)
    ]
    return "TEAM-" + "-".join(parts)
