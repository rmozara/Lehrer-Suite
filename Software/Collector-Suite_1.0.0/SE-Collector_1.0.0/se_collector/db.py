from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .identity_registry import IdentityRegistry


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    name TEXT NOT NULL,
    list_position INTEGER NOT NULL,
    public_token TEXT NOT NULL UNIQUE,
    short_code TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    archived INTEGER NOT NULL DEFAULT 0,
    UNIQUE(class_id, student_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_students_active_position
ON students(class_id, list_position) WHERE active=1;

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_token TEXT NOT NULL UNIQUE,
    workspace_id TEXT NOT NULL,
    class_id TEXT NOT NULL,
    form_id TEXT NOT NULL,
    form_version TEXT NOT NULL,
    period_id TEXT NOT NULL,
    session_code TEXT NOT NULL,
    started_at TEXT NOT NULL,
    closed_at TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(workspace_id, class_id, form_id, period_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_one_active_session_per_class
ON sessions(class_id) WHERE active=1;

CREATE TABLE IF NOT EXISTS session_roster (
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_db_id INTEGER NOT NULL REFERENCES students(id),
    list_position INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY(session_id, student_db_id)
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_db_id INTEGER NOT NULL REFERENCES students(id),
    submitted_at TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    total_points INTEGER NOT NULL,
    grade_label TEXT NOT NULL,
    grade_value REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'valid',
    replaced_by INTEGER REFERENCES submissions(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_valid_submission
ON submissions(session_id, student_db_id) WHERE status='valid';
CREATE INDEX IF NOT EXISTS idx_sessions_recent ON sessions(started_at DESC);
"""


@dataclass(frozen=True)
class ImportResult:
    imported: int
    classes: tuple[str, ...]
    deactivated: int


class Database:
    def __init__(
        self,
        path: Path,
        workspace_id: str = "default",
        identity_file: Path | None = None,
        migration_backup_dir: Path | None = None,
    ):
        self.path = Path(path)
        self.workspace_id = str(workspace_id)
        self.last_migration_backup: Path | None = None
        self.identities = IdentityRegistry(
            identity_file or self.path.parent / "collector_identities.sqlite3",
            strict=identity_file is not None,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self._requires_migration():
            self.last_migration_backup = self._backup_before_migration(
                migration_backup_dir or self.path.parent / "Sicherungen"
            )
        self.init_schema()

    def _requires_migration(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return False
        with sqlite3.connect(self.path) as conn:
            has_sessions = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchone()
            if not has_sessions:
                return False
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(sessions)")
            }
        return "workspace_id" not in columns

    def _backup_before_migration(self, backup_dir: Path) -> Path:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = backup_dir / f"SE-Datenbank_vor_Update_{stamp}.sqlite3"
        with sqlite3.connect(self.path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        return target

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "workspace_id" not in columns:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'default'"
                )
                conn.execute(
                    "UPDATE sessions SET workspace_id=? WHERE workspace_id='default'",
                    (self.workspace_id,),
                )
            if "archived" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
            conn.execute("PRAGMA user_version = 3")

    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(24)

    @staticmethod
    def _new_short_code() -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(secrets.choice(alphabet) for _ in range(8))

    @staticmethod
    def _new_session_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _normalize_rows(rows: Iterable[dict]) -> list[dict]:
        normalized: list[dict] = []
        for line_no, raw in enumerate(rows, start=2):
            try:
                class_id = str(raw["class_id"]).strip()
                student_id = str(raw["student_id"]).strip()
                name = str(raw["name"]).strip()
                list_position = int(str(raw["list_position"]).strip())
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "Die Namensliste muss class_id, student_id, name und list_position liefern; "
                    f"Fehler in Zeile {line_no}."
                ) from exc
            if not class_id or not student_id or not name or list_position < 1:
                raise ValueError(f"Ungültige oder leere Angaben in Zeile {line_no}.")
            normalized.append(
                {
                    "class_id": class_id,
                    "student_id": student_id,
                    "name": name,
                    "list_position": list_position,
                }
            )
        if not normalized:
            raise ValueError("Die Namensliste enthält keine Schülerinnen oder Schüler.")

        ids: set[tuple[str, str]] = set()
        positions: set[tuple[str, int]] = set()
        for row in normalized:
            id_key = (row["class_id"].casefold(), row["student_id"].casefold())
            pos_key = (row["class_id"].casefold(), row["list_position"])
            if id_key in ids:
                raise ValueError(f"Schüler-ID doppelt in der Namensliste: {row['class_id']} / {row['student_id']}")
            if pos_key in positions:
                raise ValueError(f"Listenplatz doppelt in der Namensliste: {row['class_id']} / Nr. {row['list_position']}")
            ids.add(id_key)
            positions.add(pos_key)
        return normalized

    def import_students(self, rows: Iterable[dict]) -> ImportResult:
        normalized = self._normalize_rows(rows)
        by_class: dict[str, list[dict]] = {}
        for row in normalized:
            by_class.setdefault(row["class_id"], []).append(row)

        imported = 0
        with self.connect() as conn:
            # One Selbstevaluation.ods represents one current class roster.  Old
            # classes remain historically available through session_roster, but
            # are never shown as additional active classes after a new sync.
            before_active = conn.execute(
                "SELECT COUNT(*) FROM students WHERE active=1"
            ).fetchone()[0]
            conn.execute("UPDATE students SET active=0")

            for class_id, class_rows in by_class.items():
                for row in sorted(class_rows, key=lambda item: item["list_position"]):
                    existing = conn.execute(
                        "SELECT id,public_token FROM students WHERE class_id=? AND student_id=?",
                        (class_id, row["student_id"]),
                    ).fetchone()
                    token = self.identities.resolve(
                        row["student_id"],
                        name=row["name"],
                        class_id=class_id,
                        existing_token=str(existing["public_token"]) if existing else None,
                        source="SE-Collector",
                    )
                    if existing:
                        conn.execute(
                            """UPDATE students
                               SET name=?, list_position=?, public_token=?, active=1
                               WHERE id=?""",
                            (row["name"], row["list_position"], token, existing["id"]),
                        )
                    else:
                        while True:
                            try:
                                conn.execute(
                                    """
                                    INSERT INTO students(
                                        class_id, student_id, name, list_position,
                                        public_token, short_code, active
                                    ) VALUES(?,?,?,?,?,?,1)
                                    """,
                                    (
                                        class_id,
                                        row["student_id"],
                                        row["name"],
                                        row["list_position"],
                                        token,
                                        self._new_short_code(),
                                    ),
                                )
                                break
                            except sqlite3.IntegrityError:
                                continue
                    imported += 1

            deactivated = max(0, before_active - imported)

        return ImportResult(imported, tuple(sorted(by_class)), deactivated)


    def classes(self) -> list[str]:
        with self.connect() as conn:
            return [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT class_id FROM students WHERE active=1 ORDER BY class_id COLLATE NOCASE"
                )
            ]

    def students_for_class(self, class_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM students
                WHERE class_id=? AND active=1
                ORDER BY list_position, name COLLATE NOCASE
                """,
                (class_id,),
            ).fetchall()

    def student_by_token(self, token: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM students WHERE public_token=? AND active=1", (token,)
            ).fetchone()

    def student_by_short_code(self, code: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM students WHERE upper(short_code)=upper(?) AND active=1",
                (code.strip(),),
            ).fetchone()

    @staticmethod
    def _refresh_roster(conn: sqlite3.Connection, session_id: int, class_id: str) -> None:
        conn.execute("DELETE FROM session_roster WHERE session_id=?", (session_id,))
        conn.execute(
            """
            INSERT INTO session_roster(session_id, student_db_id, list_position, student_id, name)
            SELECT ?, id, list_position, student_id, name
            FROM students
            WHERE class_id=? AND active=1
            ORDER BY list_position
            """,
            (session_id, class_id),
        )

    def start_or_resume_session(
        self, class_id: str, form_id: str, form_version: str, period_id: str
    ) -> tuple[sqlite3.Row, bool]:
        class_id = class_id.strip()
        period_id = period_id.strip()
        if not period_id:
            raise ValueError("Der Erhebungszeitraum darf nicht leer sein.")
        with self.connect() as conn:
            student_count = conn.execute(
                "SELECT COUNT(*) FROM students WHERE class_id=? AND active=1", (class_id,)
            ).fetchone()[0]
            if student_count == 0:
                raise ValueError(f"Für die Klasse {class_id} ist keine aktive Schülerliste vorhanden.")

            now = local_now()
            conn.execute(
                "UPDATE sessions SET active=0, closed_at=? WHERE class_id=? AND active=1",
                (now, class_id),
            )
            existing = conn.execute(
                """
                SELECT * FROM sessions
                WHERE workspace_id=? AND class_id=? AND form_id=? AND period_id=?
                """,
                (self.workspace_id, class_id, form_id, period_id),
            ).fetchone()

            created = existing is None
            if existing:
                session_id = existing["id"]
                valid_count = conn.execute(
                    "SELECT COUNT(*) FROM submissions WHERE session_id=? AND status='valid'",
                    (session_id,),
                ).fetchone()[0]
                if valid_count == 0:
                    self._refresh_roster(conn, session_id, class_id)
                conn.execute(
                    """
                    UPDATE sessions
                    SET form_version=?, session_code=?, started_at=?, closed_at=NULL, active=1, archived=0
                    WHERE id=?
                    """,
                    (form_version, self._new_session_code(), now, session_id),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO sessions(
                        public_token, workspace_id, class_id, form_id, form_version, period_id,
                        session_code, started_at, active
                    ) VALUES(?,?,?,?,?,?,?,?,1)
                    """,
                    (
                        self._new_token(), self.workspace_id, class_id, form_id, form_version,
                        period_id, self._new_session_code(), now,
                    ),
                )
                session_id = cur.lastrowid
                self._refresh_roster(conn, session_id, class_id)

            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            return row, created

    def session_by_id(self, session_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE id=? AND workspace_id=?",
                (session_id, self.workspace_id),
            ).fetchone()

    def session_by_public_token(self, token: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE public_token=? AND workspace_id=?",
                (token, self.workspace_id),
            ).fetchone()

    def active_session_by_code(self, session_code: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM sessions WHERE session_code=? AND active=1 AND archived=0 AND workspace_id=?",
                (session_code.strip(), self.workspace_id),
            ).fetchone()

    def active_session_for_student(self, student_db_id: int, session_code: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT s.*
                FROM sessions s
                JOIN session_roster r ON r.session_id=s.id
                WHERE r.student_db_id=? AND s.active=1 AND s.session_code=?
                  AND s.workspace_id=?
                ORDER BY s.started_at DESC
                LIMIT 1
                """,
                (student_db_id, session_code.strip(), self.workspace_id),
            ).fetchone()

    def close_session(self, session_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET active=0, closed_at=? WHERE id=?",
                (local_now(), session_id),
            )

    def reopen_session(self, session_id: int) -> sqlite3.Row:
        """Reopen a closed session without deleting its submissions."""
        with self.connect() as conn:
            session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not session:
                raise ValueError("Sitzung nicht gefunden.")
            now = local_now()
            conn.execute(
                "UPDATE sessions SET active=0, closed_at=? WHERE class_id=? AND id<>? AND active=1",
                (now, session["class_id"], session_id),
            )
            conn.execute(
                "UPDATE sessions SET session_code=?, started_at=?, closed_at=NULL, active=1 WHERE id=?",
                (self._new_session_code(), now, session_id),
            )
            return conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()

    def reset_session(self, session_id: int) -> sqlite3.Row:
        with self.connect() as conn:
            session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not session:
                raise ValueError("Sitzung nicht gefunden.")
            conn.execute("DELETE FROM submissions WHERE session_id=?", (session_id,))
            self._refresh_roster(conn, session_id, session["class_id"])
            now = local_now()
            conn.execute(
                "UPDATE sessions SET active=0, closed_at=? WHERE class_id=? AND id<>? AND active=1",
                (now, session["class_id"], session_id),
            )
            conn.execute(
                "UPDATE sessions SET session_code=?, started_at=?, closed_at=NULL, active=1 WHERE id=?",
                (self._new_session_code(), now, session_id),
            )
            return conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()

    def delete_session(self, session_id: int) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT archived FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not row or not row["archived"]:
                raise ValueError("Nur archivierte Sitzungen können endgültig gelöscht werden.")
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def archive_session(self, session_id: int) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT active FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not row or row["active"]:
                raise ValueError("Nur geschlossene Sitzungen können archiviert werden.")
            conn.execute("UPDATE sessions SET archived=1 WHERE id=?", (session_id,))

    def restore_session(self, session_id: int) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE sessions SET archived=0 WHERE id=? AND archived=1", (session_id,))


    def student_in_session(self, session_id: int, student_db_id: int) -> bool:
        with self.connect() as conn:
            return conn.execute(
                "SELECT 1 FROM session_roster WHERE session_id=? AND student_db_id=?",
                (session_id, student_db_id),
            ).fetchone() is not None

    def submission_for(self, session_id: int, student_db_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM submissions
                WHERE session_id=? AND student_db_id=? AND status='valid'
                ORDER BY id DESC LIMIT 1
                """,
                (session_id, student_db_id),
            ).fetchone()

    def save_submission(
        self,
        session_id: int,
        student_db_id: int,
        answers: dict[str, int],
        total_points: int,
        grade_label: str,
        grade_value: float,
    ) -> sqlite3.Row:
        with self.connect() as conn:
            session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not session or not session["active"]:
                raise ValueError("Diese Sitzung ist geschlossen.")
            in_roster = conn.execute(
                "SELECT 1 FROM session_roster WHERE session_id=? AND student_db_id=?",
                (session_id, student_db_id),
            ).fetchone()
            if not in_roster:
                raise ValueError("Diese persönliche QR-Karte gehört nicht zur geöffneten Sitzung.")
            if conn.execute(
                "SELECT 1 FROM submissions WHERE session_id=? AND student_db_id=? AND status='valid'",
                (session_id, student_db_id),
            ).fetchone():
                raise ValueError("Für diese Sitzung liegt bereits eine verbindliche Abgabe vor.")

            cur = conn.execute(
                """
                INSERT INTO submissions(
                    session_id, student_db_id, submitted_at, answers_json,
                    total_points, grade_label, grade_value, status
                ) VALUES(?,?,?,?,?,?,?,'valid')
                """,
                (
                    session_id, student_db_id, local_now(),
                    json.dumps(answers, ensure_ascii=False, sort_keys=True),
                    int(total_points), grade_label, float(grade_value),
                ),
            )
            new_id = cur.lastrowid
            old = conn.execute(
                """
                SELECT id FROM submissions
                WHERE session_id=? AND student_db_id=? AND status='reopened'
                ORDER BY id DESC LIMIT 1
                """,
                (session_id, student_db_id),
            ).fetchone()
            if old:
                conn.execute(
                    "UPDATE submissions SET status='replaced', replaced_by=? WHERE id=?",
                    (new_id, old["id"]),
                )
            return conn.execute("SELECT * FROM submissions WHERE id=?", (new_id,)).fetchone()

    def reopen_student(self, session_id: int, student_db_id: int) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM submissions
                WHERE session_id=? AND student_db_id=? AND status='valid'
                ORDER BY id DESC LIMIT 1
                """,
                (session_id, student_db_id),
            ).fetchone()
            if not row:
                return False
            conn.execute("UPDATE submissions SET status='reopened' WHERE id=?", (row["id"],))
            return True

    def session_progress(self, session_id: int) -> dict:
        with self.connect() as conn:
            session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not session:
                raise ValueError("Sitzung nicht gefunden.")
            total = conn.execute(
                "SELECT COUNT(*) FROM session_roster WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            submitted = conn.execute(
                "SELECT COUNT(*) FROM submissions WHERE session_id=? AND status='valid'",
                (session_id,),
            ).fetchone()[0]
            return {
                "session": session,
                "total": total,
                "submitted": submitted,
                "open": max(0, total - submitted),
            }

    def session_students_status(self, session_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT r.student_db_id AS id, r.list_position, r.student_id, r.name,
                       s.submitted_at, s.total_points, s.grade_label, s.grade_value
                FROM session_roster r
                LEFT JOIN submissions s
                  ON s.session_id=r.session_id
                 AND s.student_db_id=r.student_db_id
                 AND s.status='valid'
                WHERE r.session_id=?
                ORDER BY r.list_position, r.name COLLATE NOCASE
                """,
                (session_id,),
            ).fetchall()

    def recent_sessions(self, *, archived: bool = False) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.*,
                       (SELECT COUNT(*) FROM session_roster r WHERE r.session_id=s.id) AS total,
                       (SELECT COUNT(*) FROM submissions x WHERE x.session_id=s.id AND x.status='valid') AS submitted
                FROM sessions s
                WHERE s.workspace_id=? AND s.archived=?
                ORDER BY s.active DESC, s.started_at DESC
                """,
                (self.workspace_id, int(archived)),
            ).fetchall()
            return [dict(row) for row in rows]

    def raw_export_rows(self, session_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT se.class_id, r.list_position, r.student_id, r.name,
                       se.form_id, se.form_version, se.period_id,
                       sub.submitted_at, sub.answers_json, sub.total_points,
                       sub.grade_label, sub.grade_value
                FROM session_roster r
                JOIN sessions se ON se.id=r.session_id
                JOIN submissions sub
                  ON sub.session_id=r.session_id
                 AND sub.student_db_id=r.student_db_id
                 AND sub.status='valid'
                WHERE r.session_id=?
                ORDER BY r.list_position
                """,
                (session_id,),
            ).fetchall()
        result: list[dict] = []
        for row in rows:
            item = dict(row)
            answers = json.loads(item.pop("answers_json"))
            item.update(answers)
            result.append(item)
        return result

    def summary_export_rows(self, session_id: int, section_ids: list[str]) -> list[dict]:
        rows = self.session_students_status(session_id)
        session = self.session_by_id(session_id)
        if not session:
            return []
        raw_by_student = {
            row["student_id"]: row for row in self.raw_export_rows(session_id)
        }
        result: list[dict] = []
        for row in rows:
            raw = raw_by_student.get(row["student_id"])
            item = {
                "Nr.": row["list_position"],
                "Name": row["name"],
                "Schüler-ID": row["student_id"],
                "Zeitraum": session["period_id"],
            }
            if raw:
                answers = {key: int(value) for key, value in raw.items() if key.startswith("q")}
                item.update({"answers": answers, "raw": raw})
            else:
                item.update({"answers": None, "raw": None})
            result.append(item)
        return result
