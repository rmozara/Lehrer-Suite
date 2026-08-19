---
title: "Bewertungsmappe - Anleitung"
author: ""
date: "2026-07-17"
lang: de
geometry: margin=2.2cm
fontsize: 10pt
toc: true
toc-depth: 2
---

\newpage

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


\newpage

# Bewertungsmodell

Dieses Dokument beschreibt die Bewertungslogik der Mappe. Konkrete Blatt- und Spaltenbezüge stehen in `Tabellenreferenz.md`; die Formeltypen stehen in `Formelreferenz.md`.

## Grundstruktur

Die Mappe arbeitet mit vier Quartalen, zwei Halbjahren und einer Jahresnote:

```text
Q1 + Q2 -> H1
Q3 + Q4 -> H2
H1 + H2 -> Jahresnote
```

Die zentrale Umsetzung erfolgt über die Tabellenblätter `Mündlich`, `Schriftlich`, `Sonstiges`, `Lernraum`, `Zwischennote` und `Zeugnis`.

Dabei gilt:

- `Q1`, `Q2`, `Q3` und `Q4` sind Abschnittsnoten.
- `Q3` ist außerdem Grundlage für den kumulativen Zwischenstand `Stand nach Q3`.
- `H1`, `H2` und `Jahresnote` stehen im Blatt `Zeugnis`.

## Begriffe

Die Mappe verwendet drei Ebenen:

- **Abschnittsnoten**: `Q1`, `Q2`, `Q3`, `Q4`.
- **Zwischenstand**: insbesondere `Stand nach Q3`.
- **Zeugnisnoten**: `H1`, `H2`, `Jahresnote`.

Das Blatt `Zwischennote` enthält also Abschnittsnoten und den Zwischenstand nach `Q3`. Es enthält nicht die eigentlichen Halbjahres- oder Jahresnoten; diese stehen im Blatt `Zeugnis`.

## Q1, Q2 und Q4

Diese Quartale beschreiben jeweils die Leistung im betreffenden Abschnitt. Sie sind Bausteine für Halbjahres- und Jahresnoten.

`Q2` ist rechnerisch ein Baustein für `H1`. Als eigenständige Rückmeldenote ist `Q2` meist weniger wichtig, weil am Ende von `Q2` die Halbjahresnote steht.

`Q4` ist rechnerisch ein Baustein für `H2` und die Jahresnote. Als eigenständige Rückmeldenote ist `Q4` meist weniger wichtig, weil am Ende von `Q4` die Jahresnote steht.

## Q3 und Stand nach Q3

`Q3` hat zwei verschiedene Funktionen:

1. `Q3 gesamt` als Abschnittsnote des dritten Quartals.
2. `Stand nach Q3` als kumulativer Zwischenstand nach `H1` und `Q3`.

Die Abschnittsnote `Q3` darf nicht schon kumulativ sein. Sonst würden frühere Leistungen doppelt eingehen.

Der Stand nach `Q3` wird über den Parameter `HJ1-Anteil` berechnet:

```text
Stand nach Q3 = HJ1-Anteil * H1 + (1 - HJ1-Anteil) * Q3
```

Bei `HJ1-Anteil = 0.667` entspricht das praktisch:

```text
Stand nach Q3 = 2/3 * H1 + 1/3 * Q3
```

Das passt dazu, dass nach `Q3` drei Quartale vergangen sind: zwei Quartale in `H1` und ein Quartal in `H2`.

## H1, H2 und Jahresnote

`H1` ist ein abgeschlossener Block aus `Q1` und `Q2`.

`H2` ist ein abgeschlossener Block aus `Q3` und `Q4`.

Die Jahresnote wird standardmäßig 50/50 aus `H1` und `H2` gebildet:

```text
Jahresnote = 0.5 * H1 + 0.5 * H2
```

Wichtig: Die Bereiche werden nicht alle gleich gebildet.

- Der mündliche Anteil wird aus den mündlichen Quartalswerten gebildet und kann den `Lernraum` als Binnengewicht enthalten.
- Schriftliche Anteile werden aus schriftlichen Blättern wie `LEK` und `Protokoll` gebildet.
- Sonstige Anteile werden aus Blättern wie `Hefter` und `Plakat` gebildet.
- Erst danach werden `Mündlich_Block`, `Schriftlich` und `Sonstiges` zur Halbjahres- bzw. Zeugnisnote zusammengeführt.

Die erteilte Jahresnote bleibt die pädagogisch verantwortete Endentscheidung der Lehrkraft.

## Hauptbereiche der Zwischennote

Die Abschnittsnoten im Blatt `Zwischennote` können aus folgenden Hauptbereichen bestehen:

- `Mündlich`
- `Schriftlich`
- `Sonstiges`

Der `Lernraum` ist in dieser Mappe kein vierter unabhängiger Hauptbereich. Er ist ein Binnenanteil innerhalb des mündlichen Bereichs.

## Lernraum als Binnengewicht

Wenn ein `Lernraum`-Wert vorhanden ist und sein Gewicht größer als `0` ist, wird er innerhalb des mündlichen Blocks berücksichtigt.

Vereinfachte Idee:

```text
Mündlich_Block = (1 - Lernraumgewicht) * Mündlich + Lernraumgewicht * Lernraum
```

Wenn kein `Lernraum`-Wert vorhanden ist, bleibt der mündliche Block einfach die mündliche Note.

Erst danach werden `Mündlich_Block`, `Schriftlich` und `Sonstiges` zur Abschnittsnote bzw. Halbjahresnote kombiniert.

## Umlage und Renormierung

Die Mappe kennt zwei Logiken für fehlende Werte.

### Umlage

Bei `Umlage` wird ein fehlender Anteil gezielt auf einen anderen Bereich gelegt. In den Abschnittsnoten bedeutet das typischerweise: Fehlende Anteile von `Schriftlich` oder `Sonstiges` werden auf den `Mündlich_Block` umgelegt.

Beispiel:

```text
Mündlich = 0.6
Schriftlich = 0.3
Sonstiges = 0.1
Schriftlich fehlt
```

Dann gilt bei `Umlage`:

```text
Mündlich_Block = 0.9
Sonstiges = 0.1
```

### Renormierung

Bei `Renormierung` werden alle vorhandenen Bestandteile proportional neu gewichtet. Das Verhältnis der vorhandenen Gewichte bleibt erhalten.

Mit denselben Ausgangsgewichten und fehlendem `Schriftlich` ergibt sich:

```text
Mündlich_Block = 0.6 / (0.6 + 0.1) = 0.857
Sonstiges = 0.1 / (0.6 + 0.1) = 0.143
```

## Mündliche Bewertung

Die mündliche Bewertung kann aus folgenden Bestandteilen bestehen:

- `Strichliste`
- `Kompetenzbewertung`
- `Selbstevaluation`

Die `Strichliste` wird über Prozentwerte und die Notenzuordnung in eine Note umgewandelt.

Die `Kompetenzbewertung` ist eine fachlich-pädagogische Bewertung der mündlichen Mitarbeit.

Die `Selbstevaluation` ist ein gedämpfter Reflexionsanteil. Sie ist keine freie Selbstbenotung.

## Selbstevaluation

Die `Selbstevaluation` wird mit einer `Referenz` verglichen. Diese Referenz ergibt sich aus `Strichliste` und `Kompetenzbewertung`. Wenn nur einer der beiden Werte vorhanden ist, kann dieser Wert die Referenz bilden. Wenn beide fehlen, gibt es keine Referenz.

Die Selbstevaluation wird über eine Exponentialfunktion gedämpft. Je weiter die Selbstevaluation von der Referenz entfernt ist, desto stärker wird sie in Richtung Referenz gezogen. Der Parameter `Dämpfung` steuert diese Stärke.

Die Selbstevaluation kann die mündliche Note verändern, soll aber nur begrenzt wirken. Die Mappe weist deshalb auch eine Differenz mit und ohne Selbstevaluation aus.

## Rundung

Gerundete Noten werden über die Notentabelle in `Parameter` erzeugt. Die gerundete Note ist die schulisch verwendbare Notenstufe.

Ungerundete Werte dienen der genauen Berechnung und Kontrolle.

An mehreren Stellen verwendet die Mappe bewusst gerundete Werte weiter. Das gilt besonders dann, wenn eine Teilnote bereits als feststehende Teilnote behandelt werden soll. Beispiel: In `Mündlich` verwenden `Q2` und `Q4` für die mündliche Gesamtformel die gerundete Kompetenzbasis, damit Gesamtformel und Referenz ohne Selbstevaluation konsistent sind.

## Tendenzen

Tendenzen werden pädagogisch interpretiert:

```text
Tendenz = alter Notenwert - neuer Notenwert
```

Dadurch gilt:

```text
positiv  = Verbesserung
negativ  = Verschlechterung
0        = keine Veränderung
```

Beispiel:

```text
Q1 = 2.0, Q2 = 3.0 -> Tendenz = -1.0, also Verschlechterung
Q3 = 2.7, Q4 = 2.0 -> Tendenz = +0.7, also Verbesserung
```


\newpage

# Parameter

Dieses Dokument beschreibt die steuerbaren Parameter der Mappe.

## Fehlende Werte

Fehlende Werte werden in der Mappe in der Regel mit `-1` codiert.

Das bedeutet: Der Wert fehlt und soll nicht wie eine echte Note behandelt werden.

## Notenzuordnung `f(P)`

Die Notenzuordnung ordnet Prozentwerte einer schulischen Notenstufe zu.

```text
P >= 98  -> N = 0.7
P >= 92  -> N = 1.0
P >= 90  -> N = 1.3
P >= 87  -> N = 1.7
P >= 78  -> N = 2.0
P >= 75  -> N = 2.3
P >= 72  -> N = 2.7
P >= 63  -> N = 3.0
P >= 60  -> N = 3.3
P >= 57  -> N = 3.7
P >= 48  -> N = 4.0
P >= 45  -> N = 4.3
P >= 42  -> N = 4.7
P >= 30  -> N = 5.0
P >= 27  -> N = 5.3
P >= 24  -> N = 5.7
P >= 3   -> N = 6.0
P < 3    -> N = 6.3
```

Diese Tabelle wird vor allem für Prozentwerte aus Punktzahlen oder Strichlisten verwendet.

## Rundungsstruktur

Die Mappe enthält zusätzlich eine Rundungstabelle für ungerundete Notenwerte. Diese Tabelle bildet ungerundete Werte auf schulische Notenstufen ab.

Typische Formel:

```calc
=IF(Wert=-1;-1;VLOOKUP(Wert;Parameter.$E$5:$F$22;2;1))
```

Diese Rundung wird z. B. für mündliche Gesamtwerte, Kompetenzwerte, Abschnittsnoten, Halbjahresnoten und Jahresnoten verwendet.

## Gewichte

Gewichte legen fest, wie Teilnoten zusammengeführt werden.

Wichtige Gewichtsgruppen:

- `Kompetenzgewichte Mündlich`
- `Gewichte Selbstevaluation`
- `Gewichte Mündlich`
- `Gewichte Schriftlich`
- `Gewichte Sonstiges`
- `Gewichte Zwischennote`
- `Gewichte Halbjahresnote`
- `Gewichte Zeugnis`

Die Summe der Hauptgewichte muss in den relevanten Gruppen `1` ergeben.

## Kompetenzgewichte Mündlich

Diese Gewichte steuern die Berechnung der Kompetenznote im Blatt `Mündlich` und in der ausführlicheren Selbstevaluation von `Q2` und `Q4`.

Aktuelle Struktur:

```text
Quantität       0.4
Qualität        0.3
soz. Kompetenz  0.15
spr. Kompetenz  0.15
```

In `Q1` und `Q3` werden soziale und sprachliche Kompetenz in einer zusammengefassten Kompetenzspalte abgebildet. In `Q2` und `Q4` werden sie getrennt geführt.

## Gewichte Selbstevaluation

Diese Gewichte steuern die Referenzbildung für die Selbstevaluation.

Aktuelle Struktur:

```text
Kompetenz    0.6
Strichliste  0.4
Dämpfung     0.5
```

Die Referenz entsteht aus `Kompetenz` und `Strichliste`, soweit diese Werte vorhanden sind.

Der Parameter `Dämpfung` steuert die exponentielle Dämpfung der Selbstevaluation.

## Gewichte Mündlich

Diese Gewichte steuern die Kombination aus `Strichliste`, `Kompetenz` und `Selbstevaluation` im Blatt `Mündlich`.

Aktuelle Struktur:

```text
Strichliste      0.4
Kompetenz        0.3
Selbstevaluation 0.3
Switch           Renormierung
```

Wenn keine Selbstevaluation vorhanden ist, wird sie nicht wie eine Note behandelt. Die Mappe nutzt dann die vorgesehene Logik für fehlende Bestandteile.

## Gewichte Schriftlich

Diese Gewichte steuern die Kombination von `LEK` und `Protokoll` im Bereich `Schriftlich`.

Aktuelle Struktur:

```text
LEK        0.66667
Protokoll  0.333
```

## Gewichte Sonstiges

Diese Gewichte steuern die Kombination von `Hefter` und `Plakat` im Bereich `Sonstiges`.

Aktuelle Struktur:

```text
Hefter  0.66667
Plakat  0.333
```

## Gewichte Zwischennote

Diese Gewichte steuern die Kombination der Hauptbereiche im Blatt `Zwischennote`:

```text
Mündlich     0.6
Schriftlich  0.3
Sonstiges    0.1
Lernraum     0
HJ1-Anteil   0.667
Switch       Umlage
```

Der `Lernraum` ist hier nicht als vierter Hauptbereich gedacht, sondern als Binnenanteil im mündlichen Bereich.

Der `HJ1-Anteil` gehört nur zur Berechnung von `Stand nach Q3`. Er gehört nicht in die reinen Abschnittsnoten `Q1`, `Q2`, `Q3` oder `Q4`.

Beispiel:

```text
HJ1-Anteil = 0.667
Stand nach Q3 = 0.667 * H1 + 0.333 * Q3
```

## Gewichte Halbjahresnote

Diese Gewichte steuern die Kombination der Quartale innerhalb eines Halbjahres.

Aktuelle Struktur:

```text
Q1/Q3  0.4
Q2/Q4  0.6
```

Das heißt: Der zweite Abschnitt eines Halbjahres kann stärker gewichtet werden als der erste.

## Gewichte Zeugnis

Diese Gewichte steuern die Kombination der Hauptbereiche im Blatt `Zeugnis`.

Aktuelle Struktur:

```text
Mündlich     0.6
Schriftlich  0.3
Sonstiges    0.1
Lernraum     0
Switch       Umlage
```

Auch hier gilt: `Lernraum` ist ein Binnengewicht innerhalb des mündlichen Blocks.

## Switches

Switches steuern den Umgang mit fehlenden Werten.

Zulässige Werte:

```text
Umlage
Renormierung
```

Andere Einträge führen zu Warnungen oder Fehlern im Prüfbericht.

## Änderungen an Parametern

Wenn Parameter verändert werden, sollte anschließend das Prüfskript ausgeführt werden.

Besonders wichtig sind:

- Gewichtssummen
- Switch-Werte
- `HJ1-Anteil`
- `Dämpfung`
- Notenzuordnung und Rundungstabelle


\newpage

# Tabellenreferenz

Dieses Dokument beschreibt die konkrete Struktur der Mappe Blatt für Blatt.

Die Dokumentation ist bewusst modular. Wenn ein Blatt später geändert wird, sollte nur der entsprechende Abschnitt angepasst werden.

## Blatt: `Namensliste`

### Zweck

Das Blatt `Namensliste` enthält die Schülernummern und Schülernamen.

### Weiterverwendung

Andere Blätter übernehmen die Namen aus `Namensliste`, damit Namen nur einmal gepflegt werden müssen.

## Blatt: `Parameter`

### Zweck

Das Blatt `Parameter` enthält zentrale Einstellungen der Mappe:

- Notenzuordnung
- Rundungstabelle
- Gewichtungen
- Switches
- `HJ1-Anteil`
- `Dämpfung`
- weitere Steuerwerte

### Eingaben

Die Lehrkraft kann hier Bewertungsgrenzen, Gewichte und Switches anpassen.

### Weiterverwendung

Fast alle anderen Blätter verweisen auf Werte aus `Parameter`.

### Kontrolle

Das Prüfskript kontrolliert u. a.:

- ob erwartete Parameter vorhanden sind
- ob Gewichtssummen passen
- ob Switches gültig sind
- ob Parameterbezüge verrutscht wirken

## Blatt: `Selbstevaluation`

### Zweck

Das Blatt `Selbstevaluation` berechnet aus einer Selbsteinschätzung einen gedämpften Reflexionsanteil für die mündliche Bewertung.

### Q1 und Q3

In `Q1` und `Q3` gibt es eine direkte Selbstevaluationsnote. Diese wird mit einer Referenz aus `Kompetenz` und `Strichliste` verglichen und anschließend gedämpft.

Typische Spalten:

- `Selbsteval.`
- `Kompetenz`
- `Strichliste`
- `Referenz`
- `Gerundet`
- `Gedämpft`
- `Gerundet`
- `Differenz`

### Q2 und Q4

In `Q2` und `Q4` ist die Selbstevaluation ausführlicher aufgebaut. Die Schülerin bzw. der Schüler schätzt mehrere Kompetenzbereiche ein; daneben kann eine Lehrerbewertung stehen.

Typische Spalten:

- `Quantität`
- `Qualität`
- `Sprachl. K`
- `Soziale K`
- `Gesamt`
- `Gerundet`
- Lehrerbewertung derselben Bereiche
- `Strichliste`
- `Referenz`
- `Gedämpft`
- `Differenz`

### Weiterverwendung

Der gerundete gedämpfte Selbstevaluationswert wird im Blatt `Mündlich` als Selbstevaluationsanteil verwendet.

## Blatt: `Mündlich`

### Zweck

Das Blatt `Mündlich` berechnet die mündliche Leistung in den Quartalen.

### Eingaben

Typische Eingaben sind:

- Strichlistenwerte bzw. daraus entstehende Strichlistennoten
- Kompetenzbewertungen
- Selbstevaluationen aus `Selbstevaluation`
- ggf. manuell erteilte mündliche Noten

### Automatische Berechnungen

Das Blatt berechnet u. a.:

- Strichlistennote
- Kompetenznote
- mündliche Note mit Selbstevaluation
- Referenz ohne Selbstevaluation
- Differenz mit/ohne Selbstevaluation
- gerundete Werte

### Rundung

Rundungsspalten beziehen sich auf den unmittelbar davor oder daneben berechneten ungerundeten Wert. Die Rundung erfolgt über die Rundungstabelle aus `Parameter`.

### Q1 und Q3

`Q1` und `Q3` sind eigenständige Abschnittsblöcke. Die Kompetenzbewertung enthält hier eine zusammengefasste Kompetenzspalte.

Die zusammengefasste Kompetenzspalte vertritt die beiden differenzierten Kompetenzanteile, die in `Q2` und `Q4` getrennt auftreten.

### Q2 und Q4

`Q2` und `Q4` sind Abschlussblöcke eines Halbjahres. Die Kompetenzbewertung ist hier ausführlicher:

- `Quantität`
- `Qualität`
- `Soz. Komp.`
- `Spr. Komp.`

In der aktuellen Mappe wird für die mündliche Gesamtformel in `Q2` und `Q4` die gerundete Kompetenzbasis verwendet. Dadurch sind Gesamtformel und Referenz ohne Selbstevaluation konsistent.

### Selbstevaluation

Die Selbstevaluation wird nicht als freie Selbstnote übernommen. Sie wird gegen eine Referenz geprüft und gedämpft.

Die Differenzspalte zeigt, wie stark die Selbstevaluation die mündliche Note tatsächlich verändert.

### Weiterverwendung

Die gerundete bzw. erteilte mündliche Note wird in `Zwischennote` und `Zeugnis` weiterverwendet.

## Blatt: `LEK`

### Zweck

Das Blatt `LEK` erfasst schriftliche Leistungsnachweise.

### Eingaben

Typische Eingaben sind:

- `Punkte`
- `Max`

### Automatische Berechnungen

Das Blatt berechnet:

- `Prozent`
- `Note`
- ggf. Durchschnittswerte oder Verteilungen

### Weiterverwendung

Die berechneten schriftlichen Werte werden in `Schriftlich` und `Zeugnis` verwendet.

## Blatt: `Protokoll`

### Zweck

Das Blatt `Protokoll` erfasst eine schriftliche oder dokumentierende Leistung.

### Logik

Punkte werden über Prozentwerte in Noten umgerechnet. Fehlende Werte werden mit `-1` behandelt.

### Weiterverwendung

Die Ergebnisse können in `Schriftlich` eingehen.

## Blatt: `Schriftlich`

### Zweck

Das Blatt `Schriftlich` fasst schriftliche Teilbereiche zusammen, insbesondere `LEK` und `Protokoll`.

### Logik

Wenn nur ein schriftlicher Bestandteil vorhanden ist, wird dieser übernommen. Wenn beide vorhanden sind, werden sie gemäß den Parametern für `Gewichte Schriftlich` kombiniert.

### Weiterverwendung

Die gerundeten schriftlichen Werte werden in `Zwischennote` und `Zeugnis` verwendet.

## Blatt: `Hefter`

### Zweck

Das Blatt `Hefter` erfasst Hefter- oder Mappenleistungen.

### Logik

Punkte werden über Prozentwerte in Noten umgerechnet. Fehlende Werte werden mit `-1` behandelt.

### Weiterverwendung

Die Ergebnisse können in `Sonstiges` eingehen.

## Blatt: `Plakat`

### Zweck

Das Blatt `Plakat` erfasst Plakat- oder Präsentationsleistungen.

### Logik

Punkte werden über Prozentwerte in Noten umgerechnet. Fehlende Werte werden mit `-1` behandelt.

### Weiterverwendung

Die Ergebnisse können in `Sonstiges` eingehen.

## Blatt: `Sonstiges`

### Zweck

Das Blatt `Sonstiges` fasst sonstige Leistungsbereiche zusammen, insbesondere `Hefter` und `Plakat`.

### Logik

Wenn nur ein Bestandteil vorhanden ist, wird dieser übernommen. Wenn beide vorhanden sind, werden sie gemäß den Parametern für `Gewichte Sonstiges` kombiniert.

### Weiterverwendung

Die gerundeten sonstigen Werte werden in `Zwischennote` und `Zeugnis` verwendet.

## Blatt: `Lernraum`

### Zweck

Das Blatt `Lernraum` erfasst bzw. berechnet den Lernraumanteil.

### Einordnung

Der `Lernraum` ist ein Binnenanteil innerhalb der mündlichen Bewertung.

Er ist nicht als vierter unabhängiger Hauptbereich neben `Mündlich`, `Schriftlich` und `Sonstiges` gedacht.

### Weiterverwendung

Der Lernraumwert kann in `Zwischennote` und `Zeugnis` in den mündlichen Block eingehen.

## Blatt: `Zwischennote`

### Zweck

Das Blatt `Zwischennote` führt die Hauptbereiche zu Abschnittsnoten und Zwischenständen zusammen.

### Eingaben / Bezüge

Es bezieht Werte aus:

- `Mündlich`
- `Schriftlich`
- `Sonstiges`
- `Lernraum`
- `Zeugnis` für den Stand nach `Q3`

### Q1, Q2, Q3 und Q4

Diese Werte sind Abschnittsnoten.

Berechnungslogik:

1. `Mündlich_Block` wird gebildet.
2. Falls `Lernraum` vorhanden ist, wird `Lernraum` als Binnenanteil innerhalb `Mündlich` berücksichtigt.
3. `Mündlich_Block`, `Schriftlich` und `Sonstiges` werden gemäß Parameter kombiniert.
4. Fehlende Werte werden je nach Switch über `Umlage` oder `Renormierung` behandelt.

### Stand nach Q3

Zusätzlich zur Abschnittsnote `Q3` gibt es den `Stand nach Q3`.

Der Stand nach `Q3` verwendet den Parameter `HJ1-Anteil`:

```text
Stand nach Q3 = HJ1-Anteil * H1 + (1 - HJ1-Anteil) * Q3
```

### Tendenzspalten

Tendenzspalten zeigen Entwicklungen. Die Vorzeichenlogik ist:

```text
positiv  = Verbesserung
negativ  = Verschlechterung
```

Die Differenz wird also als alter Wert minus neuer Wert berechnet.

### Weiterverwendung

Die Abschnittsnoten und Zwischenstände gehen in `Zeugnis` und in die Kompaktberichte des Prüfskripts ein.

## Blatt: `Zeugnis`

### Zweck

Das Blatt `Zeugnis` berechnet `H1`, `H2` und die Jahresnote.

### H1

`H1` wird aus den Bereichen des ersten Halbjahres gebildet:

- `Mündlich` aus `Mündl. Q1` und `Mündl. Q2`
- `Schriftlich` aus `LEK H1` und `Protokoll H1`
- `Sonstiges` aus `Hefter H1` und `Plakat H1`
- `Lernraum` aus `Lernr. Q1` und `Lernr. Q2`

Anschließend werden `Mündlich_Block`, `Schriftlich` und `Sonstiges` zum H1-Gesamtwert kombiniert.

### H2

`H2` wird analog aus den Bereichen des zweiten Halbjahres gebildet:

- `Mündlich` aus `Mündl. Q3` und `Mündl. Q4`
- `Schriftlich` aus `LEK H2` und `Protokoll H2`
- `Sonstiges` aus `Hefter H2` und `Plakat H2`
- `Lernraum` aus `Lernr. Q3` und `Lernr. Q4`

Anschließend werden `Mündlich_Block`, `Schriftlich` und `Sonstiges` zum H2-Gesamtwert kombiniert.

### Jahresnote

Die Jahresnote wird standardmäßig als 50/50-Kombination aus `H1` und `H2` berechnet:

```text
Jahresnote = 0.5 * H1 + 0.5 * H2
```

### Erteilte Note

Die erteilte Note ist die pädagogisch verantwortete Endentscheidung. Sie kann vom berechneten Wert abweichen, sollte dann aber bewusst geprüft werden.

## Prüfskript und Berichte

### Prüfbericht

Der Prüfbericht kontrolliert technische und fachliche Plausibilität:

- fehlende oder fehlerhafte Parameter
- falsche Switches
- Formel- und Zellfehler
- verrutschte Bezüge
- unplausible Gewichtungen
- große Notensprünge
- Nähe zu Rundungsgrenzen
- starke Abweichungen zwischen berechneter und erteilter Note

### Kompaktberichte

Die Kompaktberichte geben pro Schüler einen Verlauf:

- `Q1`, `Q2`, `H1`
- `Q3`, `Stand nach Q3`, `Q4`, `H2`
- Jahresnote berechnet / gerundet / erteilt
- Auffälligkeiten aus der Plausibilitätsprüfung


\newpage

# Formelreferenz

Diese Formelreferenz beschreibt die zentralen Formeltypen der Mappe. Gleichartige Formeln werden in den Schülerzeilen nach unten kopiert; deshalb werden sie hier nicht für jede einzelne Schülerzeile wiederholt.

## Allgemeine Konventionen

Fehlende Werte:

```text
-1 = Wert fehlt
```

Rundung über die Rundungstabelle:

```calc
=IF(Wert=-1;-1;VLOOKUP(Wert;Parameter.$E$5:$F$22;2;1))
```

Notenzuordnung aus Prozentwerten:

```calc
=IF(Prozent=-1;-1;VLOOKUP(Prozent;Parameter.$B$5:$C$22;2;1))
```

## Prozentwert aus Punkten

Für `LEK`, `Protokoll`, `Hefter`, `Plakat` und `Lernraum` gilt im Kern:

```text
Prozent = Punkte / Max * 100
Note = f(Prozent)
```

Repräsentative Calc-Formel:

```calc
=IF(D5=-1;-1;D5/E5*100)
```

## Strichliste im Blatt `Mündlich`

Die Strichliste berücksichtigt `Anzahl`, `Max` und `Abzug`:

```text
Prozent = Anzahl / (Max - Abzug) * 100
Strichlistennote = f(Prozent)
```

Repräsentative Calc-Formeln:

```calc
=IF(D5=-1;-1;D5/(E5-F5)*100)
=IF(G5=-1;-1;VLOOKUP(G5;Parameter.$B$5:$C$22;2;1))
```

## Kompetenznote im Blatt `Mündlich`

### Q1 und Q3

In `Q1` und `Q3` gibt es eine zusammengefasste Kompetenzspalte.

```text
Kompetenz_roh = g_Quantität * Quantität
              + g_Qualität * Qualität
              + (g_sozial + g_sprachlich) * Kompetenz
```

Repräsentative Calc-Formel:

```calc
=IF(OR(L5=-1;M5=-1;N5=-1);
    -1;
    Parameter.$I$5*L5
    + Parameter.$I$6*M5
    + (Parameter.$I$7+Parameter.$I$7)*N5)
```

Anschließend wird gerundet:

```calc
=IF(O5=-1;-1;VLOOKUP(O5;Parameter.$E$5:$F$22;2;1))
```

Hinweis: Die zusammengefasste Kompetenzspalte vertritt die differenzierten Kompetenzanteile, die in `Q2` und `Q4` getrennt stehen.

### Q2 und Q4

In `Q2` und `Q4` werden soziale und sprachliche Kompetenz getrennt geführt.

```text
Kompetenz_roh = g_Quantität * Quantität
              + g_Qualität * Qualität
              + g_sozial * Soziale_Kompetenz
              + g_sprachlich * Sprachliche_Kompetenz
```

Repräsentative Calc-Formel:

```calc
=IF(OR(L43=-1;M43=-1;N43=-1;O43=-1);
    -1;
    Parameter.$I$5*L43
    + Parameter.$I$6*M43
    + Parameter.$I$7*N43
    + Parameter.$I$7*O43)
```

Anschließend wird gerundet:

```calc
=IF(P43=-1;-1;VLOOKUP(P43;Parameter.$E$5:$F$22;2;1))
```

Die gerundete Kompetenzbasis wird in `Q2` und `Q4` in der mündlichen Gesamtformel verwendet.

## Selbstevaluation: Referenz

Die Referenz bildet den fachlichen Vergleichswert für die Selbstevaluation. Wenn ein Bestandteil fehlt, werden die vorhandenen Bestandteile automatisch normiert.

```text
Referenz = gewichtetes Mittel aus Kompetenz und Strichliste
```

Repräsentative Calc-Formel für `Q1` / `Q3`:

```calc
=IF(AND(E5=-1;F5=-1);
    -1;
    (IF(E5=-1;0;Parameter.$I$13*E5)
     + IF(F5=-1;0;Parameter.$I$14*F5))
    /(IF(E5=-1;0;Parameter.$I$13)
      + IF(F5=-1;0;Parameter.$I$14)))
```

Für `Q2` / `Q4` wird analog die gerundete Lehrer-Kompetenzbewertung und die Strichliste verwendet.

Repräsentative Calc-Formel:

```calc
=IF(AND(O43=-1;P43=-1);
    -1;
    (IF(O43=-1;0;Parameter.$I$13*O43)
     + IF(P43=-1;0;Parameter.$I$14*P43))
    /(IF(O43=-1;0;Parameter.$I$13)
      + IF(P43=-1;0;Parameter.$I$14)))
```

## Selbstevaluation: Dämpfung

Die Selbstevaluation wird exponentiell gegen die Referenz gedämpft.

```text
E_gedämpft = exp(-d * abs(E - Referenz)) * E
           + (1 - exp(-d * abs(E - Referenz))) * Referenz
```

Dabei ist `d` der Parameter `Dämpfung`.

Repräsentative Calc-Formel:

```calc
=IF(D5=-1;-1;EXP(-Parameter.$I$15*ABS(D5-G5))*D5+(1-EXP(-Parameter.$I$15*ABS(D5-G5)))*G5)
```

Danach wird wieder gerundet:

```calc
=IF(I5=-1;-1;VLOOKUP(I5;Parameter.$E$5:$F$22;2;1))
```

Die Differenz zeigt den Effekt der Dämpfung:

```calc
=IF(OR(D5=-1;G5=-1;J5=-1);-1;H5-J5)
```

Positive Werte bedeuten hier: Die gedämpfte Selbstevaluation wirkt günstiger als die Referenz.

## Mündliche Gesamtnote mit Selbstevaluation

### Q1 und Q3

In `Q1` und `Q3` verwendet die mündliche Gesamtformel:

- `H` = Strichlistennote
- `P` = gerundete Kompetenznote
- `U` = gedämpfte gerundete Selbstevaluation

Repräsentative Calc-Formel:

```calc
=IF(OR(H5=-1;P5=-1);
    -1;
    IF(Parameter.$I$23="Umlage";
       Parameter.$I$20*H5
       + IF(U5=-1;
            (1-Parameter.$I$20)*P5;
            Parameter.$I$21*P5 + Parameter.$I$22*U5);
       IF(Parameter.$I$23="Renormierung";
          IF(U5=-1;
             Parameter.$I$20/(Parameter.$I$20+Parameter.$I$21)*H5
             + Parameter.$I$21/(Parameter.$I$20+Parameter.$I$21)*P5;
             Parameter.$I$20*H5 + Parameter.$I$21*P5
             + Parameter.$I$22*U5);
          "Modus?")))
```

### Q2 und Q4

In `Q2` und `Q4` verwendet die mündliche Gesamtformel die gerundete Kompetenzbasis `Q`.

Repräsentative Calc-Formel:

```calc
=IF(OR(H43=-1;Q43=-1);
    -1;
    IF(Parameter.$I$23="Umlage";
       Parameter.$I$20*H43
       + IF(U43=-1;
            (1-Parameter.$I$20)*Q43;
            Parameter.$I$21*Q43 + Parameter.$I$22*U43);
       IF(Parameter.$I$23="Renormierung";
          IF(U43=-1;
             Parameter.$I$20/(Parameter.$I$20+Parameter.$I$21)*H43
             + Parameter.$I$21/(Parameter.$I$20+Parameter.$I$21)*Q43;
             Parameter.$I$20*H43 + Parameter.$I$21*Q43
             + Parameter.$I$22*U43);
          "Modus?")))
```

## Referenz ohne Selbstevaluation im Blatt `Mündlich`

Die Referenz ohne Selbstevaluation zeigt, welche mündliche Note ohne den Selbstevaluationsanteil entstehen würde.

Für `Q1` und `Q3`:

```calc
=IF(AND(H5=-1;P5=-1);
    -1;
    VLOOKUP(
      (IF(H5=-1;0;Parameter.$I$20*H5)
       + IF(P5=-1;0;Parameter.$I$21*P5))
      /(IF(H5=-1;0;Parameter.$I$20)
        + IF(P5=-1;0;Parameter.$I$21));
      Parameter.$E$5:$F$22;2;1))
```

Für `Q2` und `Q4`:

```calc
=IF(AND(H43=-1;Q43=-1);
    -1;
    VLOOKUP(
      (IF(H43=-1;0;Parameter.$I$20*H43)
       + IF(Q43=-1;0;Parameter.$I$21*Q43))
      /(IF(H43=-1;0;Parameter.$I$20)
        + IF(Q43=-1;0;Parameter.$I$21));
      Parameter.$E$5:$F$22;2;1))
```

Differenz mit / ohne Selbstevaluation:

```calc
=IF(OR(W5=-1;X5=-1);-1;X5-W5)
```

Positive Werte bedeuten: Mit Selbstevaluation ist die mündliche Note besser als ohne Selbstevaluation.

## Zusammenführung in `Schriftlich`

`Schriftlich` kombiniert `LEK` und `Protokoll`.

```text
Wenn beide fehlen: -1
Wenn nur einer vorhanden ist: dieser Wert
Wenn beide vorhanden sind: gewichtetes Mittel
```

Repräsentative Calc-Formel:

```calc
=IF(D5=-1;IF(E5=-1;-1;E5);IF(E5=-1;D5;Parameter.$I$29*D5+Parameter.$I$30*E5))
```

## Zusammenführung in `Sonstiges`

`Sonstiges` kombiniert `Hefter` und `Plakat`.

```text
Wenn beide fehlen: -1
Wenn nur einer vorhanden ist: dieser Wert
Wenn beide vorhanden sind: gewichtetes Mittel
```

Repräsentative Calc-Formel:

```calc
=IF(D5=-1;IF(E5=-1;-1;E5);IF(E5=-1;D5;Parameter.$L$5*D5+Parameter.$L$6*E5))
```

## Abschnittsnote im Blatt `Zwischennote`

Zunächst wird der mündliche Block gebildet:

```text
Mündlich_Block = (1 - Lernraumgewicht) * Mündlich + Lernraumgewicht * Lernraum
```

Wenn `Lernraum = -1`, wird das Lernraumgewicht nicht angewendet.

### Umlage

Bei `Umlage` werden fehlende Anteile von `Schriftlich` oder `Sonstiges` auf den mündlichen Block gelegt.

Repräsentative Calc-Formel:

```calc
=IF(D5=-1;
    -1;
    IF(Parameter.$L$16="Umlage";
       (1-IF(E5=-1;0;Parameter.$L$12)
          -IF(F5=-1;0;Parameter.$L$13))
       *((1-IF(G5=-1;0;Parameter.$L$14))*D5
         +IF(G5=-1;0;Parameter.$L$14)*G5)
       +IF(E5=-1;0;Parameter.$L$12*E5)
       +IF(F5=-1;0;Parameter.$L$13*F5);
       ...))
```

### Renormierung

Bei `Renormierung` werden die vorhandenen Bestandteile proportional neu gewichtet.

Repräsentative Calc-Formel für den Renormierungsteil:

```calc
(Parameter.$L$11
 *((1-IF(G5=-1;0;Parameter.$L$14))*D5
   +IF(G5=-1;0;Parameter.$L$14)*G5)
 +IF(E5=-1;0;Parameter.$L$12*E5)
 +IF(F5=-1;0;Parameter.$L$13*F5))
/(Parameter.$L$11
  +IF(E5=-1;0;Parameter.$L$12)
  +IF(F5=-1;0;Parameter.$L$13))
```

Rundung der Abschnittsnote:

```calc
=IF(H5=-1;-1;VLOOKUP(H5;Parameter.$E$5:$F$22;2;1))
```

## Stand nach Q3

Der Stand nach `Q3` kombiniert `H1` und die Abschnittsnote `Q3`.

```text
Stand nach Q3 = HJ1-Anteil * H1 + (1 - HJ1-Anteil) * Q3
```

Repräsentative Calc-Formel:

```calc
=IF(I81=-1;J81;Parameter.$L$15*J81+(1-Parameter.$L$15)*I81)
```

Rundung:

```calc
=IF(K81=-1;-1;VLOOKUP(K81;Parameter.$E$5:$F$22;2;1))
```

Tendenz:

```calc
=J81-L81
```

## Tendenzen

Die Mappe verwendet pädagogische Vorzeichen:

```text
Tendenz = alter Wert - neuer Wert
```

Damit bedeutet:

```text
positiv  = Verbesserung
negativ  = Verschlechterung
```

Beispiele aus `Zwischennote`:

```calc
=I5-I43      // Q1 -> Q2
=J81-L81     // H1 -> Stand nach Q3
=L81-I119    // Stand nach Q3 -> Q4
```

## Halbjahresnoten im Blatt `Zeugnis`

### Bereich `Mündlich`

`Mündlich` wird aus den Quartalswerten des Halbjahres gebildet.

```text
Wenn beide Quartalswerte fehlen: -1
Wenn nur einer vorhanden ist: dieser Wert
Wenn beide vorhanden sind: gewichtetes Mittel aus Q1/Q3 und Q2/Q4
```

Repräsentative Calc-Formel:

```calc
=IF(AND(D5=-1;E5=-1);-1;IF(D5=-1;E5;IF(E5=-1;D5;Parameter.$L$21*D5+Parameter.$L$22*E5)))
```

### Bereich `Schriftlich`

`Schriftlich` wird aus `LEK` und `Protokoll` gebildet.

```calc
=IF(AND(G5=-1;H5=-1);-1;IF(G5=-1;H5;IF(H5=-1;G5;Parameter.$I$29*G5+Parameter.$I$30*H5)))
```

### Bereich `Sonstiges`

`Sonstiges` wird aus `Hefter` und `Plakat` gebildet.

```calc
=IF(AND(J5=-1;K5=-1);-1;IF(J5=-1;K5;IF(K5=-1;J5;Parameter.$I$29*J5+Parameter.$I$30*K5)))
```

### Bereich `Lernraum`

`Lernraum` wird aus den Lernraumwerten des jeweiligen Halbjahres gebildet.

```calc
=IF(AND(M5=-1;N5=-1);-1;IF(M5=-1;N5;IF(N5=-1;M5;Parameter.$L$21*M5+Parameter.$L$22*N5)))
```

## Halbjahres-Gesamtwert im Blatt `Zeugnis`

Die H1- bzw. H2-Gesamtformel entspricht der Logik aus `Zwischennote`, aber mit den Zeugnisparametern.

Repräsentative Calc-Formel:

```calc
=IF(F5=-1;
    -1;
    IF(Parameter.$L$27="Umlage";
       (1-IF(I5=-1;0;Parameter.$L$24)
          -IF(L5=-1;0;Parameter.$L$25))
       *((1-IF(O5=-1;0;Parameter.$L$26))*F5
         +IF(O5=-1;0;Parameter.$L$26)*O5)
       +IF(I5=-1;0;Parameter.$L$24*I5)
       +IF(L5=-1;0;Parameter.$L$25*L5);
       IF(Parameter.$L$27="Renormierung";
          (Parameter.$L$23
           *((1-IF(O5=-1;0;Parameter.$L$26))*F5
             +IF(O5=-1;0;Parameter.$L$26)*O5)
           +IF(I5=-1;0;Parameter.$L$24*I5)
           +IF(L5=-1;0;Parameter.$L$25*L5))
          /(Parameter.$L$23
            +IF(I5=-1;0;Parameter.$L$24)
            +IF(L5=-1;0;Parameter.$L$25));
          "Modus?")))
```

Rundung:

```calc
=IF(P5=-1;-1;VLOOKUP(P5;Parameter.$E$5:$F$22;2;1))
```

## Jahresnote

Die Jahresnote wird aus `H1` und `H2` gebildet:

```text
Jahresnote = 0.5 * H1 + 0.5 * H2
```

Repräsentative Calc-Formel:

```calc
=0.5*R43+0.5*Q43
```

Rundung:

```calc
=IF(S43=-1;-1;VLOOKUP(S43;Parameter.$E$5:$F$22;2;1))
```

Die Spalte `Erteilt` bleibt die pädagogisch verantwortete Endentscheidung.
