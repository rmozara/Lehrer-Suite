from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
import threading
import webbrowser
from html import escape
from pathlib import Path
from urllib.parse import quote_plus, urlsplit

import qrcode
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from qr_generator import VERSION
from qr_generator.network_settings import (
    connection_label,
    detect_network_addresses,
    load_preferred_url,
    normalize_base_url,
    save_preferred_url,
)
from qr_generator.registry import Registry
from qr_generator.qr_output import generate_qr_cards_pdf
from qr_generator.roster_ods import Roster, read_generation_date, read_roster, write_generation_date


ROOT = Path(__file__).resolve().parent
REGISTRY_FILE = Path(
    os.environ.get(
        "COLLECTOR_IDENTITY_FILE",
        ROOT.parent / "Collector-Daten" / "identities.sqlite3",
    )
)
TEMPLATE_FILE = ROOT / "templates" / "IB_QR-Karten.odt"
WORK_DIR = Path(os.environ.get("QR_GENERATOR_WORKDIR", ROOT.parent / "QR-Ausgaben")).resolve()
ROSTER_FILE = WORK_DIR / "Namensliste.ods"
OUTPUT_DIR = WORK_DIR
SETTINGS_FILE = ROOT.parent / "Collector-Daten" / "generator_settings.json"
TEACHER_SETTINGS_FILE = ROOT.parent / "Collector-Daten" / "teacher_settings.json"
registry = Registry(REGISTRY_FILE)
app = FastAPI(docs_url=None, redoc_url=None)


def teacher_password_configured() -> bool:
    try:
        data = json.loads(TEACHER_SETTINGS_FILE.read_text(encoding="utf-8"))
        return bool(data.get("admin_password_hash"))
    except (OSError, ValueError, TypeError):
        return False


def save_teacher_password(password: str) -> None:
    if len(password) < 10:
        raise ValueError("Das Lehrerpasswort muss mindestens 10 Zeichen lang sein.")
    if len(password) > 128:
        raise ValueError("Das Lehrerpasswort darf höchstens 128 Zeichen lang sein.")
    TEACHER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEACHER_SETTINGS_FILE.write_text(
        json.dumps({"admin_user": "lehrkraft", "admin_password_hash": hashlib.sha256(password.encode("utf-8")).hexdigest()}, indent=2),
        encoding="utf-8",
    )


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><style>"
        ":root{--space-1:8px;--space-2:16px;--space-3:24px;--space-4:32px}"
        "body{font-family:Arial,sans-serif;background:#f4f7f4;color:#183126;margin:0}"
        "main{max-width:1000px;margin:auto;padding:var(--space-3)}.card{background:white;border:1px solid #ccd6cd;"
        "border-radius:10px;padding:var(--space-3);margin-bottom:var(--space-3)}input,select,button{padding:9px;margin:4px}"
        "button,.button{background:#487f0d;color:white;border:0;border-radius:6px;text-decoration:none;"
        "font-weight:bold;display:inline-block;padding:9px 13px}.notice{border-radius:7px;padding:12px;"
        "margin:0 0 16px}.success{background:#e5f4d9;color:#254c0b}.error{background:#fde1dc;color:#7a2014}"
        ".warning{background:#fff0ca;padding:12px}.muted{color:#506258;font-size:.95rem}"
        ".summary{margin-top:12px}.summary span{display:inline-block;background:#edf3ed;"
        "border-radius:5px;padding:7px 10px;margin:3px 6px 3px 0}"
        ".connection-row{display:grid;grid-template-columns:minmax(250px,1fr) minmax(260px,1fr);"
        "gap:18px;align-items:start}.info{background:#edf3ed;border-left:4px solid #809383;"
        "border-radius:5px;padding:10px;font-size:.92rem;line-height:1.35}"
        ".actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.actions form{margin-left:auto}"
        ".danger-button{background:#8b2f2f}"
        "@media(max-width:700px){.connection-row{grid-template-columns:1fr}}"
        "</style></head><body><main>" + body + "</main></body></html>"
    )


def qr_data(payload: str) -> str:
    output = io.BytesIO()
    qrcode.make(payload).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def current_roster() -> tuple[Roster | None, str]:
    try:
        return read_roster(ROSTER_FILE), ""
    except (OSError, ValueError) as exc:
        return None, str(exc)


def roster_loaded(roster: Roster) -> bool:
    if registry.active_school_year() != roster.school_year:
        return False
    registered = registry.students(roster.class_id)
    expected = {str(item["student_id"]) for item in roster.students}
    actual = {str(item["student_key"]) for item in registered}
    return expected == actual


@app.get("/", response_class=HTMLResponse)
def home(message: str = "", error: str = ""):
    roster, roster_error = current_roster()
    if roster:
        try:
            if not roster_loaded(roster):
                registry.import_students(roster.school_year, roster.students)
            loaded = True
        except (KeyError, TypeError, ValueError) as exc:
            roster_error = str(exc)
            roster = None
            loaded = False
    else:
        loaded = False
    year = registry.active_school_year()
    feedback = ""
    if message:
        feedback = f"<p class='notice success'>{escape(message)}</p>"
    elif error:
        feedback = f"<p class='notice error'>{escape(error)}</p>"
    if roster:
        generated_on = read_generation_date(ROSTER_FILE)
        roster_status = (
            "<p class='notice success'><strong>Namensliste automatisch geladen:</strong> "
            f"Klasse {escape(roster.class_id)} · {escape(roster.school_year)} · "
            f"{len(roster.students)} Personen</p>"
            + (f"<p class='muted'><strong>Karten zuletzt erzeugt:</strong> {escape(generated_on)}</p>" if generated_on else "<p class='muted'>Für diese Klasse wurden noch keine Karten erzeugt.</p>")
        )
    else:
        roster_status = (
            "<p class='notice error'><strong>Namensliste noch nicht bereit:</strong> "
            f"{escape(roster_error)}</p>"
        )

    preferred_url = load_preferred_url(SETTINGS_FILE)
    preferred_ip = urlsplit(preferred_url).hostname if preferred_url else None
    addresses = detect_network_addresses(8765, preferred_ip)
    address_options = "".join(
        f"<option value='{escape(item.url)}'{' selected' if item.recommended else ''}>"
        f"{'Empfohlen · ' if item.recommended else ''}{escape(item.ip)} "
        f"({escape(connection_label(item.interface))})"
        "</option>"
        for item in addresses
    )
    if addresses:
        connection = (
            "<div class='connection-row'><div>"
            "<label for='direct_base_url'><strong>IP-Adresse des Laptops</strong></label><br>"
            "<select required id='direct_base_url' name='direct_base_url'>"
            f"{address_options}</select>"
            "<p class='muted'>Automatisch erkannt. Normalerweise die empfohlene Auswahl lassen.</p>"
            "</div><aside class='info'><strong>Was steht im QR?</strong><br>"
            "Die persönliche Kennung und diese IP-Adresse. So findet das Schülergerät "
            "den Collector auf diesem Laptop.</aside></div>"
        )
        cards_disabled = ""
    else:
        connection = (
            "<p class='warning'>Noch keine Unterrichtsverbindung erkannt. "
            "Bitte den Laptop mit WLAN oder Hotspot verbinden und diese Seite neu laden.</p>"
        )
        cards_disabled = " disabled"
    return page(
        "QR-Generator",
        f"<header class='card'><p class='muted'>QR</p><h1>QR-Karten</h1>"
        f"<p>Version {VERSION}</p></header>"
        f"<p>Aktives Schuljahr: <strong>{escape(year or 'noch nicht festgelegt')}</strong></p>"
        f"{feedback}"
        "<section class='card'><h2>1. Namensliste</h2>"
        "<p>Verwendete Datei:</p>"
        f"<p><code>{escape(str(ROSTER_FILE))}</code></p>"
        f"{roster_status}</section>"
        "<section class='card'><h2>2. Karten erzeugen</h2>"
        "<form method='get' action='/cards.pdf'>"
        f"<input type='hidden' name='class_id' value='{escape(roster.class_id if roster else '')}'>"
        f"{connection}"
        f"<button{cards_disabled if loaded and teacher_password_configured() else ' disabled'}>Karten erzeugen</button></form>"
        + ("" if teacher_password_configured() else "<p class='warning'>Bitte zuerst unten das gemeinsame Lehrerpasswort festlegen.</p>")
        + "</section>"
        + "<section class='card'><h2>3. Lehrerpasswort</h2>"
        + "<p><strong>Benutzername: <code>lehrkraft</code></strong></p>"
        + ("<p class='notice success'>Ein gemeinsames Lehrerpasswort für alle Collectoren ist eingerichtet.</p>" if teacher_password_configured() else "<p class='warning'>Noch kein gemeinsames Lehrerpasswort eingerichtet.</p>")
        + "<p class='muted'>Benutzername und Passwort gelten gemeinsam für SE- und HB-Collector. Das Passwort wird nicht lesbar gespeichert und kann hier jederzeit neu gesetzt werden.</p>"
        + "<form method='post' action='/teacher-password'><label>Neues Lehrerpasswort<br><input type='password' name='password' minlength='10' required></label>"
        + "<label>Wiederholen<br><input type='password' name='repeat' minlength='10' required></label><button>Passwort speichern</button></form></section>"
        + "<section class='card'><div class='actions'><form method='post' action='/shutdown'><button class='danger-button'>QR beenden</button></form></div></section>",
    )


@app.post("/teacher-password")
def teacher_password(password: str = Form(...), repeat: str = Form(...)):
    if password != repeat:
        return RedirectResponse("/?error=Die+beiden+Passwörter+stimmen+nicht+überein.", status_code=303)
    try:
        save_teacher_password(password)
    except ValueError as exc:
        return RedirectResponse(f"/?error={quote_plus(str(exc))}", status_code=303)
    return RedirectResponse("/?message=Das+Lehrerpasswort+wurde+gespeichert+und+gilt+für+alle+Collectoren.", status_code=303)


@app.get("/cards", response_class=HTMLResponse)
def cards(class_id: str, direct_base_url: str):
    if not teacher_password_configured():
        return page(
            "Lehrerpasswort einrichten",
            "<div class='warning'><h1>Zuerst Lehrerpasswort einrichten</h1>"
            "<p>Zurück zur Übersicht gehen und für den Benutzer <strong>lehrkraft</strong> "
            "ein eigenes Passwort festlegen.</p></div><p><a class='button' href='/'>Zur Übersicht</a></p>",
        )
    students = registry.students(class_id)
    if not students:
        return page("Keine Karten", "<p class='warning'>Für diese Klasse wurden keine Personen gefunden.</p>")
    cards_html = []
    base = direct_base_url.strip().rstrip("/")
    for student in students:
        payload = f"{base}/p/{student['public_token']}"
        cards_html.append(
            "<section class='qr-card'>"
            f"<h1>{escape(student['name'])}</h1>"
            f"<p>Klasse {escape(student['class_id'])} · Schüler-ID {escape(student['student_key'])}</p>"
            f"<p><strong>Persönlicher Code: {escape(student['short_code'])}</strong></p>"
            f"<img src='data:image/png;base64,{qr_data(payload)}' alt='Persönlicher QR-Code'>"
            "<p>Persönliche Collector-Karte</p></section>"
        )
    return HTMLResponse(
        "<!doctype html><html lang='de'><head><meta charset='utf-8'><style>"
        "@page{size:A5 landscape;margin:18mm 14mm 12mm 18mm}"
        "body{font-family:Arial,sans-serif;margin:0}.qr-card{break-after:page;page-break-after:always;"
        "height:105mm;text-align:center;box-sizing:border-box;padding-top:5mm}"
        ".qr-card:last-child{break-after:auto}.qr-card img{width:62mm;height:62mm}"
        "h1{margin:0 0 3mm}p{margin:2mm}</style></head><body>"
        + "".join(cards_html) + "</body></html>"
    )


@app.get("/cards.pdf")
def cards_pdf(class_id: str, direct_base_url: str):
    if not teacher_password_configured():
        return page(
            "Lehrerpasswort einrichten",
            "<div class='warning'><h1>Zuerst Lehrerpasswort einrichten</h1>"
            "<p>Ohne abgeschlossene Ersteinrichtung werden keine QR-Karten erzeugt.</p></div>"
            "<p><a class='button' href='/'>Zur Übersicht</a></p>",
        )
    roster, roster_error = current_roster()
    if roster is None:
        return page("Namensliste fehlt", f"<p class='notice error'>{escape(roster_error)}</p>")
    if class_id != roster.class_id:
        return page("Falsche Klasse", "<p class='notice error'>Die ausgewählte Klasse gehört nicht zu dieser Namensliste.</p>")
    direct_base_url = save_preferred_url(
        SETTINGS_FILE,
        normalize_base_url(direct_base_url),
    )
    raw_students = registry.students(class_id)
    students = [
        {
            "class_id": row["class_id"],
            "student_id": row["student_key"],
            "name": row["name"],
            "public_token": row["public_token"],
            "short_code": row["short_code"],
            "list_position": row["list_position"],
            "school_year": roster.school_year,
        }
        for row in raw_students
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_class = "".join(character for character in class_id if character.isalnum() or character in "-_")
    safe_year = "".join(character for character in roster.school_year.replace("/", "-") if character.isalnum() or character in "-_")
    output = OUTPUT_DIR / f"QR-Karten_{safe_class}_{safe_year}.pdf"
    generate_qr_cards_pdf(
        students,
        roster.subject,
        direct_base_url,
        TEMPLATE_FILE,
        output,
        roster.teacher_abbreviation,
        roster.school_name,
    )
    write_generation_date(ROSTER_FILE)
    return page(
        "QR-Karten erzeugt",
        "<h1>QR-Karten fertig</h1>"
        f"<p class='notice success'>{len(students)} Karten wurden erzeugt.</p>"
        f"<div class='card'><p><strong>Gespeichert als:</strong><br>"
        f"<code>{escape(str(output))}</code></p>"
        "<div class='actions'>"
        f"<a class='button' href='/output/{quote_plus(output.name)}' target='_blank'>PDF öffnen</a>"
        "<a class='button' href='/'>Zur Übersicht</a>"
        "<form method='post' action='/switch-class'><button>Weitere Klasse auswählen</button></form>"
        "<form method='post' action='/shutdown'>"
        "<button class='danger-button'>QR beenden</button></form>"
        "</div></div>",
    )


@app.get("/output/{filename}")
def output_file(filename: str):
    safe_name = Path(filename).name
    output = OUTPUT_DIR / safe_name
    if not output.is_file() or not safe_name.startswith("QR-Karten_") or output.suffix != ".pdf":
        return page("Datei nicht gefunden", "<p class='notice error'>Die PDF-Datei wurde nicht gefunden.</p>")
    return FileResponse(output, media_type="application/pdf", filename=output.name)


@app.post("/shutdown", response_class=HTMLResponse)
def shutdown():
    server = getattr(app.state, "server", None)
    if server is not None:
        threading.Timer(0.5, lambda: setattr(server, "should_exit", True)).start()
    return page(
        "QR beendet",
        "<section class='card' style='max-width:560px;margin:32px auto;text-align:center'>"
        "<div style='font-size:2rem'>✓</div><h1>QR beendet</h1>"
        "<p>Das Programm wurde geschlossen. Dieses Browserfenster kann jetzt geschlossen werden.</p></section>",
    )


@app.post("/switch-class", response_class=HTMLResponse)
def switch_class():
    app.state.switch_class_requested = True
    server = getattr(app.state, "server", None)
    if server is not None:
        threading.Timer(0.5, lambda: setattr(server, "should_exit", True)).start()
    return page(
        "Weitere Klasse auswählen",
        "<h1>Weitere Klasse auswählen</h1>"
        "<p class='notice success'>Der Ordnerdialog wird geöffnet. Dort den persönlichen Arbeitsordner der nächsten Klasse auswählen, in dem <strong>Namensliste.ods</strong> liegt.</p>"
        "<p>Nach der Auswahl erscheint die nächste Klasse automatisch hier.</p>"
        "<script>setTimeout(function retry(){fetch('/').then(function(r){if(r.ok){location.href='/'}}).catch(function(){setTimeout(retry,500)})},1200)</script>",
    )


if __name__ == "__main__":
    teacher_url = "http://127.0.0.1:8764"
    print("\nQR-GENERATOR")
    print(f"Arbeitsordner: {WORK_DIR}")
    print(f"Namensliste:   {ROSTER_FILE}")
    print("Benutzername: lehrkraft")
    print("Lehrerpasswort: im Browser festlegen" if not teacher_password_configured() else "Lehrerpasswort: gemeinsames Passwort ist eingerichtet")
    print("Die Lehreroberfläche wird jetzt im Browser geöffnet.")
    print(f"Falls kein Browserfenster erscheint, bitte diesen Link öffnen: {teacher_url}\n")
    if not os.environ.get("QR_GENERATOR_SWITCHED"):
        threading.Timer(1.2, lambda: webbrowser.open(teacher_url)).start()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8764, access_log=False))
    app.state.switch_class_requested = False
    app.state.server = server
    server.run()
    if app.state.switch_class_requested:
        sys.exit(23)
