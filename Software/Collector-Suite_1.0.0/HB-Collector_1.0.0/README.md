# HB · Hefterbewertung 1.0.0

Der HB-Collector organisiert eine Hefterbewertung mit drei getrennten Urteilen:

1. Selbstbewertung durch die Person, deren Hefter bewertet wird
2. verdeckte Peerbewertung nach zufälliger Hefterzuordnung
3. verbindliche Lehrerbewertung

Selbst- und Peerbewertung erzeugen keine automatische Endnote. Die Lehrkraft prüft die Einzelurteile und legt die verbindliche Bewertung fest.

## Vorbereitung

1. Außerhalb des Programmordners einen persönlichen Arbeitsordner für Klasse, Unterrichtsreihe oder Thema wählen. Die Ordnerstruktur ist frei wählbar.
2. `Hefterbewertung.ods` dort automatisch beim ersten Start anlegen lassen oder aus `templates` kopieren.
3. Im Blatt `Namensliste` Namen und unveränderte Schüler-IDs aus der klassenbezogenen QR-Namensliste eintragen.
4. Im Blatt `Parameter` Fach, Kürzel und Schulname kontrollieren.
5. HB starten und diesen Arbeitsordner auswählen.

## Start

Linux:

```bash
./run_on_linux.sh
```

Windows: `run_on_windows.bat` doppelklicken.

Die Lehreroberfläche öffnet sich lokal unter `http://127.0.0.1:8765/admin`.

Ist noch kein gemeinsames Lehrerpasswort eingerichtet, zeigt HB stattdessen im Browser den Hinweis, zuerst QR zu starten. HB erzeugt kein eigenes Zufallspasswort.

## Unterrichtsablauf

1. Bewertung anlegen. Die Lernenden können QR-Karte und Sitzungscode bereits vor der Freigabe der Selbstbewertung verwenden und warten anschließend auf einer Zwischenseite.
2. Zufällige Zuordnung erzeugen; ausgeschlossene Paarungen können zuvor festgelegt werden.
3. Die Lernenden scannen ihre persönliche QR-Karte und geben den Sitzungscode ein.
4. Selbstbewertung abschließen und Peerbewertung öffnen.
5. Die geöffnet gebliebene Schülerseite wechselt automatisch zur Peerbewertung.
6. Peerbewertung abschließen und Lehrerprüfung öffnen.
7. Lehrerbewertungen prüfen, speichern und abschließen.
8. Rückmeldebögen erzeugen und `Hefterbewertung.ods` aktualisieren.

## Bewertungskriterien

HB verwendet neun Kriterien zu Beschriftung, Zustand, Struktur, Ablage, Vollständigkeit, Aufgabenbearbeitung, Darstellungen, Lesbarkeit und termingerechter Abgabe. Bewertet wird von 4 „erfüllt“ bis 1 „nicht erfüllt“.

## Ausgaben

- `Hefterbewertung.ods` mit Rohdaten und Auswertung
- A4-Rückmeldebögen mit Selbst-, Peer- und Lehrerwerten
- automatische Sicherungen vor jeder Aktualisierung

## Datenschutz

Bewertungen und Zuordnungen werden ausschließlich lokal gespeichert. Persönliche QR-Identitäten werden aus dem gemeinsamen Ordner `Collector-Daten` gelesen und vom HB-Collector nicht neu erzeugt.

## Hinweise

- Schülergerät und Lehrerrechner müssen sich im selben WLAN befinden.
- VPN sollte während der Bewertung deaktiviert sein.
- Bei geänderter Netzwerkadresse steht der Zwei-QR-Ausweichweg zur Verfügung.
- Die Präsentationsansicht unter der angezeigten Adresse `/anzeige` ist für Smartboards bestimmt und enthält keine personenbezogenen Ergebnisse.
- Vor einer Veröffentlichung dürfen Arbeitsordner, Datenbanken und Sicherungen nicht mitkopiert werden.
