# Bewertungsmappe - Kurzanleitung

Diese Dokumentation gehört zur Mappe `Bewertung.ods` und zum Prüfskript `bewertung_pruefen.py`.

Die Mappe ist für eine Beispielklasse / Mittelstufen-Physik aufgebaut. Wenn Blattstruktur, Spalten, Parameterbereiche oder Bewertungslogik geändert werden, müssen Dokumentation und Prüfskript entsprechend angepasst werden.

## Was ist der Zweck?

Die Mappe soll Leistungsdaten übersichtlich sammeln, Abschnittsnoten berechnen, Halbjahres- und Jahresnoten ableiten und auffällige Stellen kontrollierbar machen.

Sie unterscheidet zwischen:

- Eingaben der Lehrkraft, z. B. Namen, Teilnoten, Strichlistenwerte, Kompetenznoten.
- berechneten Zwischenwerten, z. B. gewichtete Mittelwerte.
- gerundeten Noten nach der Notentabelle.
- erteilten Noten als pädagogisch verantwortete Endentscheidung.
- Kontrollwerten, z. B. Tendenzen, Differenzen und Plausibilitätshinweise.

Fehlende Werte werden in der Regel mit `-1` gekennzeichnet.

## Schreibweise in dieser Dokumentation

- Tabellenblätter stehen in Typefont, z. B. `Mündlich`, `Zwischennote`, `Zeugnis`.
- Spalten, Parameter und Variablen stehen ebenfalls in Typefont, z. B. `Mündlich_Block`, `HJ1-Anteil`, `Q3 gesamt`.
- Formeln stehen in eigenen Codeblöcken.

## Typischer Ablauf

1. Mappe öffnen.
2. Namen und laufende Leistungsdaten eintragen.
3. Parameter prüfen, vor allem Gewichte und Switches.
4. Notenblätter ausfüllen bzw. kontrollieren.
5. Zeugnisblatt kontrollieren.
6. Prüfskript starten.
7. Prüfbericht und Kompaktberichte lesen.
8. Erteilte Noten pädagogisch final entscheiden.

## Prüfskript starten

Normale Prüfung:

```bash
python3 bewertung_pruefen.py
```

Mit zusätzlichen Implementations-Testfällen:

```bash
python3 bewertung_pruefen.py --testfaelle
```

Das Skript verändert die Originalmappe nicht. Es erstellt eine temporäre Kopie, lässt LibreOffice die Formeln neu berechnen und prüft diese neu berechnete Kopie.

## Ergebnisdateien

Bei einer Mappe `Bewertung.ods` entstehen typischerweise:

```text
Bewertung_Pruefbericht.txt
Bewertung_Kompaktberichte.txt
```

Der Prüfbericht ist für technische und fachliche Kontrolle gedacht. Die Kompaktberichte geben je Schüler einen kurzen Verlauf für Gespräche und Überblick.

## Wichtig

Das Skript kann rechnerische und formale Plausibilität prüfen. Es kann nicht entscheiden, ob eine pädagogisch eingetragene Note inhaltlich verdient ist. Diese Entscheidung bleibt bei der Lehrkraft.
