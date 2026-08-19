from __future__ import annotations

import logging
import threading
import webbrowser

import uvicorn

from se_collector.config import VERSION, WORK_DIR, ensure_settings, ensure_workspace
from se_collector.web import create_app


if __name__ == "__main__":
    workspace_created = ensure_workspace()
    settings, _ = ensure_settings()
    logging.getLogger("uvicorn.access").disabled = True
    print(f"Benutzername:   {settings.admin_user}")
    print("Lehrerpasswort:   gemeinsames Passwort aus QR" if settings.admin_password_hash else
          "Lehrerpasswort:   zuerst in QR einrichten")
    print(f"SE-Collector {VERSION}")
    print(f"Arbeitsordner:    {WORK_DIR}")
    if workspace_created:
        print("Neue leere Selbstevaluation.ods wurde im Arbeitsordner angelegt.")
        print("Bitte dort das Blatt 'Namensliste' ausfüllen, speichern und in der Lehreroberfläche neu laden.")
    teacher_url = f"http://127.0.0.1:{settings.port}{'/admin' if settings.admin_password_hash else '/'}"
    print(f"Lehreroberfläche: {teacher_url}")
    print(f"Sitzungsadresse:  {settings.base_url} ({'automatisch' if settings.base_url_mode == 'auto' else 'manuell'})")
    print(f"Direktadresse:    {settings.direct_base_url or 'noch nicht eingerichtet'}")
    print("Die Lehreroberfläche wird jetzt im Browser geöffnet.")
    threading.Timer(1.2, lambda: webbrowser.open(teacher_url)).start()
    application = create_app(settings)
    server = uvicorn.Server(uvicorn.Config(application, host=settings.host, port=settings.port, access_log=False, log_level="warning"))
    application.state.server = server
    server.run()
