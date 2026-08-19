# Collector-Suite 1.0.0

## Schnellstart: QR → SE → HB

1. **QR:** `Namensliste.ods` vorbereiten, im Browser das gemeinsame Lehrerpasswort einrichten und persönliche QR-Karten erzeugen.
2. **SE:** persönlichen Arbeitsordner wählen, Selbstevaluation durchführen und ODS/PDF-Ergebnisse sichern.
3. **HB:** persönlichen Arbeitsordner wählen, Hefterbewertung durchführen und ODS/PDF-Rückmeldungen sichern.

**Programmordner:** enthält die heruntergeladene Collector-Suite und ihre Vorlagen. Hier keine Unterrichtsdaten ablegen.

**Persönlicher Arbeitsbereich:** liegt außerhalb des Programmordners. Dort organisiert die Lehrkraft Klassen, Unterrichtsreihen und Themen und speichert `Namensliste.ods`, `Selbstevaluation.ods` und `Hefterbewertung.ods`. Die Struktur unter `Beispiel-Durchlauf` ist nur ein Beispiel und keine technische Pflicht.

Die Collector-Suite unterstützt lokale, datensparsame Schülerbewertungen im Unterricht. Sie besteht aus drei eigenständigen Programmen, die eine gemeinsame Schüleridentität verwenden:

- **QR · QR-Karten 1.0.0:** erzeugt die persönlichen QR-Karten für ein Schuljahr.
- **SE · Selbstevaluation 1.0.0:** führt Selbstevaluationen durch und überträgt die Ergebnisse in `Selbstevaluation.ods`.
- **HB · Hefterbewertung 1.0.0:** verbindet Selbst-, Peer- und Lehrerbewertung einer Hefterbewertung.

Im normalen Unterrichtsbetrieb verbleiben alle Daten auf dem Rechner der Lehrkraft; dafür werden keine externen Server oder Cloud-Dienste benötigt.

## Voraussetzungen

- Linux oder Windows
- Python 3.11 oder neuer
- LibreOffice
- ein gemeinsames WLAN für Lehrer- und Schülergeräte

### Erstinstallation und Unterrichtsbetrieb

Beim ersten Start wird im Suite-Ordner automatisch eine gemeinsame Python-Umgebung `.venv` eingerichtet. Die Startskripte installieren darin fehlende Python-Pakete. Für diese Erstinstallation wird deshalb normalerweise Internetzugriff benötigt. In verwalteten Schulnetzen kann alternativ die Schul-IT eine vorbereitete Installation oder eine lokale Paketquelle bereitstellen.

Nach erfolgreicher Installation läuft der normale Unterrichtsbetrieb lokal. SE und HB benötigen keine Cloud-Dienste, aber eine lokale Netzwerkverbindung zwischen Lehrer- und Schülergeräten.

## Empfohlene Reihenfolge

1. Im Ordner `QR-Generator_1.0.0` QR starten.
2. In QR den angezeigten Benutzer `lehrkraft` verwenden, ein gemeinsames Lehrerpasswort festlegen und den persönlichen Arbeitsordner mit der klassenbezogenen `Namensliste.ods` auswählen.
3. Persönliche QR-Karten erzeugen und ausdrucken.
4. Für eine Selbstevaluation `SE-Collector_1.0.0` starten.
5. Für eine Hefterbewertung `HB-Collector_1.0.0` starten.

Eine persönliche QR-Karte gilt innerhalb eines Schuljahres für beide Collectoren. Bei einer geänderten Netzwerkadresse kann der jeweilige Zwei-QR-Ausweichweg verwendet werden.

Für eine **neue Klasse** eine neue `Namensliste.ods` in einem eigenen Arbeitsordner anlegen und neue QR-Karten erzeugen. Für eine **neue Unterrichtsreihe oder ein neues Thema** separate SE- und/oder HB-Arbeitsordner wählen. Die Schüler-IDs der Klasse bleiben dabei unverändert.

## Start

Linux:

```bash
./QR-Generator_1.0.0/run_on_linux.sh
./SE-Collector_1.0.0/run_on_linux.sh
./HB-Collector_1.0.0/run_on_linux.sh
```

Unter Windows die entsprechende Datei `run_on_windows.bat` doppelklicken.

Der abschließende manuelle Release-Durchlauf erfolgte unter Linux. Die Windows-Skripte wurden statisch auf Pfade, Leerzeichen und konsistente Referenzen geprüft.

SE und HB verwenden denselben Unterrichtsport und werden deshalb nacheinander, nicht gleichzeitig, betrieben.

### Sicherheit im lokalen Netzwerk

SE und HB laufen im lokalen Netzwerk über HTTP. Die Lehreroberflächen sind durch HTTP Basic Auth geschützt; ohne HTTPS bietet dieses Verfahren jedoch keine Transportverschlüsselung. Die Suite darf deshalb nur in einem vertrauenswürdigen lokalen Netzwerk eingesetzt werden. Das Lehrerpasswort sollte eigens für diese Suite gewählt und nicht auch für andere wichtige Konten verwendet werden.

Die Schülerzugänge sind für ein lokales Unterrichtsszenario vorgesehen, nicht für den Betrieb im öffentlichen Internet. Port 8765 und die Collector-Oberflächen dürfen nicht ohne zusätzliche, extern eingerichtete Absicherung ins Internet weitergeleitet oder öffentlich exponiert werden.

Am Smartboard ist kein QR-Scanner nötig: Im Browser des Boards wird die auf der Sitzungsseite angegebene Adresse mit `/anzeige` geöffnet und dort der sechsstellige Sitzungscode eingegeben. Diese Präsentationsansicht enthält keine Namen, Punkte oder Noten.

Die Ausgabevorlagen heißen `IB_QR-Karten.odt`, `IB_Selbstbewertung1.odt` und `IB_Hefterbewertung.odt`. Fach, Kürzel und Schulname werden aus dem Blatt `Parameter` der jeweiligen ODS übernommen.

## Datenordner

Die veröffentlichte Rohkopie enthält ausschließlich synthetische Beispieldaten und keine realen Schülerdaten. Personenbezogene Daten entstehen erst bei der lokalen Nutzung durch die Lehrkraft.

`Collector-Daten` enthält nach dem ersten Start das gemeinsame Identitätsregister sowie lokale Einstellungen einschließlich des Passwort-Hashs und der gewählten Netzwerkadresse. Die Ordner `SE-Collector_1.0.0/data` und `HB-Collector_1.0.0/data` enthalten die Sitzungsdatenbanken und Komponenteneinstellungen. Diese Bereiche dürfen nicht veröffentlicht oder zwischen fremden Installationen ausgetauscht werden.

Fachliche Arbeitsdateien, erzeugte PDFs sowie `SE-Collector-Sicherungen` und `HB-Collector-Sicherungen` werden in den beim Start ausgewählten Arbeitsordnern gespeichert. Auch Exporte, QR-Ausgaben, Archive und Sicherungen können personenbezogene Daten enthalten. Sie dürfen nicht in ein öffentliches Repository oder eine öffentliche Distributionskopie übernommen werden.

Die zentrale `.gitignore` bietet zusätzlichen Schutz vor versehentlichen Git-Commits typischer Laufzeitdaten. Sie ersetzt nicht die Prüfung und Verantwortung der Lehrkraft vor einer Veröffentlichung.

## Bearbeitbare Arbeitsdateien

- Programmcode, Konfigurationen und Vorlagen in den Programmordnern sollten nicht unnötig direkt verändert werden. Für Details gelten die READMEs der drei Komponenten.
- Für QR wird die mitgelieferte `templates/Namensliste.ods` unter demselben Dateinamen in den persönlichen Arbeitsordner der Klasse kopiert und dort mit Schuljahr, Klasse, Listenplätzen, Namen und eindeutigen Schüler-IDs gefüllt.
- SE arbeitet mit `Selbstevaluation.ods`. Vorgesehen sind insbesondere die Namensliste und die Angaben im Blatt `Parameter`; beim Start kann die Datei aus der mitgelieferten Vorlage im gewählten Arbeitsordner angelegt werden.
- HB arbeitet entsprechend mit `Hefterbewertung.ods`; vorgesehen sind die Namensliste mit Schüler-IDs sowie Fach, Kürzel und Schulname im Blatt `Parameter`.
- Schüler-IDs müssen innerhalb eines Schuljahres eindeutig sein und über QR, SE und HB unverändert übereinstimmen. Nur so verwenden beide Collectoren dieselbe persönliche QR-Identität.
- Identitätsregister, Sitzungsdatenbanken, lokale Einstellungen, Sicherungen und PDF-Ausgaben werden automatisch erzeugt. Sie sind Laufzeitdaten und gehören nicht zur öffentlichen Rohkopie.

Arbeitsdateien und Ergebnis-PDFs dürfen für die eigene Ablage kopiert werden. Abgeschlossene Sitzungen/Bewertungen können in SE/HB über die Oberfläche archiviert und wiederhergestellt werden. Sicherungen erst löschen, wenn die zugehörigen Ergebnisse geprüft und anderweitig gesichert sind. Programmdateien, `Collector-Daten` und Komponenten-Datenbanken nicht einzeln verschieben oder zwischen fremden Installationen mischen.

## Prüfung und Aktualisierung

- `check_on_linux.sh` beziehungsweise `check_on_windows.bat` prüft Installation, Vorlagen und vorhandene Datenbanken.
- `upgrade_on_linux.sh` beziehungsweise `upgrade_on_windows.bat` übernimmt lokale Daten aus einer älteren Suite in eine neue Installation.

## Ordnerstruktur

```text
Collector-Suite_1.0.0/
├── Collector-Daten/
├── QR-Generator_1.0.0/
├── SE-Collector_1.0.0/
├── HB-Collector_1.0.0/
├── Beispiel-Durchlauf/
└── tests/
```

Jeder Programmordner enthält nur Startdateien, Dokumentation, Programmcode, Konfiguration, Vorlagen und Tests.
