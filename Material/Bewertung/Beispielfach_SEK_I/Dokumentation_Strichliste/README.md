# Strichliste

`Strichliste.ods` dient zur schnellen Erfassung mündlicher Unterrichtsbeiträge einer Klasse. Die Datei enthält eine zentrale Namensliste und je ein Tabellenblatt für das 1. bis 4. Quartal.

Die Strichliste wird getrennt von `Bewertung.ods` geführt. Quartalsergebnisse können anschließend in die Bewertungsmappe übertragen werden.

## Einrichtung

1. Im Tabellenblatt **Namensliste** die Namen der Schülerinnen und Schüler eintragen.
2. Die Namen werden automatisch in alle vier Quartalsblätter übernommen.
3. In einem Quartalsblatt für jede verwendete Unterrichtsspalte oben das Datum eintragen.

## Eingaben

| Eingabe | Bedeutung |
|---|---|
| `0`, `1`, `2`, … | vergebener Bewertungswert; auch `0` ist ein echter Wert |
| `–` | bewusst nicht bewertet |
| `x` | Fehlzeit |
| leere Zelle | noch offen oder übersehen |
| Datum | aktiviert die jeweilige Unterrichtsspalte |

Für zwei getrennte Bewertungsblöcke am selben Tag wird dasselbe Datum in zwei Unterrichtsspalten eingetragen.

## Berechnung

- **Max:** höchster an diesem Datum vergebener Zahlenwert
- **Anzahl:** Summe der vergebenen Zahlenwerte je Schüler
- **Abzug:** Summe der Maximalwerte für Unterrichtsspalten mit `–` oder `x`
- **Wertungsmax:** `Max − Abzug`
- **Prozent:** `Anzahl ÷ Wertungsmax × 100`; die Anzeige erfolgt ohne Prozentzeichen
- **Offen:** Anzahl aktivierter Unterrichtsspalten mit leerer Eingabezelle

Solange noch keine Unterrichtsspalte durch ein Datum aktiviert wurde, zeigt die Auswertung den technischen Ergebniswert `-1`.

## Navigation

In jedem Quartalsblatt sind die Namensspalten und die oberen Kopfzeilen fixiert. Beim horizontalen Scrollen bleiben **Nr.** und **Name** sichtbar; beim vertikalen Scrollen bleiben Datum und Spaltenüberschriften sichtbar.

Die dezente Zeilenbänderung und eine stärkere Trennlinie nach jeweils fünf Schülerinnen und Schülern erleichtern die Zuordnung über viele Datumsspalten hinweg.

Die Formeln in den Auswertungs- und Maximalwertfeldern sollten nicht überschrieben werden.
