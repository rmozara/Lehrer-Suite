from __future__ import annotations

import hmac
import io
import json
import logging
import re
import threading
from urllib.parse import quote_plus, urlsplit

import qrcode
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import (
    BACKUP_DIR,
    DB_FILE,
    ODS_FILE,
    OUTPUT_DIR,
    ROOT,
    SHARED_IDENTITY_FILE,
    SE1_TEMPLATE_FILE,
    WORKSPACE_ID,
    WORK_DIR,
    VERSION,
    Settings,
    detect_network_addresses,
    hash_password,
    load_form,
    save_admin_password,
    save_direct_base_url,
)
from .core import evaluate, flatten_questions, section_totals
from .db import Database
from .ods_file import apply_parameters_to_form, read_parameters, read_roster, update_raw_data
from .se_output import generate_pdf

logger = logging.getLogger(__name__)
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,160}$")
MAX_QR_IMAGE_BYTES = 25 * 1024 * 1024


def qr_png(payload: str) -> bytes:
    image = qrcode.make(payload)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def student_token_from_qr_payload(payload: str) -> str | None:
    """Extract the student token while deliberately ignoring the QR host.

    Personal cards normally contain a direct URL such as
    http://192.168.50.10:8765/p/<token>.  In two-QR mode only the /p/<token>
    part matters, so old cards remain usable after an address or laptop change.
    """
    value = payload.strip()
    if value.startswith("secollector:student:"):
        candidate = value.removeprefix("secollector:student:")
    else:
        try:
            path = urlsplit(value).path
        except ValueError:
            return None
        match = re.search(r"(?:^|/)p/([A-Za-z0-9_-]{20,160})(?:/|$)", path)
        candidate = match.group(1) if match else ""
    return candidate if TOKEN_RE.fullmatch(candidate) else None


def _decode_qr_candidate(detector, image, cv2) -> str | None:
    """Try normal, multi-code and perspective-corrected decoding."""
    decoded, points, _ = detector.detectAndDecode(image)
    if decoded:
        return decoded

    # A photographed sheet can contain more than one visible code or a lot of
    # surrounding paper. Multi-detection is more tolerant in that situation.
    try:
        ok, decoded_values, _, _ = detector.detectAndDecodeMulti(image)
        if ok:
            for value in decoded_values:
                if value:
                    return value
    except (AttributeError, cv2.error):
        pass

    # If OpenCV can locate the corners but cannot decode the oblique code,
    # rectify it to a large square and try again.
    try:
        detected, corner_points = detector.detect(image)
        if detected and corner_points is not None:
            import numpy as np  # type: ignore

            pts = corner_points.reshape(4, 2).astype(np.float32)
            sums = pts.sum(axis=1)
            diffs = np.diff(pts, axis=1).reshape(-1)
            ordered = np.array(
                [pts[sums.argmin()], pts[diffs.argmin()], pts[sums.argmax()], pts[diffs.argmax()]],
                dtype=np.float32,
            )
            target = np.array([[0, 0], [1199, 0], [1199, 1199], [0, 1199]], dtype=np.float32)
            transform = cv2.getPerspectiveTransform(ordered, target)
            warped = cv2.warpPerspective(image, transform, (1200, 1200), borderValue=(255, 255, 255))
            decoded, _, _ = detector.detectAndDecode(warped)
            if decoded:
                return decoded
    except (ValueError, cv2.error):
        pass
    return None


def decode_qr_image(image_bytes: bytes) -> str | None:
    """Decode a personal QR from a selected phone photo.

    The photo may contain the complete card or parts of the surrounding sheet.
    It is processed only in memory and is never persisted.
    """
    if not image_bytes or len(image_bytes) > MAX_QR_IMAGE_BYTES:
        return None
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover - installation problem
        raise RuntimeError("QR-Bilderkennung ist nicht installiert.") from exc

    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return None

    # Keep enough resolution for a QR photographed on a whole sheet, while
    # bounding CPU and memory use for modern high-resolution phone photos.
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest > 3200:
        scale = 3200 / longest
        image = cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA)

    detector = cv2.QRCodeDetector()
    candidates = [image]

    # A second, smaller candidate often helps when a photo contains a large
    # amount of paper around the code.
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest > 1900:
        scale = 1900 / longest
        candidates.append(
            cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    candidates.append(gray)
    try:
        candidates.append(cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray))
    except cv2.error:
        pass

    for candidate in candidates:
        for rotated in (
            candidate,
            cv2.rotate(candidate, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(candidate, cv2.ROTATE_180),
            cv2.rotate(candidate, cv2.ROTATE_90_COUNTERCLOCKWISE),
        ):
            decoded = _decode_qr_candidate(detector, rotated, cv2)
            if decoded:
                return decoded
    return None


def create_app(initial_settings: Settings) -> FastAPI:
    form = load_form("SE1")
    db = Database(
        DB_FILE,
        WORKSPACE_ID,
        SHARED_IDENTITY_FILE,
        WORK_DIR / "SE-Collector-Sicherungen",
    )
    templates = Jinja2Templates(directory=str(ROOT / "se_collector" / "templates"))
    security = HTTPBasic()
    ods_state: dict = {"roster": None, "error": None}
    settings_state: dict[str, Settings] = {"value": initial_settings}

    app = FastAPI(title="SE-Collector", version=VERSION, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(ROOT / "se_collector" / "static")), name="static")

    def current_settings() -> Settings:
        return settings_state["value"]

    def sync_roster() -> None:
        try:
            roster = read_roster(ODS_FILE)
            parameters = read_parameters(ODS_FILE)
            apply_parameters_to_form(form, parameters)
            db.import_students(roster.students)
            ods_state["roster"] = roster
            ods_state["error"] = None
        except Exception as exc:
            ods_state["roster"] = None
            ods_state["error"] = str(exc)
            logger.warning("Namensliste aus ODS noch nicht bereit: %s", exc)

    sync_roster()

    def admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
        settings = current_settings()
        user_ok = hmac.compare_digest(credentials.username, settings.admin_user)
        password_ok = hmac.compare_digest(hash_password(credentials.password), settings.admin_password_hash)
        if not (user_ok and password_ok):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültige Zugangsdaten",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username

    def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
        values = {"request": request, "version": VERSION, "work_dir": WORK_DIR}
        if context:
            values.update(context)
        return templates.TemplateResponse(request=request, name=name, context=values, status_code=status_code)

    def get_session_or_404(session_id: int):
        session = db.session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sitzung nicht gefunden")
        return session

    def session_access_or_message(request: Request, session_token: str):
        session = db.session_by_public_token(session_token)
        if not session:
            return None, render(request, "message.html", {"title": "Sitzung ungültig", "message": "Diese Sitzung wurde nicht gefunden."}, 404)
        if not session["active"]:
            return None, render(request, "message.html", {"title": "Sitzung geschlossen", "message": "Diese Erhebung ist nicht mehr geöffnet."}, 410)
        return session, None

    def redirect_identified_student(request: Request, session, student_token: str):
        student = db.student_by_token(student_token)
        if not student or not db.student_in_session(session["id"], student["id"]):
            return render(
                request,
                "two_qr.html",
                {
                    "session": session,
                    "error": "Diese persönliche QR-Karte gehört nicht zu dieser Sitzung.",
                },
                403,
            )
        return RedirectResponse(f"/form/{session['public_token']}/{student['public_token']}", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        if not current_settings().admin_password_hash:
            return render(
                request,
                "message.html",
                {
                    "title": "Lehrerpasswort noch nicht eingerichtet",
                    "message": "Bitte zuerst QR starten und dort im Browser für den Benutzer lehrkraft ein gemeinsames Lehrerpasswort festlegen. Danach SE neu starten.",
                },
                503,
            )
        return render(request, "home.html")

    # ----- Direct mode: personal QR -> session code -----
    @app.get("/p/{student_token}", response_class=HTMLResponse)
    def personal_card(request: Request, student_token: str):
        student = db.student_by_token(student_token)
        if not student:
            return render(request, "message.html", {"title": "Karte ungültig", "message": "Diese persönliche QR-Karte ist nicht aktiv."}, 404)
        return render(request, "join.html", {"student": student, "form": form, "error": None})

    @app.post("/p/{student_token}/join")
    def join_personal(request: Request, student_token: str, session_code: str = Form(...)):
        student = db.student_by_token(student_token)
        if not student:
            return render(request, "message.html", {"title": "Karte ungültig", "message": "Diese persönliche QR-Karte ist nicht aktiv."}, 404)
        session = db.active_session_for_student(student["id"], session_code)
        if not session:
            return render(
                request,
                "join.html",
                {"student": student, "form": form, "error": "Sitzungscode ungültig oder Sitzung nicht geöffnet."},
                400,
            )
        return RedirectResponse(f"/form/{session['public_token']}/{student['public_token']}", status_code=303)

    # ----- Two-QR mode: session QR -> photographed personal QR -----
    @app.get("/access/{session_token}", response_class=HTMLResponse)
    def two_qr_page(request: Request, session_token: str):
        session, error_response = session_access_or_message(request, session_token)
        if error_response:
            return error_response
        return render(request, "two_qr.html", {"session": session, "error": None})

    @app.post("/access/{session_token}/scan", response_class=HTMLResponse)
    async def two_qr_scan(
        request: Request,
        session_token: str,
        session_code: str = Form(...),
        qr_image: UploadFile = File(...),
    ):
        session, error_response = session_access_or_message(request, session_token)
        if error_response:
            return error_response
        if session_code.strip() != str(session["session_code"]):
            return render(
                request,
                "two_qr.html",
                {"session": session, "error": "Der Sitzungscode ist ungültig."},
                400,
            )
        try:
            image_bytes = await qr_image.read(MAX_QR_IMAGE_BYTES + 1)
            payload = decode_qr_image(image_bytes)
        except RuntimeError as exc:
            logger.exception("QR-Bilderkennung nicht verfügbar")
            return render(request, "two_qr.html", {"session": session, "error": str(exc)}, 500)
        token = student_token_from_qr_payload(payload or "")
        if not token:
            return render(
                request,
                "two_qr.html",
                {"session": session, "error": "Auf dem Bild wurde keine gültige persönliche QR-Karte erkannt. Bitte näher und gerade fotografieren."},
                400,
            )
        return redirect_identified_student(request, session, token)

    @app.post("/access/{session_token}/code", response_class=HTMLResponse)
    def two_qr_code(
        request: Request,
        session_token: str,
        session_code: str = Form(...),
        personal_code: str = Form(...),
    ):
        session, error_response = session_access_or_message(request, session_token)
        if error_response:
            return error_response
        if session_code.strip() != str(session["session_code"]):
            return render(
                request,
                "two_qr.html",
                {"session": session, "error": "Der Sitzungscode ist ungültig."},
                400,
            )
        token = db.identities.token_by_short_code(personal_code)
        if not token:
            return render(
                request,
                "two_qr.html",
                {
                    "session": session,
                    "error": "Der persönliche Code ist ungültig.",
                },
                400,
            )
        return redirect_identified_student(request, session, token)

    # ----- Unchanged questionnaire and result flow -----
    @app.get("/form/{session_token}/{student_token}", response_class=HTMLResponse)
    def student_form(request: Request, session_token: str, student_token: str):
        session = db.session_by_public_token(session_token)
        student = db.student_by_token(student_token)
        if not session or not student:
            return render(request, "message.html", {"title": "Link ungültig", "message": "Sitzung oder persönliche QR-Karte wurde nicht gefunden."}, 404)
        if not session["active"]:
            return render(request, "message.html", {"title": "Sitzung geschlossen", "message": "Diese Erhebung ist nicht mehr geöffnet."}, 410)
        if not db.student_in_session(session["id"], student["id"]):
            return render(request, "message.html", {"title": "Nicht zugeordnet", "message": "Diese persönliche QR-Karte gehört nicht zur geöffneten Sitzung."}, 403)
        if db.submission_for(session["id"], student["id"]):
            return render(request, "already_submitted.html", {"session": session, "student": student})
        return render(request, "form.html", {"session": session, "student": student, "form": form, "answers": {}, "error": None})

    @app.post("/form/{session_token}/{student_token}", response_class=HTMLResponse)
    async def submit_form(request: Request, session_token: str, student_token: str):
        session = db.session_by_public_token(session_token)
        student = db.student_by_token(student_token)
        if not session or not student:
            return render(request, "message.html", {"title": "Link ungültig", "message": "Sitzung oder persönliche QR-Karte wurde nicht gefunden."}, 404)

        data = await request.form()
        answers = {q["id"]: data.get(q["id"]) for q in flatten_questions(form) if data.get(q["id"]) is not None}
        try:
            normalized, total, grade_label, grade_value, totals = evaluate(form, answers)
            db.save_submission(session["id"], student["id"], normalized, total, grade_label, grade_value)
        except ValueError as exc:
            return render(request, "form.html", {"session": session, "student": student, "form": form, "answers": answers, "error": str(exc)}, 400)
        except Exception:
            logger.exception("Abgabe konnte nicht gespeichert werden")
            return render(
                request,
                "form.html",
                {
                    "session": session,
                    "student": student,
                    "form": form,
                    "answers": answers,
                    "error": "Die Abgabe konnte nicht gespeichert werden. Deine Auswahl bleibt auf diesem Gerät erhalten. Bitte informiere die Lehrkraft.",
                },
                500,
            )
        return render(
            request,
            "done.html",
            {
                "session": session,
                "student": student,
                "form": form,
                "total": total,
                "grade_label": grade_label,
                "grade_value": grade_value,
                "section_totals": totals,
            },
        )

    @app.get("/done/{session_token}/{student_token}", response_class=HTMLResponse)
    def done_page(request: Request, session_token: str, student_token: str):
        session = db.session_by_public_token(session_token)
        student = db.student_by_token(student_token)
        if not session or not student:
            raise HTTPException(status_code=404)
        submission = db.submission_for(session["id"], student["id"])
        if not submission:
            return RedirectResponse(f"/form/{session_token}/{student_token}", status_code=303)
        answers = json.loads(submission["answers_json"])
        return render(
            request,
            "done.html",
            {
                "session": session,
                "student": student,
                "form": form,
                "total": submission["total_points"],
                "grade_label": submission["grade_label"],
                "grade_value": submission["grade_value"],
                "section_totals": section_totals(form, answers),
            },
        )

    @app.get("/status/{public_token}", response_class=HTMLResponse)
    def public_status(request: Request, public_token: str):
        session = db.session_by_public_token(public_token)
        if not session:
            raise HTTPException(status_code=404)
        return render(request, "status.html", {"progress": db.session_progress(session["id"])})

    @app.get("/anzeige", response_class=HTMLResponse)
    def classroom_display(request: Request, session_code: str = ""):
        session = db.active_session_by_code(session_code)
        if not session:
            return render(request, "display.html", {"progress": None, "session_code": session_code, "error": bool(session_code)})
        return render(request, "display.html", {"progress": db.session_progress(session["id"]), "session_code": session_code, "error": False})

    # ----- Teacher administration -----
    @app.get("/admin", response_class=HTMLResponse)
    def admin_home(request: Request, message: str | None = None, _: str = Depends(admin)):
        roster = ods_state.get("roster")
        settings = current_settings()
        preferred_ip = urlsplit(settings.direct_base_url).hostname if settings.direct_base_url else None
        detected_addresses = detect_network_addresses(settings.port, preferred_ip)
        return render(
            request,
            "admin.html",
            {
                "classes": db.classes(),
                "form": form,
                "settings": settings,
                "detected_addresses": detected_addresses,
                "sessions": db.recent_sessions(),
                "archived_sessions": db.recent_sessions(archived=True),
                "message": message,
                "ods_path": ODS_FILE,
                "ods_error": ods_state.get("error"),
                "roster": roster,
            },
        )

    @app.post("/admin/settings/direct-url")
    def set_direct_url(direct_base_url: str = Form(""), _: str = Depends(admin)):
        try:
            settings_state["value"] = save_direct_base_url(direct_base_url)
            message = "Direktmodus deaktiviert." if not direct_base_url.strip() else "Direktadresse gespeichert. Neu erzeugte persönliche QR-Karten verwenden diese Adresse."
        except ValueError as exc:
            message = f"Direktadresse nicht gespeichert: {exc}"
        return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)

    @app.post("/admin/shutdown", response_class=HTMLResponse)
    def shutdown_collector(request: Request, _: str = Depends(admin)):
        server = getattr(request.app.state, "server", None)
        if server is not None:
            threading.Timer(0.5, lambda: setattr(server, "should_exit", True)).start()
        return render(request, "shutdown.html", {})

    @app.post("/admin/settings/password", response_class=HTMLResponse)
    def set_admin_password(
        request: Request,
        current_password: str = Form(...),
        new_password: str = Form(...),
        new_password_repeat: str = Form(...),
        _: str = Depends(admin),
    ):
        settings = current_settings()
        if not hmac.compare_digest(hash_password(current_password), settings.admin_password_hash):
            message = "Das bisherige Passwort ist nicht richtig."
            return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)
        if new_password != new_password_repeat:
            message = "Die beiden Eingaben für das neue Passwort stimmen nicht überein."
            return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)
        if hmac.compare_digest(hash_password(new_password), settings.admin_password_hash):
            message = "Das neue Passwort ist mit dem bisherigen Passwort identisch."
            return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)
        try:
            settings_state["value"] = save_admin_password(new_password)
        except ValueError as exc:
            return RedirectResponse(
                f"/admin?message={quote_plus(f'Passwort nicht geändert: {exc}')}",
                status_code=303,
            )
        return render(
            request,
            "password_changed.html",
            {"admin_user": settings.admin_user},
        )

    @app.post("/admin/sync-ods")
    def sync_ods(_: str = Depends(admin)):
        sync_roster()
        if ods_state.get("error"):
            message = f"Namensliste konnte nicht geladen werden: {ods_state['error']}"
        else:
            roster = ods_state["roster"]
            message = f"{len(roster.students)} SuS aus Selbstevaluation.ods geladen ({roster.class_id})."
        return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)

    @app.post("/admin/session/start")
    def start_session(class_id: str = Form(...), period_id: str = Form(...), _: str = Depends(admin)):
        try:
            session, created = db.start_or_resume_session(class_id, form["form_id"], form["version"], period_id)
        except ValueError as exc:
            return RedirectResponse(f"/admin?message={quote_plus(str(exc))}", status_code=303)
        return RedirectResponse(f"/admin/session/{session['id']}?new={1 if created else 0}", status_code=303)

    @app.get("/admin/session/{session_id}", response_class=HTMLResponse)
    def session_admin(request: Request, session_id: int, new: int | None = None, message: str | None = None, _: str = Depends(admin)):
        get_session_or_404(session_id)
        return render(
            request,
            "session_admin.html",
            {
                "progress": db.session_progress(session_id),
                "students": db.session_students_status(session_id),
                "settings": current_settings(),
                "new": bool(new),
                "message": message,
                "ods_path": ODS_FILE,
            },
        )

    @app.get("/admin/session/{session_id}/live")
    def session_live(session_id: int, _: str = Depends(admin)):
        """Small polling endpoint for the teacher view.

        The page updates counters and the status table without a full page reload,
        so incoming submissions appear reliably and without visible flicker.
        """
        if not db.session_by_id(session_id):
            return JSONResponse(
                {"gone": True, "overview_url": "/admin"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        progress = db.session_progress(session_id)
        students = db.session_students_status(session_id)
        rows_html = templates.env.get_template("session_students_rows.html").render(
            students=students,
            progress=progress,
        )
        return {
            "submitted": progress["submitted"],
            "open": progress["open"],
            "total": progress["total"],
            "rows_html": rows_html,
        }

    @app.post("/admin/session/{session_id}/close")
    def close_session(session_id: int, _: str = Depends(admin)):
        db.close_session(session_id)
        return RedirectResponse("/admin?message=Sitzung+geschlossen.", status_code=303)

    @app.post("/admin/session/{session_id}/reopen")
    def reopen_session(session_id: int, _: str = Depends(admin)):
        db.reopen_session(session_id)
        return RedirectResponse(f"/admin/session/{session_id}?message=Sitzung+erneut+geöffnet.", status_code=303)

    @app.post("/admin/session/{session_id}/reset")
    def reset_session(session_id: int, _: str = Depends(admin)):
        db.reset_session(session_id)
        return RedirectResponse(f"/admin/session/{session_id}?message=Sitzung+geleert+und+neu+geöffnet.", status_code=303)

    @app.post("/admin/session/{session_id}/delete")
    def delete_session(session_id: int, _: str = Depends(admin)):
        try:
            db.delete_session(session_id)
            message = "Archivierte Sitzung endgültig gelöscht."
        except ValueError as exc:
            message = str(exc)
        return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)

    @app.post("/admin/session/{session_id}/archive")
    def archive_session(session_id: int, _: str = Depends(admin)):
        try:
            db.archive_session(session_id)
            message = "Sitzung archiviert."
        except ValueError as exc:
            message = str(exc)
        return RedirectResponse(f"/admin?message={quote_plus(message)}", status_code=303)

    @app.post("/admin/session/{session_id}/restore")
    def restore_session(session_id: int, _: str = Depends(admin)):
        db.restore_session(session_id)
        return RedirectResponse("/admin?message=Sitzung+wiederhergestellt.", status_code=303)

    @app.post("/admin/session/{session_id}/reopen/{student_db_id}")
    def reopen_student(session_id: int, student_db_id: int, _: str = Depends(admin)):
        db.reopen_student(session_id, student_db_id)
        return RedirectResponse(f"/admin/session/{session_id}?message=Erneute+Abgabe+freigegeben.", status_code=303)

    @app.post("/admin/session/{session_id}/write-ods")
    def write_ods(session_id: int, _: str = Depends(admin)):
        session = get_session_or_404(session_id)
        rows = db.summary_export_rows(session_id, [section["id"] for section in form["sections"]])
        try:
            backup = update_raw_data(ODS_FILE, session, rows, form, BACKUP_DIR)
            message = f"Selbstevaluation.ods aktualisiert. Sicherung: {backup.name}"
        except Exception as exc:
            logger.exception("ODS konnte nicht aktualisiert werden")
            message = f"ODS-Aktualisierung fehlgeschlagen: {exc}"
        return RedirectResponse(f"/admin/session/{session_id}?message={quote_plus(message)}", status_code=303)

    @app.post("/admin/session/{session_id}/output-pdf")
    def output_pdf(session_id: int, _: str = Depends(admin)):
        session = get_session_or_404(session_id)
        try:
            rows = db.summary_export_rows(session_id, [section["id"] for section in form["sections"]])
            update_raw_data(ODS_FILE, session, rows, form, BACKUP_DIR)
            safe_class = re.sub(r"[^A-Za-z0-9_-]+", "_", session["class_id"]).strip("_") or "Klasse"
            safe_period = re.sub(r"[^A-Za-z0-9_-]+", "_", session["period_id"]).strip("_") or "Zeitraum"
            output = OUTPUT_DIR / f"Evaluation_SE1_{safe_class}_{safe_period}.pdf"
            count = generate_pdf(ODS_FILE, SE1_TEMPLATE_FILE, output, form)
        except Exception as exc:
            logger.exception("Ausgabeblätter konnten nicht erzeugt werden")
            message = f"Ausgabeblätter konnten nicht erzeugt werden: {exc}"
            return RedirectResponse(f"/admin/session/{session_id}?message={quote_plus(message)}", status_code=303)
        return FileResponse(
            output,
            media_type="application/pdf",
            filename=output.name,
            headers={"X-SE-Sheets": str(count)},
        )

    @app.get("/admin/download-ods")
    def download_ods(_: str = Depends(admin)):
        if not ODS_FILE.exists():
            raise HTTPException(status_code=404, detail="Selbstevaluation.ods fehlt")
        return FileResponse(
            ODS_FILE,
            media_type="application/vnd.oasis.opendocument.spreadsheet",
            filename="Selbstevaluation.ods",
        )

    @app.get("/admin/cards/{class_id}", response_class=HTMLResponse)
    def replacement_card(request: Request, class_id: str, student_token: str | None = None, _: str = Depends(admin)):
        students = db.students_for_class(class_id)
        student = next((item for item in students if item["public_token"] == student_token), None)
        return render(
            request,
            "cards.html",
            {"students": students, "student": student, "settings": current_settings(), "class_id": class_id},
        )

    @app.get("/admin/qr/student/{token}.png")
    def student_qr(token: str, _: str = Depends(admin)):
        student = db.student_by_token(token)
        settings = current_settings()
        if not student:
            raise HTTPException(status_code=404)
        base_url = settings.direct_base_url or settings.base_url
        return Response(qr_png(f"{base_url}/p/{token}"), media_type="image/png")

    @app.get("/admin/qr/wifi.png")
    def wifi_qr(_: str = Depends(admin)):
        settings = current_settings()

        def esc(value: str) -> str:
            return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")

        payload = f"WIFI:T:WPA;S:{esc(settings.wifi_ssid)};P:{esc(settings.wifi_password)};;"
        return Response(qr_png(payload), media_type="image/png")

    @app.get("/admin/qr/session/{session_id}.png")
    def session_qr(session_id: int, _: str = Depends(admin)):
        session = get_session_or_404(session_id)
        settings = current_settings()
        return Response(qr_png(f"{settings.base_url}/access/{session['public_token']}"), media_type="image/png")

    @app.get("/admin/qr/status/{session_id}.png")
    def status_qr(session_id: int, _: str = Depends(admin)):
        session = get_session_or_404(session_id)
        settings = current_settings()
        return Response(qr_png(f"{settings.base_url}/status/{session['public_token']}"), media_type="image/png")

    return app
