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
