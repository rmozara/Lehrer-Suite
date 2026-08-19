from __future__ import annotations

import sqlite3
import secrets
from pathlib import Path


class IdentityRegistry:
    def __init__(self, path: Path, strict: bool = True):
        self.path = Path(path)
        self.strict = strict

    def resolve(
        self,
        student_key: str,
        *,
        name: str,
        class_id: str,
        existing_token: str | None = None,
        source: str,
    ) -> str:
        if not self.path.exists():
            if not self.strict:
                return existing_token or secrets.token_urlsafe(24)
            raise ValueError(
                "Die gemeinsamen QR-Identitäten fehlen. Bitte zuerst die "
                "Namensliste in QR importieren."
            )
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            year = conn.execute(
                "SELECT value FROM meta WHERE key='active_school_year'"
            ).fetchone()
            if not year:
                raise ValueError("Im QR-Generator ist kein aktives Schuljahr festgelegt.")
            row = conn.execute(
                """SELECT public_token FROM identities
                   WHERE school_year=? AND student_key=? AND active=1""",
                (year["value"], student_key.strip()),
            ).fetchone()
            if not row:
                raise ValueError(
                    f"Schüler-ID {student_key} fehlt im gemeinsamen QR-Register "
                    f"für das Schuljahr {year['value']}."
                )
            return str(row["public_token"])

    def roster_for_class(self, class_id: str) -> list[dict]:
        if not self.path.exists():
            raise ValueError(
                "Die gemeinsamen QR-Identitäten fehlen. Bitte zuerst die "
                "Namensliste in QR importieren."
            )
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            year = conn.execute(
                "SELECT value FROM meta WHERE key='active_school_year'"
            ).fetchone()
            if not year:
                raise ValueError("Im QR-Generator ist kein aktives Schuljahr festgelegt.")
            return [
                dict(row)
                for row in conn.execute(
                    """SELECT student_key, public_token, name, class_id, list_position
                       FROM identities
                       WHERE school_year=? AND class_id=? AND active=1
                       ORDER BY list_position""",
                    (year["value"], class_id.strip()),
                )
            ]

    def token_by_short_code(self, short_code: str) -> str | None:
        if not self.path.exists():
            return None
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(identities)")
            }
            if "short_code" not in columns:
                return None
            year = conn.execute(
                "SELECT value FROM meta WHERE key='active_school_year'"
            ).fetchone()
            if not year:
                return None
            row = conn.execute(
                """SELECT public_token FROM identities
                   WHERE school_year=? AND short_code=? COLLATE NOCASE
                   AND active=1""",
                (year["value"], short_code.strip()),
            ).fetchone()
            return str(row["public_token"]) if row else None

    def classes(self) -> list[str]:
        if not self.path.exists():
            return []
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            year = conn.execute(
                "SELECT value FROM meta WHERE key='active_school_year'"
            ).fetchone()
            if not year:
                return []
            return [
                str(row["class_id"])
                for row in conn.execute(
                    """SELECT DISTINCT class_id FROM identities
                       WHERE school_year=? AND active=1 ORDER BY class_id""",
                    (year["value"],),
                )
            ]
