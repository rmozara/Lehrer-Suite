from __future__ import annotations

import logging
import threading
import webbrowser

import uvicorn

from hefter_collector.config import WORK_DIR, ensure_settings, ensure_workspace
from hefter_collector.web import create_app
from hefter_collector import VERSION


if __name__ == "__main__":
    workspace_created = ensure_workspace()
    settings, _ = ensure_settings()
    logging.getLogger("uvicorn.access").disabled = True
    print(f"Benutzername:   {settings.admin_user}")
    print("Lehrerpasswort:   gemeinsames Passwort aus QR" if settings.admin_password_hash else
          "Lehrerpasswort:   zuerst in QR einrichten")
    print(f"HB-Collector {VERSION}")
    print(f"Arbeitsordner:    {WORK_DIR}")
    if workspace_created:
        print("Neuer HB-Arbeitsordner wurde eingerichtet.")
    teacher_url = f"http://127.0.0.1:{settings.port}{'/admin' if settings.admin_password_hash else '/'}"
    print(f"Lehreroberfläche: {teacher_url}")
    print(f"Direktadresse:    {settings.direct_base_url or 'noch nicht eingerichtet'}")
    print("Die Lehreroberfläche wird jetzt im Browser geöffnet.")
    threading.Timer(1.2, lambda: webbrowser.open(teacher_url)).start()
    application = create_app(settings)
    server = uvicorn.Server(uvicorn.Config(application, host=settings.host, port=settings.port, access_log=False, log_level="warning"))
    application.state.server = server
    server.run()
