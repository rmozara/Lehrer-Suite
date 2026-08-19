# QR · QR-Karten 1.0.0

Der QR-Generator erzeugt die gemeinsamen persönlichen QR-Karten für SE- und HB-Collector. Eine Karte gilt für eine Person und ein Schuljahr.

## Vorbereitung

1. Außerhalb des Programmordners einen persönlichen Arbeitsordner für die Klasse wählen. Eine Struktur wie `Schuljahr/Organisation/QR-Karten` ist nur eine Empfehlung.
2. `templates/Namensliste.ods` unter demselben Namen dorthin kopieren.
3. Schuljahr, Klasse, Listenplätze, Namen und eindeutige Schüler-IDs eintragen.

## Start

Linux:

```bash
./run_on_linux.sh
```

Windows: `run_on_windows.bat` doppelklicken.

Beim ersten Start wird das gemeinsame Lehrerpasswort im Browser für den Benutzer `lehrkraft` festgelegt. Ohne diese Ersteinrichtung werden keine Karten erzeugt. Danach den persönlichen Arbeitsordner mit `Namensliste.ods` auswählen, die vorgeschlagene Unterrichtsadresse prüfen und das Karten-PDF erzeugen.

## Ergebnis

Jede Karte enthält:

- Name und Listenplatz
- Klasse und Schuljahr
- persönlichen QR-Code
- persönlichen achtstelligen Ersatzcode

Ein erneuter Import derselben Schüler-ID im selben Schuljahr behält die Identität bei. Ein neues Schuljahr erzeugt eine neue Identität.

## Datenschutz

Das Identitätsregister liegt ausschließlich in `Collector-Daten/identities.sqlite3`. Es darf nicht veröffentlicht oder an unberechtigte Personen weitergegeben werden. QR-Karten enthalten keine Bewertungen.

## Hinweise

- Schüler-IDs müssen innerhalb eines Schuljahres eindeutig und dauerhaft sein.
- Änderungen an Namen oder Listenplätzen erzeugen keine neue Identität, solange Schüler-ID und Schuljahr gleich bleiben.
- Die Karten sollten geschützt aufbewahrt und am Ende ihrer Gültigkeit vernichtet werden.
