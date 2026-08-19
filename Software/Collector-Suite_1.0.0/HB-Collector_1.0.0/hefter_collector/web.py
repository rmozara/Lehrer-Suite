from __future__ import annotations

import hmac
import json
import threading
from datetime import date, datetime
from html import escape
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import VERSION
from .config import (
    DB_FILE,
    ROOT,
    SHARED_IDENTITY_FILE,
    WORKSPACE_ID,
    WORK_DIR,
    Settings,
    detect_network_addresses,
    hash_password,
    load_criteria,
    save_admin_password,
    save_direct_base_url,
)
from .bewertung_ods import read_roster as read_bewertung_roster, roster_class, read_subject, read_document_parameters
from .bewertung_ods import write_hefter_results
from .core import (
    difference_level,
    format_percent,
    grade_for_percent,
    parse_rating,
    rating_difference,
)
from .db import Database
from .feedback_output import generate_feedback_pdf, safe_filename
from .permutation import generate_derangement, swap_subjects
from .qr_access import (
    MAX_QR_IMAGE_BYTES,
    decode_qr_image,
    qr_png,
    student_token_from_qr_payload,
)
from .workflow import WorkflowError, validate_transition


STYLE = """
:root{font-family:Arial,Helvetica,sans-serif;color:#183126;background:#f4f7f4;
--space-1:8px;--space-2:16px;--space-3:24px;--space-4:32px}
*{box-sizing:border-box}body{margin:0}.bar{background:#356d09;color:white;padding:14px 20px}
.wrap{max-width:1180px;margin:0 auto;padding:20px}.card{background:white;border:1px solid #c8d3c8;
border-radius:10px;padding:18px;margin:0 0 16px;box-shadow:0 2px 8px #0000000b}
h1,h2,h3{margin-top:0}.muted{color:#617067}.notice{background:#e4f0d3;border-left:5px solid #72a82f;padding:12px}
.warning{background:#fff0ca;border-left:5px solid #d69500;padding:12px}.danger{background:#ffe3df;border-left:5px solid #b73a2f;padding:12px}
table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #cad3cb;padding:8px;text-align:left;vertical-align:top}
th{background:#dceaf5}.good{background:#e2f1ca}.medium{background:#fff0bf}.bad{background:#ffdcd6}
button,.button{display:inline-block;border:0;border-radius:6px;background:#487f0d;color:white;padding:9px 13px;
text-decoration:none;font-weight:bold;cursor:pointer;margin:2px}.secondary{background:#557084}.small{padding:5px 8px;font-size:.9rem}
input,select{padding:8px;border:1px solid #9ba99e;border-radius:5px;max-width:100%}label{font-weight:bold}
.inline{display:inline}.inline button{margin-left:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.criterion{border-top:1px solid #d5ddd6;padding:14px 0}
.criterion>.scale{margin-top:12px}.student-access-form input{display:block;width:100%;margin:8px 0 18px}
.admin-setup-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.workbook-header{background:#c6d9f1;border:1px solid #9da7ad;border-radius:5px;padding:16px 18px;margin-bottom:16px}
.path-block{display:block;margin-top:5px;padding:8px 10px;background:#fff;border:1px solid #cbd3d8;border-radius:5px;white-space:normal;overflow-wrap:anywhere;word-break:break-word}
.narrow{max-width:610px;margin:5vh auto}.scan-card-view{text-align:left;padding:24px;border-radius:7px}
.replacement-card{text-align:center;margin-top:18px;padding-top:14px;border-top:1px solid #cad3cb}
.replacement-card img{display:block;width:min(72vw,360px);height:auto;margin:12px auto}
.scale{display:flex;gap:8px;flex-wrap:wrap}.scale label{font-weight:normal;background:#edf2ed;border-radius:6px;padding:7px 10px}
.actions{display:flex;gap:var(--space-1);flex-wrap:wrap;align-items:center}.pill{display:inline-block;padding:3px 8px;border-radius:20px;background:#e7eee7}
.workflow{display:grid;grid-template-columns:repeat(4,minmax(170px,1fr));gap:0;margin:14px 0 18px}
.stage-shell{position:relative;min-width:0}
.stage-main{display:block;width:100%;height:112px;min-height:112px;margin:0;padding:12px 20px 43px;border:2px solid #c8d3c8;border-radius:0;
background:#fafbfa;color:#56645a;text-align:left;text-decoration:none}.stage-shell:first-child .stage-main{border-radius:9px 0 0 9px}
.stage-shell:last-child .stage-main{border-radius:0 9px 9px 0}.stage-shell:not(:first-child) .stage-main{border-left-width:1px}
.stage-shell.clickable .stage-main{cursor:pointer;color:#183126}.stage-shell.clickable .stage-main:hover{background:#edf5e4;border-color:#487f0d}
.stage-shell.done .stage-main{background:#eef1ee;color:#657069}.stage-shell.current .stage-main{background:#e4f0d3;
border-color:#487f0d;box-shadow:inset 0 0 0 1px #487f0d}.stage-shell.next .stage-main{background:#fff8df;
border-color:#d5b45d;color:#183126}.stage-title{font-weight:bold;margin-bottom:7px}
.stage-state{font-size:.85rem;font-weight:normal}.stage-form{margin:0}.stage-subform{position:absolute;left:20px;right:20px;bottom:7px;margin:0;text-align:left;z-index:4}
.stage-sub{padding:5px 8px;font-size:.82rem;background:#557084}.stage-sub:disabled{cursor:default;background:#d9dfda;color:#68736b}
.stage-shell.current:first-child:has(.stage-sub:hover) .stage-main{background:#e4f0d3;border-color:#487f0d;box-shadow:inset 0 0 0 1px #487f0d}
.rating-matrix tr.disagreement td{background:#fff8df}.rating-matrix td:first-child{width:58%}
.scale-line{position:relative;display:grid;grid-template-columns:repeat(4,minmax(58px,1fr));gap:8px;min-width:340px}
.scale-line::before{content:"";position:absolute;left:10%;right:10%;top:21px;border-top:2px solid #aeb9b0}
.scale-point{position:relative;z-index:1;display:grid;grid-template-columns:auto auto;grid-template-rows:auto 20px;
justify-content:center;align-items:center;column-gap:5px;padding:5px 4px 3px;border:2px solid transparent;border-radius:8px;
background:#f4f7f4;font-weight:normal;cursor:pointer;min-height:57px}
.scale-point:hover{border-color:#99ad9c}.scale-point:has(input:checked){border-color:#487f0d;background:#e4f0d3}
.scale-point.peer-diff{box-shadow:inset 0 0 0 1px #d1aa4b;background:#fff9e7}
.scale-point.peer-diff:has(input:checked){border-color:#487f0d;background:#e4f0d3;box-shadow:inset 0 0 0 2px #d1aa4b}
.scale-point input{margin:0;width:17px;height:17px;accent-color:#487f0d}.scale-number{font-size:1.05rem;font-weight:bold}
.markers{grid-column:1/3;display:flex;justify-content:center;gap:3px;min-height:18px}
.marker{display:inline-flex;align-items:center;justify-content:center;min-width:14px;height:18px;padding:0 2px;
font-size:.78rem;font-weight:bold;color:#4b5850;font-style:normal}.marker-separator{display:inline-flex;align-items:center;
justify-content:center;height:18px;color:#879189;font-size:.78rem}
.matrix-legend{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:0 0 10px}.matrix-legend .marker{margin-right:3px}
.matrix-help{color:#617067;font-size:.9rem}
.review-nav{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 14px}
.review-nav .disabled{color:#9aa39c;padding:7px 10px}
.save-actions{display:flex;gap:8px;align-items:center;justify-content:flex-end;flex-wrap:wrap;margin-top:14px}
.review-footer{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-top:14px}
.review-footer .review-nav,.review-footer .save-actions{margin:0}
.title-with-status{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 14px}
.title-with-status h1{margin:0}.status-saved{background:#e2f1ca}.status-open{background:#fff0bf}
.top-actions{display:flex;justify-content:flex-end;margin:0 0 12px}.top-actions form{margin:0}.danger-button{background:#963542}
.admin-header{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;background:#c6d9f1;
border:1px solid #9da7ad;border-radius:5px;padding:16px 18px;margin-bottom:18px}.admin-header h1{margin:3px 0}
.eyebrow{text-transform:uppercase;letter-spacing:.11em;font-size:.78rem;font-weight:bold;color:#557084}
.subtitle{font-size:1.08rem;margin:0 0 7px}.header-tools{display:flex;justify-content:flex-end;align-items:flex-start;gap:10px;flex-wrap:wrap}
.header-tools details{position:relative}.header-tools details[open] .password-panel{display:block}.password-panel{position:absolute;right:0;z-index:10;
width:min(390px,85vw);background:white;border:1px solid #c8d3c8;border-radius:10px;padding:15px;box-shadow:0 8px 24px #0002}
.network-option{display:block;background:#f7faf7;border:1px solid #c8d3c8;border-radius:7px;padding:8px;margin:7px 0;font-weight:normal}
.network-option code{font-weight:bold}.status-box{padding:12px;border-left:5px solid #487f0d;background:#e4f0d3}.panel-green{border-top:5px solid #72a82f}
.session-code{font-size:2.5rem;font-weight:bold;letter-spacing:.16em;text-align:center;background:#f1f6eb;border:2px solid #72a82f;border-radius:9px;padding:12px;margin:12px 0}
details>summary{cursor:pointer}.subsection{margin-top:24px;padding-top:18px;border-top:1px solid #d5ddd6}.file-name{overflow-wrap:anywhere}
.anchor-section{scroll-margin-top:var(--space-2)}.subsection h3+form{margin-bottom:var(--space-3)}.subsection .exclusions-title{margin-top:var(--space-4)}
.exclusion-form{margin-bottom:var(--space-2)}
.submission-status{margin-top:24px;padding-top:18px;border-top:1px solid #d5ddd6}
@media(max-width:650px){.wrap{padding:10px}th,td{padding:5px;font-size:.88rem}.hide-mobile{display:none}}
@media(max-width:760px){.admin-setup-grid{grid-template-columns:1fr}}
@media(max-width:900px){.workflow{grid-template-columns:1fr;gap:0}.stage-main{height:100px!important;min-height:100px!important;border-radius:0!important;border-left-width:2px!important}
.stage-shell:first-child .stage-main{border-radius:9px 9px 0 0!important}.stage-shell:last-child .stage-main{border-radius:0 0 9px 9px!important}
}
@media(max-width:700px){.rating-matrix td{display:block;width:100%!important}.rating-matrix th:last-child{display:none}.scale-line{min-width:0}.scale-point{min-height:53px}}
@media(max-width:650px){.scale{display:grid;grid-template-columns:1fr}.scale label{display:block;width:100%}}
"""

PHASE_LABELS = {
    "setup": "noch nicht geöffnet",
    "self": "Selbstbewertung",
    "self_closed": "Selbstbewertung abgeschlossen",
    "peer": "Peerbewertung",
    "peer_closed": "Peerbewertung abgeschlossen",
    "teacher": "Lehrerprüfung",
    "teacher_closed": "Lehrerbewertung abgeschlossen",
    "closed": "abgeschlossen",
}


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='de'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>"
        f"<main class='wrap'>{body}</main></body></html>"
    )


def redirect(url: str):
    return RedirectResponse(url, status_code=303)


def workflow_bar(
    session_id: int,
    phase: str,
    has_assignments: bool,
    teacher_review_opened: bool = False,
) -> str:
    phases = ["self", "peer", "teacher", "closed"]
    labels = {
        "self": "Selbstbewertung",
        "peer": "Peerbewertung",
        "teacher": "Lehrerprüfung",
        "closed": "Abschluss",
    }
    phase_progress = {
        "setup": (-1, None),
        "self": (0, "self"),
        "self_closed": (0, None),
        "peer": (1, "peer"),
        "peer_closed": (1, None),
        "teacher": (2, "teacher"),
        "teacher_closed": (2, None),
        "closed": (3, "closed"),
    }
    completed_index, active_item = phase_progress[phase]
    next_item = {
        "setup": "self",
        "self": None,
        "self_closed": "peer",
        "peer": None,
        "peer_closed": "teacher",
        "teacher": None,
        "teacher_closed": "closed",
        "closed": None,
    }[phase]
    stages = []
    for index, item in enumerate(phases):
        if item == "closed" and phase == "closed":
            css, state = "current", "abgeschlossen"
        elif item == active_item:
            css, state = "current", "geöffnet"
        elif index <= completed_index and item != "closed":
            css, state = "done", "abgeschlossen"
        elif item == next_item:
            css = "future next"
            state = {
                "self": "zum Start klicken",
                "peer": "zum Start klicken",
                "teacher": "zum Aktivieren klicken",
                "closed": "zum Abschließen klicken",
            }[item]
            if item == "peer" and phase == "self_closed" and not has_assignments:
                state = "zuerst Zuordnung erzeugen"
        else:
            css, state = "future", "folgt"
        inner = (
            f"<div class='stage-title'>{labels[item]}</div>"
            f"<div class='stage-state'>{state}</div>"
        )
        action = ""
        clickable = False
        if item == "self" and phase == "setup":
            action = f"/admin/session/{session_id}/phase"
            hidden = "<input type='hidden' name='phase' value='self'>"
            clickable = True
        elif item == "self" and phase == "self":
            stages.append(
                f"<div class='stage-shell current'><div class='stage-main'>{inner}</div>"
                f"<form class='stage-subform' method='post' action='/admin/session/{session_id}/phase'>"
                "<input type='hidden' name='phase' value='self_closed'>"
                "<button class='stage-sub' type='submit'>Selbstbewertung abschließen</button></form></div>"
            )
            continue
        elif item == "peer" and phase == "self_closed" and has_assignments:
            action = f"/admin/session/{session_id}/phase"
            hidden = "<input type='hidden' name='phase' value='peer'>"
            clickable = True
        elif item == "peer" and phase == "peer":
            stages.append(
                f"<div class='stage-shell current'><div class='stage-main'>{inner}</div>"
                f"<form class='stage-subform' method='post' action='/admin/session/{session_id}/phase'>"
                "<input type='hidden' name='phase' value='peer_closed'>"
                "<button class='stage-sub' type='submit'>Peerbewertung abschließen</button></form></div>"
            )
            continue
        elif item == "teacher" and phase == "peer_closed":
            action = f"/admin/session/{session_id}/phase"
            hidden = "<input type='hidden' name='phase' value='teacher'>"
            clickable = True
        elif item == "teacher" and phase == "teacher":
            sub = (
                f"<form class='stage-subform' method='post' action='/admin/session/{session_id}/phase'>"
                "<input type='hidden' name='phase' value='teacher_closed'>"
                "<button class='stage-sub' type='submit'>Lehrerbewertung abschließen</button></form>"
                if teacher_review_opened else
                "<div class='stage-subform'><button class='stage-sub' type='button' disabled>"
                "zuerst Lehrerprüfung öffnen</button></div>"
            )
            stages.append(
                f"<div class='stage-shell current clickable'><a class='stage-main' href='/admin/session/{session_id}/review'>"
                f"<div class='stage-title'>{labels[item]}</div><div class='stage-state'>zum Öffnen klicken</div></a>"
                f"{sub}</div>"
            )
            continue
        elif item == "teacher" and phase == "teacher_closed":
            stages.append(
                f"<div class='stage-shell done'><div class='stage-main'>{inner}</div>"
                f"<form class='stage-subform' method='post' action='/admin/session/{session_id}/phase'>"
                "<input type='hidden' name='phase' value='teacher'>"
                "<button class='stage-sub' type='submit'>Wieder öffnen</button></form></div>"
            )
            continue
        elif item == "closed" and phase == "teacher_closed":
            stages.append(
                f"<div class='stage-shell next clickable'>"
                f"<form class='stage-form' method='post' action='/admin/session/{session_id}/phase'>"
                "<input type='hidden' name='phase' value='closed'>"
                f"<button class='stage-main' type='submit'>{inner}</button></form>"
                "<div class='stage-subform'><button class='stage-sub' type='button' disabled>"
                "noch offen</button></div></div>"
            )
            continue
        elif item == "closed" and phase == "closed":
            stages.append(
                f"<div class='stage-shell current clickable'><a class='stage-main' href='/admin/session/{session_id}/review'>{inner}</a>"
                f"<div class='stage-subform'><a class='button stage-sub' href='/admin/session/{session_id}/review'>Ergebnisse ansehen</a></div></div>"
            )
            continue
        if clickable:
            stage_main = (
                f"<form class='stage-form' method='post' action='{action}'>{hidden}"
                f"<button class='stage-main' type='submit'>{inner}</button></form>"
            )
            shell_css = f"{css} clickable"
        else:
            stage_main = f"<div class='stage-main'>{inner}</div>"
            shell_css = css
        subaction = ""
        if item == "peer":
            if phase in {"self", "self_closed"}:
                sub_label = "Zuordnung ändern" if has_assignments else "Zuordnung erzeugen"
                subaction = (
                    f"<form class='stage-subform' method='post' action='/admin/session/{session_id}/assign'>"
                    f"<button class='stage-sub' type='submit'>{sub_label}</button></form>"
                )
            elif phase == "setup":
                subaction = "<div class='stage-subform'><button class='stage-sub' type='button' disabled>Zuordnung folgt</button></div>"
            else:
                subaction = "<div class='stage-subform'><button class='stage-sub' type='button' disabled>Zuordnung festgelegt</button></div>"
        elif item == "self" and phase not in {"self"}:
            sub_label = "noch nicht geöffnet" if phase == "setup" else "abgeschlossen"
            subaction = f"<div class='stage-subform'><button class='stage-sub' type='button' disabled>{sub_label}</button></div>"
        elif item == "teacher" and phase != "teacher":
            sub_label = "abgeschlossen" if phase in {"teacher_closed", "closed"} else "noch nicht geöffnet"
            subaction = f"<div class='stage-subform'><button class='stage-sub' type='button' disabled>{sub_label}</button></div>"
        elif item == "closed":
            sub_label = "Ergebnisse ansehen" if phase == "closed" else "noch nicht erreicht"
            subaction = f"<div class='stage-subform'><button class='stage-sub' type='button' disabled>{sub_label}</button></div>"
        stages.append(
            f"<div class='stage-shell {shell_css}'>{stage_main}{subaction}</div>"
        )
    return f"<div class='workflow'>{''.join(stages)}</div>"


def rating_form(criteria: dict, action: str, values: dict | None = None, submit_label: str = "Bewertung verbindlich abgeben") -> str:
    values = values or {}
    rows = []
    for number, item in enumerate(criteria["criteria"], start=1):
        cid = str(item["id"])
        options = []
        for value in range(4, 0, -1):
            checked = " checked" if int(values.get(cid, 0) or 0) == value else ""
            label = escape(str(criteria["scale"][str(value)]))
            options.append(
                f"<label><input required type='radio' name='c_{escape(cid)}' value='{value}'{checked}> {value} – {label}</label>"
            )
        rows.append(
            f"<div class='criterion'><strong>{number}. {escape(str(item['label']))}</strong>"
            f"<div class='scale'>{''.join(options)}</div></div>"
        )
    return (
        f"<form method='post' action='{escape(action)}' "
        "onsubmit=\"return window.confirm('Jetzt verbindlich abgeben? Danach kannst du die Bewertung nicht selbst erneut ändern.');\">"
        f"{''.join(rows)}"
        "<label style='display:flex;gap:8px;align-items:flex-start;margin:12px 0;font-weight:normal'>"
        "<input required type='checkbox' name='confirmed' value='yes'>"
        "<span>Ich habe meine Bewertung geprüft und möchte sie verbindlich abgeben.</span></label>"
        f"<button>{escape(submit_label)}</button></form>"
    )


def create_app(settings: Settings) -> FastAPI:
    criteria = load_criteria()
    criterion_ids = [str(item["id"]) for item in criteria["criteria"]]
    db = Database(
        DB_FILE,
        WORKSPACE_ID,
        SHARED_IDENTITY_FILE,
        WORK_DIR / "HB-Collector-Sicherungen",
    )
    security = HTTPBasic()
    settings_state: dict[str, Settings] = {"value": settings}
    app_work_dir = WORK_DIR
    app = FastAPI(title="HB-Collector", version=VERSION, docs_url=None, redoc_url=None)

    def current_settings() -> Settings:
        return settings_state["value"]

    def submission_status_rows(session_id: int, phase: str) -> str:
        rows = []
        for row in db.comparisons(session_id):
            self_status = "abgegeben" if row["self_submitted_at"] else "offen"
            peer_status = "abgegeben" if row["peer_submitted_at"] else "offen"
            reopen = ""
            if phase == "self" and row["self_submitted_at"]:
                reopen = (
                    f"<form method='post' action='/admin/session/{session_id}/self/{row['student_id']}/reopen'>"
                    "<button class='small secondary'>Erneut freigeben</button></form>"
                )
            rows.append(
                f"<tr><td>{row['list_position']}</td><td>{escape(row['name'])}</td>"
                f"<td>{self_status}</td><td>{peer_status}</td><td>{reopen}</td></tr>"
            )
        return "".join(rows)

    def admin(credentials: HTTPBasicCredentials = Depends(security)):
        settings = current_settings()
        if not (
            hmac.compare_digest(credentials.username, settings.admin_user)
            and hmac.compare_digest(hash_password(credentials.password), settings.admin_password_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültige Zugangsdaten",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username

    @app.get("/", response_class=HTMLResponse)
    def home():
        if not current_settings().admin_password_hash:
            return page(
                "Lehrerpasswort noch nicht eingerichtet",
                "<div class='card narrow'><div class='eyebrow'>Ersteinrichtung erforderlich</div>"
                "<h1>Lehrerpasswort noch nicht eingerichtet</h1>"
                "<p>Bitte zuerst QR starten und dort im Browser für den Benutzer "
                "<strong>lehrkraft</strong> ein gemeinsames Lehrerpasswort festlegen.</p>"
                "<p>Danach HB neu starten.</p></div>",
            )
        return page(
            "HB-Collector",
            "<div class='card'><h1>Hefterbewertung</h1>"
            "<p>Öffne deinen persönlichen Schülerlink oder die Lehreroberfläche.</p>"
            "<a class='button' href='/admin'>Lehreroberfläche</a></div>",
        )

    @app.get("/admin", response_class=HTMLResponse)
    def admin_home(message: str = "", _: str = Depends(admin)):
        settings = current_settings()
        ods_file = app_work_dir / "Hefterbewertung.ods"
        ods_error = ""
        ods_class = ""
        try:
            ods_students = read_bewertung_roster(ods_file)
            ods_class = roster_class(ods_students)
            db.import_ods_roster(ods_class, ods_students)
        except Exception as exc:
            ods_error = str(exc)
        classes = db.classes()
        sessions = db.sessions()
        archived_sessions = db.sessions(archived=True)
        class_options = "".join(
            f"<option value='{escape(row['class_id'])}'>{escape(row['class_id'])} ({row['count']})</option>"
            for row in classes
        )
        qr_card_links = "".join(
            f"<p><a class='button secondary' href='/admin/cards/{quote(str(row['class_id']))}'>"
            f"QR-Karte anzeigen · {escape(str(row['class_id']))}</a></p>"
            for row in classes
        ) or "<p class='muted'>Noch keine Klasse verfügbar.</p>"
        session_rows = "".join(
            f"<tr><td>{row['id']}</td><td>{escape(row['class_id'])}</td><td>{escape(row['period'])}</td>"
            f"<td>{escape(PHASE_LABELS.get(row['phase'], row['phase']))}</td><td>{row['self_count']}/{row['roster_count']}</td>"
            f"<td>{row['peer_count']}/{row['roster_count']}</td><td>{row['teacher_count']}/{row['roster_count']}</td>"
            f"<td><a class='button small' href='/admin/session/{row['id']}'>Öffnen</a>"
            + (
                f"<form class='inline' method='post' action='/admin/session/{row['id']}/repeat'>"
                "<button class='small secondary'>Wiederholen</button></form>"
                if row["phase"] == "closed"
                else ""
            )
            + (
                f"<form class='inline' method='post' action='/admin/session/{row['id']}/archive'>"
                "<button class='small secondary'>Archivieren</button></form>"
                if row["phase"] == "closed"
                else ""
            )
            + "</td></tr>"
            for row in sessions
        ) or "<tr><td colspan='8'>Noch keine Bewertung angelegt.</td></tr>"
        archived_rows = "".join(
            f"<tr><td>{row['id']}</td><td>{escape(row['class_id'])}</td>"
            f"<td>{escape(row['period'])}</td><td>{escape(row['title'])}</td><td>"
            f"<form class='inline' method='post' action='/admin/session/{row['id']}/restore'>"
            "<button class='small secondary'>Wiederherstellen</button></form>"
            f"<form class='inline' method='post' action='/admin/session/{row['id']}/delete' "
            f"onsubmit=\"return confirm('Bewertung ID {row['id']} wirklich endgültig löschen? Vorher wird eine Sicherung angelegt.')\">"
            f"<input type='hidden' name='confirmation' value='{row['id']}'>"
            "<button class='small danger-button'>Endgültig löschen</button></form></td></tr>"
            for row in archived_sessions
        ) or "<tr><td colspan='5'>Noch keine archivierte Bewertung.</td></tr>"
        preferred_ip = ""
        if settings.direct_base_url:
            from urllib.parse import urlsplit

            preferred_ip = urlsplit(settings.direct_base_url).hostname or ""
        detected = detect_network_addresses(settings.port, preferred_ip)
        address_options = "".join(
            f"<label class='network-option'><input type='radio' name='direct_base_url' value='{escape(item.url)}'"
            f"{' checked' if settings.direct_base_url == item.url or (not settings.direct_base_url and item.recommended) else ''}> "
            f"<code>{escape(item.url)}</code> · {escape(item.interface)}"
            f"{' <strong>(empfohlen)</strong>' if item.recommended else ''}"
            f"{' <strong>(aktuell verwendet)</strong>' if settings.direct_base_url == item.url else ''}</label>"
            for item in detected
        )
        current_direct = (
            f"<p class='notice'>Eingerichtet: <strong>{escape(settings.direct_base_url)}</strong></p>"
            if settings.direct_base_url else
            "<p class='warning'>Noch keine Direktadresse eingerichtet.</p>"
        )
        bewertung_file = ods_file
        ods_status = (
            f"<p class='notice'><strong>Namensliste bereit:</strong> Klasse {escape(ods_class)} · "
            f"{len(read_bewertung_roster(ods_file))} Personen</p>"
            if not ods_error
            else f"<p class='warning'><strong>Hefterbewertung.ods noch nicht bereit.</strong><br>{escape(ods_error)}</p>"
        )
        feedback = f"<p class='notice'>{escape(message)}</p>" if message else ""
        body = f"""
        <header class='admin-header'><div><div class='eyebrow'>Lokale Verwaltung</div>
          <h1>HB</h1><p class='subtitle'>Hefterbewertung · Version {VERSION}</p>
          <p class='muted'><strong>Arbeitsordner</strong><code class='path-block'>{escape(str(app_work_dir))}</code></p></div>
          <div class='header-tools'><details><summary class='button secondary'>Lehrerpasswort ändern</summary>
            <div class='password-panel'><p class='muted'>Das Passwort gilt für alle Collectoren und muss mindestens 10 Zeichen lang sein.</p>
            <form method='post' action='/admin/settings/password'>
              <p><label>Bisheriges Passwort<br><input required type='password' name='old_password'></label></p>
              <p><label>Neues Passwort<br><input required minlength='10' type='password' name='new_password'></label></p>
              <p><label>Neues Passwort wiederholen<br><input required minlength='10' type='password' name='repeat_password'></label></p>
              <button>Passwort ändern</button></form></div></details>
            <form method='post' action='/admin/shutdown'><button class='danger-button'>HB beenden</button></form>
          </div></header>
        {feedback}
        <div class='admin-setup-grid'>
          <section class='card'>
            <h2>1. Namensliste</h2>
            {ods_status}
            <p><strong>Datei:</strong> <code class='file-name'>{escape(ods_file.name)}</code></p>
            <form method='post' action='/admin/import-ods'>
              <button>Hefterbewertung.ods erneut prüfen</button>
            </form>
            <p><a class='button secondary' href='/admin/download-ods'>Hefterbewertung.ods herunterladen</a></p>
          </section>
          <section class='card'>
            <h2>2. Direktmodus</h2>
            {current_direct}
            <p>Die Adresse des QR-Generators wird automatisch übernommen. Nur bei einer bewussten Änderung hier eine andere lokale Adresse wählen.</p>
            <p class='warning'><strong>Vor dem Unterricht:</strong> Laptop und Schülergeräte mit demselben WLAN verbinden; VPN auf den Schülergeräten ausschalten.</p>
            <form method='post' action='/admin/settings/direct-url'>
              {address_options}
              <button>Diese Adresse für den Direktmodus verwenden</button>
            </form>
            <form method='post' action='/admin/settings/direct-url'>
              <input type='hidden' name='direct_base_url' value=''>
              <button class='secondary'>Direktmodus deaktivieren</button>
            </form>
          </section>
          <section class='card'>
            <h2>3. QR-Karte anzeigen</h2>
            <p class='muted'>Falls eine persönliche QR-Karte vergessen wurde, kann sie hier zum Scannen angezeigt werden. Neue Karten werden weiterhin ausschließlich in QR erzeugt.</p>
            {qr_card_links}
          </section>
          <section class='card'>
            <h2>4. Halbjahresbewertung öffnen</h2>
            <form method='post' action='/admin/session'>
              <input type='hidden' name='class_id' value='{escape(ods_class)}'>
              <p><label>Zeitraum<br><input required name='period' placeholder='1. Halbjahr 2026/27'></label></p>
              <button{' disabled' if not ods_class else ''}>Bewertung öffnen</button>
            </form>
            <p class='muted'>Die Klasse wird aus der Namensliste übernommen. Für denselben Zeitraum kann eine vorhandene Bewertung über die Liste unten geöffnet werden.</p>
          </section>
        </div>
        <section class='card'><h2>Bewertungen</h2><table>
        <tr><th>ID</th><th>Klasse</th><th>Zeitraum</th><th>Phase</th><th>Selbst</th><th>Peer</th><th>Lehrkraft</th><th></th></tr>
        {session_rows}</table></section>
        <details class='card'><summary><strong>Archivierte Bewertungen</strong></summary>
          <p class='muted'>Archivierte Bewertungen bleiben gespeichert. Nicht mehr benötigte Einträge können hier nach Eingabe ihrer ID endgültig gelöscht werden; zuvor wird automatisch eine Datenbanksicherung erstellt.</p>
          <table><tr><th>ID</th><th>Klasse</th><th>Zeitraum</th><th>Titel</th><th></th></tr>
          {archived_rows}</table>
        </details>
        """
        return page("Lehreroberfläche", body)

    @app.get("/admin/cards/{class_id}", response_class=HTMLResponse)
    def show_student_card(
        class_id: str,
        student_token: str = "",
        _: str = Depends(admin),
    ):
        students = db.identities.roster_for_class(class_id)
        selected = next(
            (row for row in students if str(row["public_token"]) == student_token),
            None,
        )
        options = "".join(
            f"<option value='{escape(str(row['public_token']))}'"
            f"{' selected' if selected and row['public_token'] == selected['public_token'] else ''}>"
            f"{row['list_position']} · {escape(str(row['name']))}</option>"
            for row in students
        )
        card = ""
        if selected:
            if not current_settings().direct_base_url:
                card = "<p class='warning'>Bitte zuerst in der Übersicht den Direktmodus einrichten.</p>"
            else:
                card = (
                    f"<div class='replacement-card'>"
                    f"<h2>{escape(str(selected['name']))}</h2>"
                    f"<p>Schüler-ID {escape(str(selected['student_key']))}</p>"
                    f"<img src='/admin/qr/student/{quote(str(selected['public_token']))}.png' "
                    "alt='Persönlicher QR-Code'>"
                    "<p><strong>Am Schülergerät scannen.</strong></p>"
                    "<p class='muted'>Mit dem Klassen-WLAN verbinden und VPN ausschalten.</p></div>"
                )
        body = f"""
        <header class='workbook-header'><div class='eyebrow'>Ausweichhilfe</div>
          <h1>QR-Karte anzeigen</h1>
          <p class='subtitle'>Nur für SuS, die ihre persönliche QR-Karte vergessen haben.</p></header>
        <section class='card narrow scan-card-view'>
        <form method='get' action='/admin/cards/{quote(class_id)}'>
          <label for='student_token'>Schülerin oder Schüler</label>
          <select id='student_token' name='student_token' onchange='this.form.submit()'>
            <option value=''>Bitte auswählen</option>{options}
          </select>
          <noscript><button class='button' type='submit'>Anzeigen</button></noscript>
        </form>{card}
        <p><a class='button secondary' href='/admin'>Zur Lehrerübersicht</a></p>
        </section>
        """
        return page("QR-Karte anzeigen", body)

    @app.get("/admin/qr/student/{student_token}.png")
    def student_qr(student_token: str, _: str = Depends(admin)):
        student = db.student_by_token(student_token)
        direct_base_url = current_settings().direct_base_url
        if not student or not direct_base_url:
            raise HTTPException(404)
        return Response(
            qr_png(f"{direct_base_url.rstrip('/')}/p/{student_token}"),
            media_type="image/png",
        )

    @app.post("/admin/settings/direct-url")
    def update_direct_url(
        direct_base_url: str = Form(""),
        _: str = Depends(admin),
    ):
        try:
            settings_state["value"] = save_direct_base_url(direct_base_url)
        except ValueError as exc:
            return page("Adresse ungültig", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        return redirect("/admin")

    @app.post("/admin/shutdown", response_class=HTMLResponse)
    def shutdown_collector(request: Request, _: str = Depends(admin)):
        server = getattr(request.app.state, "server", None)
        if server is not None:
            threading.Timer(0.5, lambda: setattr(server, "should_exit", True)).start()
        return page(
            "HB beendet",
            "<section class='card' style='max-width:560px;margin:32px auto;text-align:center'>"
            "<div style='font-size:2rem'>✓</div><h1>HB beendet</h1>"
            "<p>Das Programm wurde geschlossen. Dieses Browserfenster kann jetzt geschlossen werden.</p></section>",
        )

    @app.post("/admin/settings/password", response_class=HTMLResponse)
    def update_password(
        old_password: str = Form(...),
        new_password: str = Form(...),
        repeat_password: str = Form(...),
        _: str = Depends(admin),
    ):
        current = current_settings()
        if not hmac.compare_digest(hash_password(old_password), current.admin_password_hash):
            return page("Passwort nicht geändert", "<div class='danger'><p>Das bisherige Passwort ist falsch.</p></div>")
        if new_password != repeat_password:
            return page("Passwort nicht geändert", "<div class='danger'><p>Die neuen Passwörter stimmen nicht überein.</p></div>")
        try:
            settings_state["value"] = save_admin_password(new_password)
        except ValueError as exc:
            return page("Passwort nicht geändert", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        return page(
            "Passwort geändert",
            "<div class='notice'><h1>Lehrerpasswort geändert</h1>"
            "<p>Der Browser kann die Anmeldung beim nächsten Aufruf erneut abfragen.</p></div>"
            "<p><a class='button' href='/admin'>Zur Lehreroberfläche</a></p>",
        )

    @app.post("/admin/import-ods")
    def import_ods(_: str = Depends(admin)):
        try:
            ods_students = read_bewertung_roster(app_work_dir / "Hefterbewertung.ods")
            class_id = roster_class(ods_students)
            count = db.import_ods_roster(
                class_id,
                ods_students,
            )
        except Exception as exc:
            return page(
                "Importfehler",
                f"<div class='danger'><h1>Namensliste nicht geladen</h1>"
                f"<p>{escape(str(exc))}</p></div><p><a class='button' href='/admin'>Zurück</a></p>",
            )
        return redirect(
            f"/admin?message={quote(f'{count} Personen aus Hefterbewertung.ods übernommen.')}"
        )

    @app.get("/admin/download-ods")
    def download_ods(_: str = Depends(admin)):
        path = app_work_dir / "Hefterbewertung.ods"
        if not path.exists():
            raise HTTPException(404, "Hefterbewertung.ods fehlt.")
        return FileResponse(path, media_type="application/vnd.oasis.opendocument.spreadsheet", filename=path.name)

    @app.post("/admin/session")
    def create_session(
        class_id: str = Form(...), period: str = Form(...), _: str = Depends(admin)
    ):
        try:
            session_id = db.create_session(class_id.strip(), period.strip(), "Hefterbewertung")
        except Exception as exc:
            return page("Fehler", f"<div class='danger'><h1>Bewertung nicht angelegt</h1><p>{escape(str(exc))}</p></div>")
        return redirect(f"/admin/session/{session_id}")

    @app.post("/admin/session/{session_id}/repeat")
    def repeat_session(session_id: int, _: str = Depends(admin)):
        try:
            new_session_id = db.repeat_session(session_id)
        except ValueError as exc:
            return page(
                "Wiederholung nicht möglich",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        return redirect(f"/admin/session/{new_session_id}")

    @app.post("/admin/session/{session_id}/archive")
    def archive_session(session_id: int, _: str = Depends(admin)):
        try:
            db.archive_session(session_id)
        except ValueError as exc:
            return page(
                "Archivieren nicht möglich",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        return redirect("/admin?message=Bewertung%20archiviert.")

    @app.post("/admin/session/{session_id}/restore")
    def restore_session(session_id: int, _: str = Depends(admin)):
        try:
            db.restore_session(session_id)
        except ValueError as exc:
            return page(
                "Wiederherstellen nicht möglich",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        return redirect("/admin?message=Bewertung%20wieder%20eingeblendet.")

    @app.post("/admin/session/{session_id}/delete")
    def delete_session(
        session_id: int,
        confirmation: str = Form(...),
        _: str = Depends(admin),
    ):
        if confirmation.strip() != str(session_id):
            return page(
                "Löschen nicht bestätigt",
                "<div class='danger'><p>Die eingegebene ID stimmt nicht überein. "
                "Es wurde nichts gelöscht.</p></div>",
            )
        try:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = db.backup_to(
                app_work_dir
                / "HB-Collector-Sicherungen"
                / f"HB-Datenbank_vor_Loeschen_{stamp}.sqlite3"
            )
            db.delete_archived_session(session_id)
        except ValueError as exc:
            return page(
                "Löschen nicht möglich",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        return redirect(
            f"/admin?message={quote(f'Bewertung gelöscht. Sicherung: {backup.name}')}"
        )

    @app.get("/admin/session/{session_id}", response_class=HTMLResponse)
    def session_admin(session_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        assignments = db.assignments(session_id)
        exclusions = db.exclusions(session_id)
        assignment_rows = "".join(
            f"<tr><td>{row['reviewer_no']} · {escape(row['reviewer_name'])}</td>"
            f"<td>{row['subject_no']} · {escape(row['subject_name'])}</td></tr>"
            for row in assignments
        ) or "<tr><td colspan='2'>Noch nicht erzeugt.</td></tr>"
        exclusion_rows = "".join(
            f"<tr><td>{row['student_a_no']} · {escape(row['student_a_name'])}</td>"
            f"<td>{row['student_b_no']} · {escape(row['student_b_name'])}</td><td>"
            f"<form method='post' action='/admin/session/{session_id}/exclusion/remove'>"
            f"<input type='hidden' name='student_a_id' value='{row['student_a_id']}'>"
            f"<input type='hidden' name='student_b_id' value='{row['student_b_id']}'>"
            "<button class='small secondary'>Entfernen</button></form></td></tr>"
            for row in exclusions
        ) or "<tr><td colspan='3'>Keine Paare ausgeschlossen.</td></tr>"
        students = db.roster(session_id)
        progress_rows = submission_status_rows(session_id, str(session["phase"]))
        phase_help = {
            "setup": "Die Selbstbewertung kann sofort geöffnet werden. Die Peerzuordnung wird spätestens vor Beginn der Peerbewertung benötigt.",
            "self": "Die Selbstbewertung ist geöffnet. Die Peerzuordnung kann jetzt erzeugt oder noch geändert werden.",
            "self_closed": "Die Selbstbewertung ist abgeschlossen. Nach Erzeugung der Zuordnung kann die Peerbewertung geöffnet werden.",
            "peer": "Die Peerbewertung ist geöffnet. Dieselben persönlichen Links führen jetzt zur zugewiesenen Fremdbewertung.",
            "peer_closed": "Die Peerbewertung ist abgeschlossen. Als Nächstes kann die Lehrerprüfung geöffnet werden.",
            "teacher": "Die Schülerbewertungen sind beendet. Jetzt erfolgt die verbindliche Lehrerbewertung.",
            "teacher_closed": "Die Lehrerbewertung ist beendet, kann aber noch einmal geöffnet werden. Erst der Abschluss sperrt die gesamte Bewertung endgültig.",
            "closed": "Die Bewertung ist abgeschlossen und kann nur noch angesehen oder exportiert werden.",
        }[session["phase"]]
        has_assignments = len(assignments) == len(students)
        workflow = workflow_bar(
            session_id,
            session["phase"],
            has_assignments,
            bool(session["teacher_review_opened"]),
        )
        swap_form = ""
        exclusion_form = ""
        if session["phase"] in {"setup", "self", "self_closed"}:
            swap_form = f"""
              <form method='post' action='/admin/session/{session_id}/swap'>
                <label>Prüfende Nr. <input required type='number' min='1' name='reviewer_a'></label>
                <label>mit Nr. <input required type='number' min='1' name='reviewer_b'></label>
                <button class='secondary'>zugewiesene Hefter tauschen</button>
              </form>"""
            exclusion_form = f"""
              <form class='exclusion-form' method='post' action='/admin/session/{session_id}/exclusion'>
                <label>Listenplatz <input required type='number' min='1' name='student_a_no'></label>
                <label>und <input required type='number' min='1' name='student_b_no'></label>
                <button class='secondary'>Paar ausschließen</button>
              </form>"""
        feedback_action = (
            f"<a class='button' href='/admin/session/{session_id}/feedback.pdf'>"
            "Rückmeldebögen als PDF</a>"
            if session["phase"] in {"teacher_closed", "closed"}
            else ""
        )
        active_settings = current_settings()
        presentation_url = f"{active_settings.direct_base_url}/anzeige" if active_settings.direct_base_url else "/anzeige"
        presentation_section = f"""
        <section class='card'><h2>Präsentationsansicht am Smartboard</h2>
          <p>Am Smartboard im Browser <code>{escape(presentation_url)}</code> öffnen und dort den Sitzungscode eingeben.</p>
          <p class='muted'>Diese Ansicht zeigt keine Namen, Punkte oder Noten.</p>
        </section>"""
        if active_settings.direct_base_url:
            access_url = (
                f"{active_settings.direct_base_url}/access/{session['access_token']}"
            )
            access_section = f"""
            <section class='card panel-green'><h2>Direktmodus</h2>
              <p class='warning'><strong>Vor dem Scannen:</strong> Mit dem Klassen-WLAN verbinden und VPN ausschalten.</p>
              <p><strong>Normaler Zugang:</strong> Die SuS scannen ihre persönliche QR-Karte und geben anschließend diesen Sitzungscode ein:</p>
              <div class='session-code'>{escape(session['session_code'])}</div>
              <p class='status-box'><strong>Direktmodus aktiviert</strong><br>
              Verwendete Adresse: <code>{escape(active_settings.direct_base_url)}</code></p>
              <details><summary><strong>Ausweichweg: Zwei-QR-Modus anzeigen</strong></summary>
                <p>Zuerst diesen Sitzungs-QR scannen, danach die persönliche QR-Karte.
                Dabei darf die Adresse auf einer älteren persönlichen Karte veraltet sein.</p>
                <img src='/admin/session/{session_id}/access-qr.png'
                     alt='Sitzungs-QR-Code' width='260' height='260'>
                <p class='muted'><code>{escape(access_url)}</code></p>
              </details>
            </section>"""
        else:
            access_section = """
            <section class='card'><h2>Direktmodus</h2>
              <p class='warning'>Noch nicht eingerichtet. Bitte in der Übersicht
              eine lokale Adresse auswählen. Bis dahin kann keine QR-Verbindung hergestellt werden.</p>
            </section>"""
        body = f"""
        <p><a href='/admin'>← Übersicht</a></p>
        <h1>{escape(session['title'])} · {escape(session['class_id'])}</h1>
        <p><span class='pill'>Zeitraum: {escape(session['period'])}</span>
           <span class='pill'>Phase: {escape(PHASE_LABELS.get(session['phase'], session['phase']))}</span></p>
        <p class='notice'>{escape(phase_help)}</p>
        {presentation_section}
        {access_section}
        <section class='card anchor-section' id='workflow'><h2>Ablauf steuern</h2>
          {workflow}
          <div class='actions'>
          {feedback_action}
          <form method='post' action='/admin/session/{session_id}/export-ods'>
            <button>Hefterbewertung.ods aktualisieren</button>
          </form>
          <a class='button secondary' href='/admin/download-ods'>Hefterbewertung.ods herunterladen</a>
          </div>
          <div class='submission-status'><h3>Abgabestand</h3>
          <table><thead><tr><th>Nr.</th><th>Name</th><th>Selbstbewertung</th><th>Peerbewertung</th><th></th></tr></thead>
          <tbody id='submission-status-rows'>{progress_rows}</tbody></table>
          <p class='muted'>Wird automatisch aktualisiert.</p></div>
        </section>
        <section class='card anchor-section' id='assignment'><h2>Zufällige Zuordnung</h2>
          <p>Die Zuordnung enthält weder Selbstbewertungen, gegenseitige Zweierpaare
          noch die unten ausgeschlossenen Kombinationen.</p>
          <h3>Erzeugte Zuordnung</h3>
          <table><tr><th>Prüfende Person</th><th>Hefter von</th></tr>{assignment_rows}</table>
          <div class='subsection'><h3>Zuordnung anpassen</h3>
          {swap_form}
          <h3 class='exclusions-title'>Ausgeschlossene Paare</h3>
          <p>Die beiden Personen werden einander in keiner Richtung zugewiesen.
          Ein neuer Ausschluss verwirft eine bereits erzeugte Zuordnung.</p>
          {exclusion_form}
          <table><tr><th>Person</th><th>nicht mit</th><th></th></tr>{exclusion_rows}</table>
          </div>
        </section>
        <script>
        (() => {{
          const scrollKey = 'hb-session-scroll:{session_id}';
          const saved = sessionStorage.getItem(scrollKey);
          if (saved !== null) {{
            sessionStorage.removeItem(scrollKey);
            requestAnimationFrame(() => window.scrollTo(0, Number(saved) || 0));
          }}
          document.querySelectorAll('#workflow form, #assignment form').forEach(form => {{
            form.addEventListener('submit', () => sessionStorage.setItem(scrollKey, String(window.scrollY)));
          }});
          const target = document.getElementById('submission-status-rows');
          if (!target) return;
          const refresh = async () => {{
            try {{
              const response = await fetch('/admin/session/{session_id}/submission-status', {{cache:'no-store'}});
              if (response.ok) target.innerHTML = await response.text();
            }} catch (_) {{}}
          }};
          setInterval(refresh, 3000);
        }})();
        </script>
        """
        return page("Bewertung steuern", body)

    @app.get("/admin/session/{session_id}/submission-status", response_class=HTMLResponse)
    def submission_status(session_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        return HTMLResponse(submission_status_rows(session_id, str(session["phase"])))

    @app.post("/admin/session/{session_id}/self/{student_id}/reopen")
    def reopen_self_rating(
        session_id: int,
        student_id: int,
        _: str = Depends(admin),
    ):
        session = db.session(session_id)
        if not session or session["phase"] != "self":
            return page(
                "Wiederfreigabe nicht möglich",
                "<div class='danger'><p>Eine Selbstbewertung kann nur während der geöffneten Selbstbewertungsphase erneut freigegeben werden.</p></div>",
            )
        if not any(int(row["student_id"]) == student_id for row in db.roster(session_id)):
            raise HTTPException(404)
        db.delete_rating(session_id, student_id, "self")
        return redirect(f"/admin/session/{session_id}")

    @app.get("/admin/session/{session_id}/access-qr.png")
    def access_qr(session_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        direct_base_url = current_settings().direct_base_url
        if not direct_base_url:
            raise HTTPException(409, "Aktuelle IP-Adresse ist noch nicht ausgewählt.")
        return Response(
            qr_png(f"{direct_base_url}/access/{session['access_token']}"),
            media_type="image/png",
        )

    @app.get("/access/{access_token}", response_class=HTMLResponse)
    def two_qr_page(access_token: str):
        session = db.session_by_access_token(access_token)
        if not session:
            raise HTTPException(404, "Sitzung nicht gefunden.")
        if session["phase"] not in {"self", "peer"}:
            return page(
                "Bewertung nicht geöffnet",
                "<div class='warning'><p>Diese Bewertung ist derzeit nicht "
                "für Eingaben geöffnet.</p></div>",
            )
        body = f"""
        <section class='card' style='max-width:620px;margin:20px auto'>
          <p class='pill'>{escape(session['class_id'])} · {escape(session['period'])}</p>
          <h1>Persönliche QR-Karte scannen</h1>
          <p class='warning'><strong>Vor dem Scannen:</strong> Mit dem Klassen-WLAN verbinden und VPN ausschalten.</p>
          <ol>
            <li>Gib zuerst den sechsstelligen Sitzungscode ein, der im Klassenraum angezeigt wird.</li>
            <li>Tippe auf „Kamera öffnen“. Je nach Handy öffnet sich entweder direkt die Kamera oder die Bildauswahl.</li>
            <li>Fotografiere den persönlichen QR-Code möglichst gerade und nah. Falls du dafür die normale Kamera-App verwendest, kehre anschließend zu dieser Seite zurück und wähle das Foto aus.</li>
            <li>Das Foto wird automatisch ausgewertet und deine Bewertung öffnet sich.</li>
          </ol>
          <form id='qr-camera-form' method='post'
                action='/access/{escape(access_token)}/scan'
                enctype='multipart/form-data'>
            <p><label for='session_code_photo'>Sitzungscode</label><br>
            <input id='session_code_photo' name='session_code' inputmode='numeric'
                   pattern='[0-9]{{6}}' maxlength='6' required></p>
            <label class='button' for='qr_image'>Kamera öffnen</label>
            <input id='qr_image' name='qr_image' type='file'
                   accept='image/*' capture='environment' required
                   style='position:absolute;left:-10000px'>
            <button id='qr-submit' class='secondary' disabled>QR auswerten</button>
          </form>
          <p class='muted'>Das Foto wird nur im lokalen Schulnetz ausgewertet
          und nicht gespeichert.</p>
          <hr>
          <p><strong>Falls die Kamera den QR nicht erkennt:</strong> Gib den
          achtstelligen persönlichen Code ein, der unter dem QR steht.</p>
          <form method='post' action='/access/{escape(access_token)}/code'>
            <p><label for='session_code_manual'>Sitzungscode</label><br>
            <input id='session_code_manual' name='session_code' inputmode='numeric'
                   pattern='[0-9]{{6}}' maxlength='6' required></p>
            <label for='personal_code'>Persönlicher Code</label>
            <input id='personal_code' name='personal_code' required
                   minlength='8' maxlength='8' autocomplete='off'
                   autocapitalize='characters'>
            <button>Öffnen</button>
          </form>
        </section>
        <script>
        (() => {{
          const input = document.getElementById('qr_image');
          const form = document.getElementById('qr-camera-form');
          const button = document.getElementById('qr-submit');
          input.addEventListener('change', () => {{
            if (input.files && input.files.length) {{
              button.disabled = false;
              button.textContent = 'QR wird gelesen …';
              setTimeout(() => form.requestSubmit(), 50);
            }}
          }});
        }})();
        </script>"""
        return page("Persönliche QR-Karte scannen", body)

    @app.post("/access/{access_token}/scan", response_class=HTMLResponse)
    async def two_qr_scan(
        access_token: str,
        session_code: str = Form(...),
        qr_image: UploadFile = File(...),
    ):
        session = db.session_by_access_token(access_token)
        if not session:
            raise HTTPException(404, "Sitzung nicht gefunden.")
        if session["phase"] not in {"self", "peer"}:
            raise HTTPException(410, "Bewertung ist nicht geöffnet.")
        if session_code.strip() != str(session["session_code"]):
            return page(
                "Sitzungscode ungültig",
                "<div class='danger'><p>Der Sitzungscode ist ungültig.</p></div>"
                f"<p><a class='button' href='/access/{escape(access_token)}'>Erneut versuchen</a></p>",
            )
        try:
            payload = decode_qr_image(
                await qr_image.read(MAX_QR_IMAGE_BYTES + 1)
            )
        except RuntimeError as exc:
            return page(
                "QR konnte nicht gelesen werden",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        token = student_token_from_qr_payload(payload or "")
        student = db.student_by_token(token or "")
        if not student or not db.student_in_session(session["id"], student["id"]):
            return page(
                "QR konnte nicht gelesen werden",
                "<div class='danger'><p>Keine gültige persönliche QR-Karte dieser "
                "Klasse erkannt. Bitte die Karte näher und gerade "
                "fotografieren.</p></div>"
                f"<p><a class='button' href='/access/{escape(access_token)}'>"
                "Erneut versuchen</a></p>",
            )
        return redirect(f"/s/{quote(str(student['token']))}?session_code={session['session_code']}")

    @app.post("/access/{access_token}/code", response_class=HTMLResponse)
    def two_qr_code(
        access_token: str,
        session_code: str = Form(...),
        personal_code: str = Form(...),
    ):
        session = db.session_by_access_token(access_token)
        if not session:
            raise HTTPException(404, "Sitzung nicht gefunden.")
        if session["phase"] not in {"self", "peer"}:
            raise HTTPException(410, "Bewertung ist nicht geöffnet.")
        if session_code.strip() != str(session["session_code"]):
            return page(
                "Sitzungscode ungültig",
                "<div class='danger'><p>Der Sitzungscode ist ungültig.</p></div>"
                f"<p><a class='button' href='/access/{escape(access_token)}'>Erneut versuchen</a></p>",
            )
        token = db.identities.token_by_short_code(personal_code)
        student = db.student_by_token(token or "")
        if not student or not db.student_in_session(session["id"], student["id"]):
            return page(
                "Code ungültig",
                "<div class='danger'><p>Der persönliche Code gehört nicht zu "
                "dieser Klasse oder ist ungültig.</p></div>"
                f"<p><a class='button' href='/access/{escape(access_token)}'>"
                "Erneut versuchen</a></p>",
            )
        return redirect(f"/s/{quote(str(student['token']))}?session_code={session['session_code']}")

    @app.post("/admin/session/{session_id}/assign")
    def assign(session_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session or session["phase"] not in {"setup", "self", "self_closed"}:
            return page("Gesperrt", "<div class='danger'><p>Die Zuordnung ist ab Beginn der Peerbewertung gesperrt.</p></div>")
        ids = [int(row["student_id"]) for row in db.roster(session_id)]
        try:
            db.save_assignments(
                session_id,
                generate_derangement(
                    ids,
                    excluded_pairs=db.exclusion_pairs(session_id),
                ),
            )
        except Exception as exc:
            return page("Fehler", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        return redirect(f"/admin/session/{session_id}")

    @app.post("/admin/session/{session_id}/swap")
    def swap(
        session_id: int,
        reviewer_a: int = Form(...),
        reviewer_b: int = Form(...),
        _: str = Depends(admin),
    ):
        session = db.session(session_id)
        if not session or session["phase"] not in {"setup", "self", "self_closed"}:
            return page("Gesperrt", "<div class='danger'><p>Die Zuordnung ist ab Beginn der Peerbewertung gesperrt.</p></div>")
        first = db.roster_student_by_position(session_id, reviewer_a)
        second = db.roster_student_by_position(session_id, reviewer_b)
        mapping = db.assignment_mapping(session_id)
        if not first or not second or not mapping:
            return page("Tausch nicht möglich", "<div class='danger'><p>Listennummer oder Zuordnung fehlt.</p></div>")
        try:
            changed = swap_subjects(
                mapping,
                int(first["student_id"]),
                int(second["student_id"]),
                db.exclusion_pairs(session_id),
            )
            db.save_assignments(session_id, changed)
        except ValueError as exc:
            return page("Tausch nicht möglich", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        return redirect(f"/admin/session/{session_id}")

    @app.post("/admin/session/{session_id}/exclusion")
    def add_exclusion(
        session_id: int,
        student_a_no: int = Form(...),
        student_b_no: int = Form(...),
        _: str = Depends(admin),
    ):
        try:
            db.add_exclusion(session_id, student_a_no, student_b_no)
        except ValueError as exc:
            return page(
                "Ausschluss nicht möglich",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        return redirect(f"/admin/session/{session_id}")

    @app.post("/admin/session/{session_id}/exclusion/remove")
    def remove_exclusion(
        session_id: int,
        student_a_id: int = Form(...),
        student_b_id: int = Form(...),
        _: str = Depends(admin),
    ):
        try:
            db.remove_exclusion(session_id, student_a_id, student_b_id)
        except ValueError as exc:
            return page(
                "Ausschluss nicht entfernt",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        return redirect(f"/admin/session/{session_id}")

    @app.post("/admin/session/{session_id}/phase")
    def phase(session_id: int, phase: str = Form(...), _: str = Depends(admin)):
        current = db.session(session_id)
        if not current:
            raise HTTPException(404)
        if phase == current["phase"]:
            return redirect(f"/admin/session/{session_id}")
        roster = db.roster(session_id)
        has_assignment = len(db.assignment_mapping(session_id)) == len(roster)
        comparisons = db.comparisons(session_id)
        teacher_count = sum(bool(row["teacher_submitted_at"]) for row in comparisons)
        teacher_ratings_complete = bool(roster) and teacher_count == len(roster)
        if phase == "teacher_closed" and not teacher_ratings_complete:
            return page(
                "Lehrerbewertung noch nicht vollständig",
                "<div class='warning'><h1>Lehrerbewertung noch nicht vollständig</h1>"
                f"<p><strong>{teacher_count} von {len(roster)} Personen bewertet.</strong></p>"
                "<p>Die Phase bleibt geöffnet. Bereits gespeicherte Lehrerbewertungen bleiben erhalten.</p></div>"
                f"<p><a class='button' href='/admin/session/{session_id}/review'>Zur Lehrerprüfung</a></p>",
            )
        try:
            validate_transition(
                current["phase"],
                phase,
                has_complete_assignment=has_assignment,
                teacher_review_opened=bool(current["teacher_review_opened"]),
                teacher_ratings_complete=teacher_ratings_complete,
            )
        except WorkflowError as exc:
            return page(
                "Phasenwechsel nicht möglich",
                f"<div class='danger'><p>{escape(str(exc))}</p></div>",
            )
        db.set_phase(session_id, phase)
        return redirect(f"/admin/session/{session_id}")

    @app.get("/s/{token}", response_class=HTMLResponse)
    def student_home(token: str, session_code: str = ""):
        student = db.student_by_token(token)
        if not student:
            raise HTTPException(404)
        session = db.student_session_by_code(student["class_id"], session_code.strip())
        if not session:
            return page("Sitzungscode ungültig", "<div class='card'><h1>Der Sitzungscode ist ungültig oder die Bewertung ist nicht geöffnet.</h1></div>")
        if session["phase"] == "setup":
            return page(
                "Warten auf Selbstbewertung",
                "<div class='card'><h1>Du bist angemeldet.</h1>"
                "<p>Die Selbstbewertung wurde noch nicht geöffnet. Diese Seite kann geöffnet bleiben; sie wechselt anschließend automatisch zur Bewertung.</p></div>"
                f"<script>(()=>{{const check=async()=>{{try{{const r=await fetch('/s/{quote(token)}/phase-state?session_code={quote(session_code)}&t='+Date.now(),{{cache:'no-store'}});"
                f"if(r.ok){{const d=await r.json();if(d.phase==='self')window.location.replace('/s/{quote(token)}?session_code={quote(session_code)}&t='+Date.now());}}}}catch(_){{}}}};check();setInterval(check,2000);}})();</script>",
            )
        if session["phase"] == "self":
            existing = db.rating(session["id"], student["id"], "self")
            if existing:
                return page(
                    "Selbstbewertung abgegeben",
                    "<div class='card'><h1>Deine Selbstbewertung ist gespeichert.</h1>"
                    "<p>Diese Seite kann geöffnet bleiben. Sobald die Lehrkraft die Peerbewertung öffnet, erscheint sie automatisch.</p>"
                    "<p class='muted'>Warte auf die Freigabe durch die Lehrkraft.</p></div>"
                    f"<script>(()=>{{const check=async()=>{{try{{const r=await fetch('/s/{quote(token)}/phase-state?session_code={quote(session_code)}&t='+Date.now(),{{cache:'no-store'}});"
                    f"if(r.ok){{const d=await r.json();if(d.phase==='peer')window.location.replace('/s/{quote(token)}?session_code={quote(session_code)}&t='+Date.now());}}}}catch(_){{}}}};check();setInterval(check,2000);}})();</script>",
                )
            body = (
                f"<div class='card'><h1>Selbstbewertung</h1><p><strong>{escape(student['name'])}</strong></p>"
                "<p>Bewerte den aktuellen Zustand deines Hefters. Nach dem verbindlichen Absenden darf der Hefter bis zum Abschluss der Bewertung nicht mehr verändert werden.</p>"
                + rating_form(criteria, f"/s/{quote(token)}/self?session_code={quote(session_code)}")
                + "</div>"
            )
            return page("Selbstbewertung", body)
        if session["phase"] == "self_closed":
            return page(
                "Warten auf Peerbewertung",
                "<div class='card'><h1>Die Selbstbewertung ist abgeschlossen.</h1>"
                "<p>Bitte diese Seite geöffnet lassen. Die Peerbewertung erscheint automatisch, sobald die Lehrkraft sie freigibt.</p></div>"
                f"<script>(()=>{{const check=async()=>{{try{{const r=await fetch('/s/{quote(token)}/phase-state?session_code={quote(session_code)}&t='+Date.now(),{{cache:'no-store'}});"
                f"if(r.ok){{const d=await r.json();if(d.phase==='peer')window.location.replace('/s/{quote(token)}?session_code={quote(session_code)}&t='+Date.now());}}}}catch(_){{}}}};check();setInterval(check,2000);}})();</script>",
            )
        assignment = db.assignment_for(session["id"], student["id"])
        if not assignment:
            return page("Keine Zuordnung", "<div class='danger'><h1>Noch keine Peerzuordnung vorhanden.</h1></div>")
        existing = db.rating(session["id"], assignment["subject_id"], "peer")
        if existing:
            return page("Abgegeben", "<div class='notice'><h1>Deine Peerbewertung ist gespeichert und gesperrt.</h1><p>Die Seite kann nun geschlossen werden.</p></div>")
        body = (
            f"<div class='card'><h1>Peerbewertung</h1>"
            f"<p>Du bewertest den Hefter von <strong>Nr. {assignment['subject_no']} · {escape(assignment['subject_name'])}</strong>.</p>"
            "<p>Die Selbstbewertung dieser Person ist für dich nicht sichtbar.</p>"
            + rating_form(criteria, f"/s/{quote(token)}/peer?session_code={quote(session_code)}")
            + "</div>"
        )
        return page("Peerbewertung", body)

    @app.get("/s/{token}/phase-state")
    def student_phase_state(token: str, session_code: str = ""):
        student = db.student_by_token(token)
        if not student:
            raise HTTPException(404)
        session = db.student_session_by_code(student["class_id"], session_code.strip())
        if not session:
            return JSONResponse({"phase": "closed"})
        return JSONResponse({"phase": str(session["phase"])})

    @app.get("/anzeige", response_class=HTMLResponse)
    def classroom_display(session_code: str = ""):
        session = db.active_session_by_code(session_code)
        if not session:
            error = "<div class='danger'><p>Keine laufende Bewertung mit diesem Code gefunden.</p></div>" if session_code else ""
            return page("Präsentationsansicht", f"""
              <section class='card' style='max-width:560px;margin:32px auto'>
                <p class='eyebrow'>HB-Collector · Klassenraum</p><h1>Bewertung anzeigen</h1>{error}
                <form method='get' action='/anzeige'>
                  <label>Sitzungscode<br><input name='session_code' inputmode='numeric' pattern='[0-9]{{6}}' maxlength='6' required autofocus></label>
                  <p><button>Anzeigen</button></p>
                </form>
              </section>""")
        progress = db.public_progress(session["id"])
        if session["phase"] in {"setup", "self", "self_closed"}:
            submitted, label = progress["self"], "Selbstbewertungen"
        elif session["phase"] in {"peer", "peer_closed"}:
            submitted, label = progress["peer"], "Peerbewertungen"
        else:
            submitted, label = progress["total"], "Schülerbewertungen abgeschlossen"
        return page("Präsentationsansicht", f"""
          <section class='card' style='max-width:760px;margin:32px auto;text-align:center'>
            <p class='eyebrow'>HB-Collector · Klassenraum</p>
            <h1>Sitzungscode {escape(session['session_code'])}</h1>
            <p class='session-code'>{submitted} / {progress['total']}</p><p>{escape(label)}</p>
            <p class='muted'>Diese Seite zeigt absichtlich keine Namen, Punkte oder Noten.</p>
          </section><script>setTimeout(()=>location.reload(),3000)</script>""")

    @app.get("/p/{token}", response_class=HTMLResponse)
    def universal_student_home(token: str):
        if not db.student_by_token(token):
            raise HTTPException(404)
        return page("Sitzungscode", f"""
        <section class='card' style='max-width:520px;margin:30px auto'>
          <h1>Hefterbewertung</h1><p>Gib den sechsstelligen Sitzungscode ein, der im Klassenraum angezeigt wird.</p>
          <form class='student-access-form' method='post' action='/p/{quote(token)}'>
            <label>Sitzungscode<br><input name='session_code' inputmode='numeric' pattern='[0-9]{{6}}' maxlength='6' required autofocus></label>
            <button>Bewertung öffnen</button>
          </form></section>""")

    @app.post("/p/{token}")
    def universal_student_code(token: str, session_code: str = Form(...)):
        student = db.student_by_token(token)
        if not student or not db.active_session_for_student(student["class_id"], session_code.strip()):
            return page("Code ungültig", "<div class='danger'><p>Der Sitzungscode ist ungültig oder die Bewertung ist nicht geöffnet.</p></div>")
        return redirect(f"/s/{quote(token)}?session_code={quote(session_code.strip())}")

    async def submitted_values(request: Request) -> dict[str, int]:
        form = await request.form()
        return parse_rating(form, criterion_ids)

    @app.post("/s/{token}/self")
    async def submit_self(token: str, request: Request, session_code: str = ""):
        student = db.student_by_token(token)
        if not student:
            raise HTTPException(404)
        session = db.active_session_for_student(student["class_id"], session_code.strip())
        if not session or session["phase"] != "self":
            raise HTTPException(409, "Selbstbewertung ist nicht geöffnet.")
        if db.rating(session["id"], student["id"], "self"):
            raise HTTPException(409, "Bereits abgegeben.")
        try:
            values = await submitted_values(request)
        except ValueError as exc:
            return page("Unvollständig", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        db.save_rating(session["id"], student["id"], student["id"], "self", values)
        return redirect(f"/s/{quote(token)}?session_code={quote(session_code)}")

    @app.post("/s/{token}/peer")
    async def submit_peer(token: str, request: Request, session_code: str = ""):
        student = db.student_by_token(token)
        if not student:
            raise HTTPException(404)
        session = db.active_session_for_student(student["class_id"], session_code.strip())
        if not session or session["phase"] != "peer":
            raise HTTPException(409, "Peerbewertung ist nicht geöffnet.")
        assignment = db.assignment_for(session["id"], student["id"])
        if not assignment or db.rating(session["id"], assignment["subject_id"], "peer"):
            raise HTTPException(409, "Keine offene Peerbewertung.")
        try:
            values = await submitted_values(request)
        except ValueError as exc:
            return page("Unvollständig", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        db.save_rating(session["id"], assignment["subject_id"], student["id"], "peer", values)
        return redirect(f"/s/{quote(token)}?session_code={quote(session_code)}")

    @app.get("/admin/session/{session_id}/review", response_class=HTMLResponse)
    def review(session_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        if session["phase"] == "teacher":
            db.mark_teacher_review_opened(session_id)
        rows = []
        maximum = len(criterion_ids) * 4
        for row in db.comparisons(session_id):
            self_values = json.loads(row["self_values"]) if row["self_values"] else None
            peer_values = json.loads(row["peer_values"]) if row["peer_values"] else None
            if self_values and peer_values:
                delta = rating_difference(self_values, peer_values, criterion_ids)
                css = difference_level(delta)
                delta_text = str(delta)
            else:
                css = "bad"
                delta_text = "unvollständig"
            if session["phase"] == "closed" and row["teacher_values"]:
                status_text = "abgeschlossen"
            else:
                status_text = "gespeichert" if row["teacher_values"] else "offen"
            if row["teacher_total"] is None:
                teacher_points = teacher_percent = teacher_grade = "–"
            else:
                percent = int(row["teacher_total"]) / maximum * 100
                teacher_points = str(row["teacher_total"])
                teacher_percent = format_percent(percent)
                teacher_grade = str(grade_for_percent(percent))
            exact = bool(self_values and peer_values and all(self_values.get(cid) == peer_values.get(cid) for cid in criterion_ids))
            quick = (
                f"<form method='post' action='/admin/session/{session_id}/review/{row['student_id']}/confirm'>"
                "<button class='small'>Übereinstimmung übernehmen</button></form>"
                if exact and not row["teacher_values"] and session["phase"] == "teacher"
                else ""
            )
            rows.append(
                f"<tr class='{css}'><td>{row['list_position']}</td><td>{escape(row['name'])}</td>"
                f"<td>{row['self_total'] if row['self_total'] is not None else '–'}</td>"
                f"<td>{row['peer_total'] if row['peer_total'] is not None else '–'}</td>"
                f"<td>{delta_text}</td><td>{teacher_points}</td><td>{teacher_percent}</td><td>{teacher_grade}</td>"
                f"<td>{status_text}</td><td>{quick}<a class='button small' href='/admin/session/{session_id}/review/{row['student_id']}'>Prüfen</a></td></tr>"
            )
        body = f"""
        <p><a href='/admin/session/{session_id}'>← Sitzungssteuerung</a></p>
        <h1>Lehrerprüfung · {escape(session['class_id'])}</h1>
        <p class='notice'>Grün: geringe Abweichung. Gelb: gezielte Prüfung. Rot: fehlende oder größere Abweichung.
        Die Farben sind nur eine Prüfreihenfolge und erzeugen keine Note.</p>
        <table><thead><tr><th rowspan='2'>Nr.</th><th rowspan='2'>Name</th><th rowspan='2'>Selbst</th><th rowspan='2'>Peer</th>
        <th rowspan='2'>Abweichung</th><th colspan='3'>Lehrerbewertung</th><th rowspan='2'>Status</th><th rowspan='2'></th></tr>
        <tr><th>Punkte</th><th>Prozent</th><th>Note</th></tr></thead>
        {''.join(rows)}</table>
        <div class='save-actions'>
          <a class='button' href='/admin/session/{session_id}#workflow'>Weiter</a>
        </div>"""
        return page("Lehrerprüfung", body)

    @app.get("/admin/session/{session_id}/review/{student_id}", response_class=HTMLResponse)
    def review_student(session_id: int, student_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        if session["phase"] == "teacher":
            db.mark_teacher_review_opened(session_id)
        comparison_rows = list(db.comparisons(session_id))
        row_index = next((index for index, item in enumerate(comparison_rows) if item["student_id"] == student_id), None)
        row = comparison_rows[row_index] if row_index is not None else None
        if not row:
            raise HTTPException(404)
        previous_id = comparison_rows[row_index - 1]["student_id"] if row_index and row_index > 0 else None
        next_id = comparison_rows[row_index + 1]["student_id"] if row_index is not None and row_index + 1 < len(comparison_rows) else None
        previous_link = (
            f"<a class='button small' href='/admin/session/{session_id}/review/{previous_id}'>← Vorherige</a>"
            if previous_id is not None else "<span class='disabled'>← Vorherige</span>"
        )
        next_link = (
            f"<a class='button small' href='/admin/session/{session_id}/review/{next_id}'>Nächste →</a>"
            if next_id is not None else "<span class='disabled'>Nächste →</span>"
        )
        navigation = (
            f"<div class='review-nav'>{previous_link}"
            f"<a class='button small' href='/admin/session/{session_id}/review'>Prüfliste</a>"
            f"{next_link}</div>"
        )
        self_values = json.loads(row["self_values"]) if row["self_values"] else {}
        peer_values = json.loads(row["peer_values"]) if row["peer_values"] else {}
        teacher_values = json.loads(row["teacher_values"]) if row["teacher_values"] else {}
        if session["phase"] == "closed":
            status_label = "Lehrerbewertung abgeschlossen"
            status_class = "status-saved"
        elif teacher_values:
            status_label = "Lehrerbewertung gespeichert"
            status_class = "status-saved"
        else:
            status_label = "Lehrerbewertung noch nicht gespeichert"
            status_class = "status-open"
        # Die Selbstbewertung dient als zeitsparender Arbeitsvorschlag.
        # Die Lehrkraft prüft und ändert nur abweichende Einzelurteile.
        prefill = teacher_values or self_values or peer_values
        compare_rows = []
        for number, item in enumerate(criteria["criteria"], start=1):
            cid = str(item["id"])
            differs = cid in self_values and cid in peer_values and self_values.get(cid) != peer_values.get(cid)
            scale_points = []
            for value in range(1, 5):
                checked = " checked" if int(prefill.get(cid, 0) or 0) == value else ""
                marker_items = []
                if int(self_values.get(cid, 0) or 0) == value:
                    marker_items.append("<span class='marker marker-self' title='Selbstbewertung'>S</span>")
                if int(peer_values.get(cid, 0) or 0) == value:
                    marker_items.append("<span class='marker marker-peer' title='Peerbewertung'>P</span>")
                markers = "<span class='marker-separator'>·</span>".join(marker_items)
                point_class = "scale-point peer-diff" if differs and int(peer_values.get(cid, 0) or 0) == value else "scale-point"
                scale_points.append(
                    f"<label class='{point_class}'><input required type='radio' name='c_{escape(cid)}' value='{value}'{checked}>"
                    f"<span class='scale-number'>{value}</span><span class='markers'>{markers}</span></label>"
                )
            compare_rows.append(
                f"<tr class='{'disagreement' if differs else ''}'><td>{number}. {escape(item['label'])}</td>"
                f"<td><div class='scale-line'>{''.join(scale_points)}</div></td></tr>"
            )
        if session["phase"] == "closed":
            closed_rows = []
            for number, item in enumerate(criteria["criteria"], start=1):
                cid = str(item["id"])
                closed_rows.append(
                    f"<tr><td>{number}. {escape(item['label'])}</td><td>{self_values.get(cid,'–')}</td>"
                    f"<td>{peer_values.get(cid,'–')}</td><td>{'=' if self_values.get(cid)==peer_values.get(cid) and cid in self_values else '≠'}</td>"
                    f"<td>{teacher_values.get(cid,'–')}</td></tr>"
                )
            assessment = (
                "<p class='notice'>Die Bewertung ist abgeschlossen und nicht mehr veränderbar.</p>"
                f"<table><tr><th>Kriterium</th><th>Selbst</th><th>Peer</th><th></th><th>Lehrkraft</th></tr>{''.join(closed_rows)}</table>"
                f"<div class='review-footer'>{navigation}</div>"
            )
        else:
            continue_button = (
                f"<button name='continue_to' value='{next_id}'>Speichern und weiter</button>"
                if next_id is not None else ""
            )
            save_label = "Änderungen speichern" if teacher_values else "Speichern"
            assessment = (
                f"<form method='post' action='/admin/session/{session_id}/review/{student_id}'>"
                "<div class='matrix-legend'>"
                "<span><span class='marker marker-self'>S</span>Selbstbewertung</span>"
                "<span><span class='marker marker-peer'>P</span>Peerbewertung</span>"
                "<span class='matrix-help'>Der ausgewählte Kreis ist die verbindliche Lehrerbewertung. Gelb markiert nur Abweichungen.</span>"
                "</div>"
                f"<table class='rating-matrix'><tr><th>Kriterium</th><th>Gemeinsame Skala 1–4</th></tr>"
                f"{''.join(compare_rows)}</table><div class='review-footer'>{navigation}"
                f"<div class='save-actions'><button>{save_label}</button>{continue_button}</div>"
                "</div></form>"
            )
        body = f"""
        <p><a href='/admin/session/{session_id}'>← Sitzungssteuerung</a></p>
        <div class='title-with-status'>
          <h1>Nr. {row['list_position']} · {escape(row['name'])}</h1>
          <span class='pill {status_class}'>{status_label}</span>
        </div>
        {assessment}
        """
        return page("Einzelprüfung", body)

    @app.post("/admin/session/{session_id}/review/{student_id}")
    async def save_teacher(session_id: int, student_id: int, request: Request, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session or session["phase"] != "teacher":
            return page("Gesperrt", "<div class='danger'><p>Die Lehrerbewertung ist nicht geöffnet oder bereits abgeschlossen.</p></div>")
        try:
            form = await request.form()
            values = parse_rating(form, criterion_ids)
        except ValueError as exc:
            return page("Unvollständig", f"<div class='danger'><p>{escape(str(exc))}</p></div>")
        db.save_rating(session_id, student_id, None, "teacher", values)
        raw_continue = form.get("continue_to")
        if raw_continue:
            try:
                continue_to = int(raw_continue)
            except (TypeError, ValueError):
                continue_to = None
            if continue_to is not None and any(
                int(item["student_id"]) == continue_to for item in db.comparisons(session_id)
            ):
                return redirect(f"/admin/session/{session_id}/review/{continue_to}")
        return redirect(f"/admin/session/{session_id}/review")

    @app.post("/admin/session/{session_id}/review/{student_id}/confirm")
    def confirm_agreement(session_id: int, student_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session or session["phase"] != "teacher":
            return page("Gesperrt", "<div class='danger'><p>Die Lehrerbewertung ist nicht geöffnet oder bereits abgeschlossen.</p></div>")
        self_rating = db.rating(session_id, student_id, "self")
        peer_rating = db.rating(session_id, student_id, "peer")
        if not self_rating or not peer_rating:
            return page("Nicht möglich", "<div class='danger'><p>Beide Schülerbewertungen müssen vorliegen.</p></div>")
        self_values = json.loads(self_rating["values_json"])
        peer_values = json.loads(peer_rating["values_json"])
        if any(self_values.get(cid) != peer_values.get(cid) for cid in criterion_ids):
            return page("Nicht möglich", "<div class='danger'><p>Die Einzelwerte stimmen nicht vollständig überein.</p></div>")
        db.save_rating(session_id, student_id, None, "teacher", self_values)
        return redirect(f"/admin/session/{session_id}/review")

    @app.get("/admin/session/{session_id}/feedback.pdf")
    def feedback_pdf(session_id: int, _: str = Depends(admin)):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        if session["phase"] not in {"teacher_closed", "closed"}:
            return page(
                "Rückmeldebögen noch nicht möglich",
                "<div class='danger'><p>Die verbindliche Lehrerbewertung muss "
                "zuerst abgeschlossen sein.</p></div>",
            )
        filename = (
            f"Rueckmeldungen_HB_{safe_filename(str(session['class_id']))}_"
            f"{session_id}.pdf"
        )
        output_path = app_work_dir / filename
        try:
            generate_feedback_pdf(
                [dict(row) for row in db.comparisons(session_id)],
                list(criteria["criteria"]),
                {**dict(session), **read_document_parameters(app_work_dir / "Hefterbewertung.ods")},
                ROOT / "templates" / "IB_Hefterbewertung.odt",
                output_path,
            )
        except Exception as exc:
            return page(
                "Rückmeldebögen fehlgeschlagen",
                "<div class='danger'><h1>PDF wurde nicht erzeugt</h1>"
                f"<p>{escape(str(exc))}</p></div>",
            )
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=filename,
        )

    @app.post("/admin/session/{session_id}/export-ods")
    def export_ods(
        session_id: int,
        _: str = Depends(admin),
    ):
        session = db.session(session_id)
        if not session:
            raise HTTPException(404)
        if session["phase"] not in {"teacher_closed", "closed"}:
            return page(
                "Übernahme noch nicht möglich",
                "<div class='danger'><p>Die verbindliche Lehrerbewertung muss "
                "zuerst abgeschlossen sein.</p></div>",
            )
        try:
            backup = write_hefter_results(
                app_work_dir / "Hefterbewertung.ods",
                [dict(row) for row in db.comparisons(session_id)],
                len(criterion_ids) * 4,
                date.fromisoformat(str(session["created_at"])[:10]),
                str(session["period"]),
                criterion_ids=criterion_ids,
            )
        except Exception as exc:
            return page(
                "Übernahme fehlgeschlagen",
                f"<div class='danger'><h1>Hefterbewertung.ods wurde nicht verändert</h1>"
                f"<p>{escape(str(exc))}</p></div>",
            )
        return page(
            "Übernahme abgeschlossen",
            "<div class='notice'><h1>Ergebnisse übernommen</h1>"
            f"<p>Rohdaten und Auswertung wurden in Hefterbewertung.ods aktualisiert.</p>"
            f"<p>Sicherung: {escape(backup.name)}</p></div>"
            "<p><a class='button secondary' href='/admin/download-ods'>Hefterbewertung.ods herunterladen</a></p>"
            f"<p><a class='button' href='/admin/session/{session_id}'>Zur Bewertung</a></p>",
        )

    return app


def _token_for_student(db: Database, student_id: int) -> str:
    with db.connect() as conn:
        row = conn.execute("SELECT token FROM students WHERE id=?", (student_id,)).fetchone()
    return str(row["token"]) if row else ""
