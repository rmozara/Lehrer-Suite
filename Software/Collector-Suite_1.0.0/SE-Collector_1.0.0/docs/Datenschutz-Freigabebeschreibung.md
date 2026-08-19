# Kurzbeschreibung für Datenschutz- und IT-Freigabe

## Zweck

Lokale digitale Erfassung der Selbstevaluation zur Mitarbeit im Unterricht. Das Verfahren ersetzt die manuelle Übertragung eines Papierarbeitsblatts.

## Datenarten

- interne Schüler-ID, z. B. `8a-01`
- Name und Listenplatz in der lokalen Datei `Selbstevaluation.ods` und der lokalen Lehreranwendung
- 22 Selbsteinschätzungen mit Werten 0–3
- aus den Antworten in LibreOffice berechnete Gesamtpunktzahl und numerischer Notenwert
- Abgabezeitpunkt

## Datenfluss

1. Laptop stellt den lokalen Webserver im genehmigten WLAN bereit.
2. Schülergerät öffnet das Formular über eine persönliche QR-Karte.
3. Antworten werden direkt an den Laptop übertragen.
4. Speicherung ausschließlich in einer zentralen lokalen SQLite-Datei innerhalb der Programminstallation.
5. Übernahme von Zeitraum, Zeitstempel und q01–q22 in die lokale Datei `Selbstevaluation.ods`.
6. Bereichssummen, Prozent und Note werden durch Formeln in LibreOffice berechnet.
7. Optional werden daraus lokal individuelle, druckfertige SE1-Ausgabeblätter als PDF erzeugt.

Die Lehrkraft wählt beim Programmstart einen Unterrichtsordner. ODS,
Sicherungskopien und PDF-Ausgaben werden ausschließlich dort abgelegt. Die
zentrale Programminstallation und ihre Python-Umgebung werden nicht vervielfacht.

Die Anwendung benötigt für die Erhebung keine Internetverbindung und verwendet keine externen Analyse-, Tracking-, Cloud- oder Formulardienste.

## Pseudonymisierung und Zugriff

- Im QR-Link steht ein zufälliger Token, nicht der Schülername.
- Der Lehrerbereich ist durch HTTP-Basic-Authentifizierung geschützt.
- Die Zuordnung zwischen Token, Schüler-ID und Name liegt nur in der lokalen Datenbank.
- Das Programm protokolliert keine IP-Adressen oder Gerätekennungen.

## Technische und organisatorische Maßnahmen

- schulisch genehmigter, verschlüsselter Arbeitslaptop
- genehmigtes, WPA2/WPA3-gesichertes lokales WLAN bzw. Access Point
- keine Verbindung des privaten Routers mit dem Schul-LAN ohne IT-Freigabe
- Sperrbildschirm und Benutzerpasswort
- automatische lokale Sicherung vor jeder ODS-Aktualisierung
- definierte Sicherungs- und Löschregeln
- erneute Schülerabgabe nur nach Freigabe durch die Lehrkraft
- erste vollständige verbindliche Abgabe gilt

## Löschung

Empfehlung: Rohdaten nach abgeschlossener Notenfeststellung und Ablauf der schulischen Aufbewahrungs- bzw. Widerspruchsfristen löschen oder in den von der Schule vorgesehenen geschützten Speicher überführen. Die konkrete Frist ist schulisch festzulegen.

## Offene Freigabepunkte

- Darf die portable Python-Anwendung auf dem Arbeitsgerät ausgeführt werden?
- Darf ein lokaler Webserver auf Port 8765 erreichbar sein?
- Welcher lokale Router/Access Point ist zugelassen?
- Welcher Speicherort und welche Löschfrist sind verbindlich?

## Zwei-QR-Zugang

Im Zwei-QR-Modus wird ein von der Schülerin oder dem Schüler aktiv aufgenommenes Foto der persönlichen QR-Karte über das lokale WLAN an den Lehrer-Laptop übertragen. Das Bild wird ausschließlich im Arbeitsspeicher zur QR-Erkennung verarbeitet und nicht als Datei gespeichert. Nach der Erkennung wird nur der bereits vorhandene zufällige persönliche Schülerschlüssel weiterverwendet.
