from __future__ import annotations

import ipaddress
import json
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


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


def connection_label(interface: str) -> str:
    rank = _interface_rank(interface)[0]
    if rank == 0:
        return "WLAN"
    if rank == 1:
        return "Netzwerkkabel"
    return "Lokales Netzwerk"


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


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Keine gültige Collector-Verbindung ausgewählt.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Die Collector-Verbindung ist ungültig.")
    if parsed.path not in {"", "/"}:
        raise ValueError("Die Collector-Verbindung darf keinen zusätzlichen Pfad enthalten.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Der Port der Collector-Verbindung ist ungültig.") from exc
    return value


def load_preferred_url(settings_file: Path) -> str:
    try:
        raw = json.loads(settings_file.read_text(encoding="utf-8"))
        return normalize_base_url(str(raw.get("direct_base_url", "")))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return ""


def save_preferred_url(settings_file: Path, value: str) -> str:
    normalized = normalize_base_url(value)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        json.dumps({"direct_base_url": normalized}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return normalized
