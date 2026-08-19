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
