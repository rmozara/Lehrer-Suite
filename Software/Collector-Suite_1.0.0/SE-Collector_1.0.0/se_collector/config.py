from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
SETTINGS_FILE = DATA_DIR / "settings.json"
DB_FILE = DATA_DIR / "se_collector.sqlite3"
SHARED_IDENTITY_FILE = Path(
    os.environ.get(
        "COLLECTOR_IDENTITY_FILE",
        ROOT.parent / "Collector-Daten" / "identities.sqlite3",
    )
).expanduser().resolve()
SHARED_TEACHER_SETTINGS_FILE = ROOT.parent / "Collector-Daten" / "teacher_settings.json"
GENERATOR_SETTINGS_FILE = ROOT.parent / "Collector-Daten" / "generator_settings.json"
WORK_DIR = Path(
    os.environ.get("SE_COLLECTOR_WORKDIR", ROOT / "Arbeitsordner")
).expanduser().resolve()
WORKSPACE_ID = hashlib.sha256(str(WORK_DIR).encode("utf-8")).hexdigest()[:20]
ODS_TEMPLATE_FILE = ROOT / "templates" / "Selbstevaluation.ods"
ODS_FILE = WORK_DIR / "Selbstevaluation.ods"
BACKUP_DIR = WORK_DIR / "SE-Collector-Sicherungen"
OUTPUT_DIR = WORK_DIR
SE1_TEMPLATE_FILE = ROOT / "templates" / "IB_Selbstbewertung1.odt"
VERSION = "1.0.0"


def ensure_workspace() -> bool:
    """Prepare one lesson folder without copying the application into it.

    Returns True when a fresh, empty ODS was created.
    """
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    if ODS_FILE.exists():
        return False
    shutil.copy2(ODS_TEMPLATE_FILE, ODS_FILE)
    return True


@dataclass(frozen=True)
class Settings:
    admin_user: str
    admin_password_hash: str
    base_url: str
    base_url_mode: str
    direct_base_url: str
    wifi_ssid: str
    wifi_password: str
    host: str
    port: int

    @property
    def direct_mode_enabled(self) -> bool:
        return bool(self.direct_base_url)



@dataclass(frozen=True)
class DetectedAddress:
    interface: str
    ip: str
    url: str
    recommended: bool = False


def _interface_rank(name: str) -> tuple[int, str]:
    lower = name.lower()
    if any(part in lower for part in ("wlan", "wifi", "wi-fi", "wireless")) or lower.startswith("wl"):
        return (0, lower)
    if lower.startswith(("eth", "en")) or "ethernet" in lower or "lan" in lower:
        return (1, lower)
    if any(part in lower for part in ("hotspot", "access", "ap")):
        return (0, lower)
    if any(part in lower for part in ("docker", "veth", "virbr", "vmnet", "virtualbox", "loopback")) or lower.startswith(("br-", "tun", "tap")):
        return (9, lower)
    return (3, lower)


def detect_network_addresses(port: int, preferred_ip: str | None = None) -> list[DetectedAddress]:
    """Return selectable local IPv4 addresses, preferring WLAN/Ethernet.

    psutil is used when available because it works on Linux and Windows and
    exposes interface names. A socket-based fallback keeps the app usable if
    the optional dependency cannot be imported. Obvious virtual interfaces are
    hidden when at least one physical-looking address is available.
    """
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

    # Deduplicate while preserving the clearest interface label.
    unique: dict[str, str] = {}
    for interface, ip in sorted(found, key=lambda item: _interface_rank(item[0])):
        unique.setdefault(ip, interface)

    items = [(interface, ip) for ip, interface in unique.items()]
    physical = [item for item in items if _interface_rank(item[0])[0] < 9]
    if physical:
        items = physical

    items.sort(key=lambda item: (_interface_rank(item[0]), item[1]))
    if preferred_ip and any(ip == preferred_ip for _, ip in items):
        recommended_ip = preferred_ip
    else:
        route_ip = detect_lan_ip()
        recommended_ip = route_ip if any(ip == route_ip for _, ip in items) else (items[0][1] if items else "")

    return [
        DetectedAddress(
            interface=interface,
            ip=ip,
            url=f"http://{ip}:{port}",
            recommended=(ip == recommended_ip),
        )
        for interface, ip in items
    ]

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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
    """Best-effort detection of the laptop address reachable in the local WLAN."""
    candidates: list[str] = []
    for target in (("192.0.3.1", 9), ("10.255.255.255", 9)):
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

    usable = [value for value in candidates if _is_usable_ipv4(value)]
    private = [value for value in usable if ipaddress.ip_address(value).is_private]
    if private:
        return private[0]
    if usable:
        return usable[0]
    return "127.0.0.1"


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


def _default_settings() -> dict:
    return {
        "admin_user": "lehrkraft",
        "admin_password_hash": "",
        "base_url": "auto",
        "direct_base_url": "",
        "wifi_ssid": "SE-Lokal",
        "wifi_password": "Bitte-aendern-2026",
        "host": "0.0.0.0",
        "port": 8765,
    }


def _load_settings_data() -> tuple[dict, str | None]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        data = _default_settings()
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

    defaults = _default_settings()
    changed = False
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
            changed = True
    if not str(data.get("direct_base_url", "")).strip():
        try:
            generator_data = json.loads(GENERATOR_SETTINGS_FILE.read_text(encoding="utf-8"))
            generator_url = normalize_base_url(str(generator_data.get("direct_base_url", "")), allow_blank=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            generator_url = ""
        if generator_url:
            data["direct_base_url"] = generator_url
            changed = True
    if changed:
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        shared = json.loads(SHARED_TEACHER_SETTINGS_FILE.read_text(encoding="utf-8"))
        shared_hash = str(shared.get("admin_password_hash", ""))
    except (OSError, ValueError, TypeError):
        shared_hash = ""
    if shared_hash:
        if data.get("admin_password_hash") != shared_hash:
            data["admin_password_hash"] = shared_hash
            SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        # QR ist die einzige Komponente, die das gemeinsame Lehrerpasswort
        # einrichtet. Lokale Altwerte dürfen kein verborgenes Ersatzpasswort
        # für eine frische Installation bilden.
        if data.get("admin_password_hash"):
            data["admin_password_hash"] = ""
            SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data, None


def ensure_settings() -> tuple[Settings, str | None]:
    data, first_password = _load_settings_data()

    configured = str(os.environ.get("SE_BASE_URL", data.get("base_url", "auto"))).strip()
    port = int(data["port"])
    if not configured or configured.lower() == "auto":
        resolved = f"http://{detect_lan_ip()}:{port}"
        mode = "auto"
    else:
        resolved = normalize_base_url(configured)
        mode = "manual"

    direct = normalize_base_url(str(data.get("direct_base_url", "")), allow_blank=True)

    return (
        Settings(
            admin_user=str(data["admin_user"]),
            admin_password_hash=str(data["admin_password_hash"]),
            base_url=resolved,
            base_url_mode=mode,
            direct_base_url=direct,
            wifi_ssid=str(data["wifi_ssid"]),
            wifi_password=str(data["wifi_password"]),
            host=str(data["host"]),
            port=port,
        ),
        first_password,
    )


def save_direct_base_url(value: str) -> Settings:
    normalized = normalize_base_url(value, allow_blank=True)
    data, _ = _load_settings_data()
    data["direct_base_url"] = normalized
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return ensure_settings()[0]


def save_admin_password(value: str) -> Settings:
    if len(value) < 10:
        raise ValueError("Das neue Passwort muss mindestens 10 Zeichen lang sein.")
    if len(value) > 128:
        raise ValueError("Das neue Passwort darf höchstens 128 Zeichen lang sein.")
    data, _ = _load_settings_data()
    data["admin_password_hash"] = hash_password(value)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    SHARED_TEACHER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SHARED_TEACHER_SETTINGS_FILE.write_text(
        json.dumps({"admin_user": "lehrkraft", "admin_password_hash": data["admin_password_hash"]}, indent=2),
        encoding="utf-8",
    )
    return ensure_settings()[0]


def load_form(form_id: str = "SE1") -> dict:
    path = CONFIG_DIR / f"{form_id.lower()}.json"
    if not path.exists():
        raise FileNotFoundError(f"Formularkonfiguration nicht gefunden: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
