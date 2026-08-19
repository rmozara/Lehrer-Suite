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
