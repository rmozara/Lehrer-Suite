from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from . import VERSION


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_FILE = DATA_DIR / "hefter_collector.sqlite3"
SHARED_IDENTITY_FILE = Path(
    os.environ.get(
        "COLLECTOR_IDENTITY_FILE",
        ROOT.parent / "Collector-Daten" / "identities.sqlite3",
    )
).expanduser().resolve()
SHARED_TEACHER_SETTINGS_FILE = ROOT.parent / "Collector-Daten" / "teacher_settings.json"
GENERATOR_SETTINGS_FILE = ROOT.parent / "Collector-Daten" / "generator_settings.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
CRITERIA_FILE = ROOT / "config" / "criteria.json"
WORK_DIR = Path(os.environ.get("HB_COLLECTOR_WORKDIR", ROOT)).expanduser().resolve()
WORKSPACE_MARKER = WORK_DIR / ".hb-collector-workspace"
WORKSPACE_ID = hashlib.sha256(str(WORK_DIR).encode("utf-8")).hexdigest()


def ensure_workspace() -> bool:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    created = not WORKSPACE_MARKER.exists()
    if created:
        WORKSPACE_MARKER.write_text(
            json.dumps(
                {"workspace_id": WORKSPACE_ID, "path": str(WORK_DIR)},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    workbook = WORK_DIR / "Hefterbewertung.ods"
    template = ROOT / "templates" / "Hefterbewertung.ods"
    if not workbook.exists() and template.exists():
        shutil.copy2(template, workbook)
    return created


def hash_password(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Settings:
    admin_user: str
    admin_password_hash: str
    host: str
    port: int
    direct_base_url: str = ""

    @property
    def direct_mode_enabled(self) -> bool:
        return bool(self.direct_base_url)


@dataclass(frozen=True)
class DetectedAddress:
    interface: str
    ip: str
    url: str
    recommended: bool


def _is_usable_ipv4(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        ip.version == 4
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_unspecified
    )


def detect_lan_ip() -> str:
    candidates: list[str] = []
    for target in (("192.0.2.1", 9), ("10.255.255.255", 9)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(target)
            candidates.append(sock.getsockname()[0])
        except OSError:
            pass
        finally:
            sock.close()
    try:
        candidates.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    private = [
        value for value in candidates
        if _is_usable_ipv4(value) and ipaddress.ip_address(value).is_private
    ]
    return private[0] if private else "127.0.0.1"


def _interface_rank(name: str) -> tuple[int, str]:
    value = name.casefold()
    if value.startswith(("wl", "wifi", "wlan")):
        return 0, value
    if value.startswith(("en", "eth")):
        return 1, value
    if value.startswith(("docker", "br-", "virbr", "veth", "tun", "tap")):
        return 9, value
    return 5, value


def detect_network_addresses(port: int, preferred_ip: str | None = None) -> list[DetectedAddress]:
    found: list[tuple[str, str]] = []
    try:
        import psutil  # type: ignore

        stats = psutil.net_if_stats()
        for interface, addresses in psutil.net_if_addrs().items():
            if interface in stats and not stats[interface].isup:
                continue
            for address in addresses:
                if address.family == socket.AF_INET and _is_usable_ipv4(address.address):
                    found.append((interface, address.address))
    except Exception:
        pass
    if not found:
        ip = detect_lan_ip()
        if _is_usable_ipv4(ip):
            found.append(("Netzwerk", ip))

    unique: dict[str, str] = {}
    for interface, ip in sorted(found, key=lambda item: _interface_rank(item[0])):
        unique.setdefault(ip, interface)
    items = [(interface, ip) for ip, interface in unique.items()]
    physical = [item for item in items if _interface_rank(item[0])[0] < 9]
    if physical:
        items = physical
    items.sort(key=lambda item: (_interface_rank(item[0]), item[1]))
    route_ip = detect_lan_ip()
    if preferred_ip and any(ip == preferred_ip for _, ip in items):
        recommended_ip = preferred_ip
    elif any(ip == route_ip for _, ip in items):
        recommended_ip = route_ip
    else:
        recommended_ip = items[0][1] if items else ""
    return [
        DetectedAddress(interface, ip, f"http://{ip}:{port}", ip == recommended_ip)
        for interface, ip in items
    ]


def normalize_base_url(value: str, *, allow_blank: bool = False) -> str:
    value = value.strip().rstrip("/")
    if not value:
        if allow_blank:
            return ""
        raise ValueError("Die Adresse darf nicht leer sein.")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Die Adresse muss mit http:// oder https:// beginnen.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Die Adresse darf keine Zugangsdaten, Abfrage oder Sprungmarke enthalten.")
    if parsed.path not in {"", "/"}:
        raise ValueError("Bitte nur die Grundadresse ohne zusätzlichen Pfad eintragen.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Der Port der Adresse ist ungültig.") from exc
    return value


def ensure_settings() -> tuple[Settings, str | None]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(
            json.dumps(
                {
                    "admin_user": "lehrkraft",
                    "admin_password_hash": "",
                    "host": "0.0.0.0",
                    "port": 8765,
                    "direct_base_url": "",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    changed = False
    if not str(raw.get("direct_base_url", "")).strip():
        try:
            generator_data = json.loads(GENERATOR_SETTINGS_FILE.read_text(encoding="utf-8"))
            generator_url = normalize_base_url(
                str(generator_data.get("direct_base_url", "")),
                allow_blank=True,
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            generator_url = ""
        if generator_url:
            raw["direct_base_url"] = generator_url
            changed = True
    try:
        shared = json.loads(SHARED_TEACHER_SETTINGS_FILE.read_text(encoding="utf-8"))
        shared_hash = str(shared.get("admin_password_hash", ""))
    except (OSError, ValueError, TypeError):
        shared_hash = ""
    if shared_hash:
        if raw.get("admin_password_hash") != shared_hash:
            raw["admin_password_hash"] = shared_hash
            changed = True
    else:
        # Das gemeinsame Passwort wird ausschließlich im QR-Teil bewusst
        # eingerichtet; HB erzeugt niemals ein verborgenes Ersatzpasswort.
        if raw.get("admin_password_hash"):
            raw["admin_password_hash"] = ""
            changed = True
    if int(raw.get("port", 8765)) == 8766:
        raw["port"] = 8765
        direct = str(raw.get("direct_base_url", ""))
        if direct.endswith(":8766"):
            raw["direct_base_url"] = direct[:-5] + ":8765"
        changed = True
    if changed:
        SETTINGS_FILE.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return (
        Settings(
            admin_user=str(raw["admin_user"]),
            admin_password_hash=str(raw["admin_password_hash"]),
            host=str(raw.get("host", "0.0.0.0")),
            port=int(raw.get("port", 8765)),
            direct_base_url=normalize_base_url(
                str(raw.get("direct_base_url", "")),
                allow_blank=True,
            ),
        ),
        None,
    )


def _settings_data() -> dict:
    ensure_settings()
    return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))


def save_direct_base_url(value: str) -> Settings:
    normalized = normalize_base_url(value, allow_blank=True)
    data = _settings_data()
    data["direct_base_url"] = normalized
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ensure_settings()[0]


def save_admin_password(value: str) -> Settings:
    if len(value) < 10:
        raise ValueError("Das neue Passwort muss mindestens 10 Zeichen lang sein.")
    if len(value) > 128:
        raise ValueError("Das neue Passwort darf höchstens 128 Zeichen lang sein.")
    data = _settings_data()
    data["admin_password_hash"] = hash_password(value)
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    SHARED_TEACHER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SHARED_TEACHER_SETTINGS_FILE.write_text(
        json.dumps({"admin_user": "lehrkraft", "admin_password_hash": data["admin_password_hash"]}, indent=2),
        encoding="utf-8",
    )
    return ensure_settings()[0]


def load_criteria() -> dict:
    data = json.loads(CRITERIA_FILE.read_text(encoding="utf-8"))
    ids = [str(item["id"]) for item in data["criteria"]]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("Die Kriterien-IDs müssen eindeutig und nicht leer sein.")
    return data
