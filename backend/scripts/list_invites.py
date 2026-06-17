import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from app.core.logging import configure_logging
from app.crud.repositories import invites
from app.db import create_db_and_tables, engine, seed_defaults


def main() -> None:
    configure_logging()
    create_db_and_tables()
    seed_defaults()
    with Session(engine) as session:
        rows = invites.available(session)
        if not rows:
            print("No available invite codes.")
            return
        print("Available invite codes:")
        for invite in rows:
            remaining = invite.max_uses - invite.used_count
            print(
                f"- {invite.code} | remaining={remaining} | expires_at={invite.expires_at.isoformat()}"
            )


if __name__ == "__main__":
    main()

