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
