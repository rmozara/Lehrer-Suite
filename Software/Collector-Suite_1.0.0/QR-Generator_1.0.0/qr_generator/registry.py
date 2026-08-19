from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS identities(
  school_year TEXT NOT NULL,
  student_key TEXT NOT NULL COLLATE NOCASE,
  public_token TEXT NOT NULL UNIQUE,
  short_code TEXT NOT NULL UNIQUE COLLATE NOCASE,
  name TEXT NOT NULL,
  class_id TEXT NOT NULL,
  list_position INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(school_year,student_key)
);
"""


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.last_migration_backup: Path | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self._requires_short_code_migration():
            self.last_migration_backup = self._backup_before_migration()
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(identities)")
            }
            if "short_code" not in columns:
                conn.execute("ALTER TABLE identities ADD COLUMN short_code TEXT")
                for row in conn.execute("SELECT rowid FROM identities"):
                    conn.execute(
                        "UPDATE identities SET short_code=? WHERE rowid=?",
                        (self._new_short_code(conn), row["rowid"]),
                    )
                conn.execute(
                    "CREATE UNIQUE INDEX identities_short_code "
                    "ON identities(short_code COLLATE NOCASE)"
                )

    def _requires_short_code_migration(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return False
        with sqlite3.connect(self.path) as conn:
            has_identities = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='identities'"
            ).fetchone()
            if not has_identities:
                return False
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(identities)")
            }
        return "short_code" not in columns

    def _backup_before_migration(self) -> Path:
        backup_dir = self.path.parent / "Collector-Sicherungen"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = backup_dir / f"Identitaetsregister_vor_Update_{stamp}.sqlite3"
        with sqlite3.connect(self.path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        return target

    @staticmethod
    def _new_short_code(conn: sqlite3.Connection) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if not conn.execute(
                "SELECT 1 FROM identities WHERE short_code=? COLLATE NOCASE",
                (code,),
            ).fetchone():
                return code

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def active_school_year(self) -> str:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key='active_school_year'"
            ).fetchone()
            return str(row["value"]) if row else ""

    def set_active_school_year(self, school_year: str) -> None:
        value = school_year.strip()
        if not value:
            raise ValueError("Das Schuljahr darf nicht leer sein.")
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO meta(key,value) VALUES('active_school_year',?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (value,),
            )

    def import_students(self, school_year: str, rows: list[dict]) -> int:
        self.set_active_school_year(school_year)
        seen: set[tuple[str, str]] = set()
        normalized = []
        for raw in rows:
            class_id = str(raw["class_id"]).strip()
            student_key = str(raw.get("student_id") or raw.get("student_code") or "").strip()
            name = str(raw["name"]).strip()
            list_position = int(raw["list_position"])
            key = (class_id.casefold(), student_key.casefold())
            if not class_id or not student_key or not name or list_position < 1:
                raise ValueError("Klasse, Schüler-ID, Listenplatz und Name müssen ausgefüllt sein.")
            if key in seen:
                raise ValueError(f"Schüler-ID doppelt: {student_key}")
            seen.add(key)
            normalized.append((class_id, student_key, name, list_position))
        if not normalized:
            raise ValueError("Die Namensliste ist leer.")

        with self.connect() as conn:
            classes = {row[0] for row in normalized}
            for class_id in classes:
                conn.execute(
                    "UPDATE identities SET active=0 WHERE school_year=? AND class_id=?",
                    (school_year, class_id),
                )
            for class_id, student_key, name, list_position in normalized:
                existing = conn.execute(
                    """SELECT public_token,short_code FROM identities
                       WHERE school_year=? AND student_key=?""",
                    (school_year, student_key),
                ).fetchone()
                token = str(existing["public_token"]) if existing else secrets.token_urlsafe(24)
                short_code = (
                    str(existing["short_code"])
                    if existing
                    else self._new_short_code(conn)
                )
                conn.execute(
                    """INSERT INTO identities(
                         school_year,student_key,public_token,short_code,
                         name,class_id,list_position,active
                       ) VALUES(?,?,?,?,?,?,?,1)
                       ON CONFLICT(school_year,student_key) DO UPDATE SET
                         name=excluded.name,class_id=excluded.class_id,
                         list_position=excluded.list_position,active=1""",
                    (
                        school_year,
                        student_key,
                        token,
                        short_code,
                        name,
                        class_id,
                        list_position,
                    ),
                )
        return len(normalized)

    def classes(self) -> list[str]:
        year = self.active_school_year()
        with self.connect() as conn:
            return [
                str(row[0]) for row in conn.execute(
                    """SELECT DISTINCT class_id FROM identities
                       WHERE school_year=? AND active=1 ORDER BY class_id""",
                    (year,),
                )
            ]

    def class_summaries(self) -> list[dict]:
        year = self.active_school_year()
        with self.connect() as conn:
            return [
                dict(row) for row in conn.execute(
                    """SELECT class_id, COUNT(*) AS student_count
                       FROM identities
                       WHERE school_year=? AND active=1
                       GROUP BY class_id ORDER BY class_id""",
                    (year,),
                )
            ]

    def students(self, class_id: str) -> list[dict]:
        year = self.active_school_year()
        with self.connect() as conn:
            return [
                dict(row) for row in conn.execute(
                    """SELECT * FROM identities
                       WHERE school_year=? AND class_id=? AND active=1
                       ORDER BY list_position""",
                    (year, class_id),
                )
            ]
