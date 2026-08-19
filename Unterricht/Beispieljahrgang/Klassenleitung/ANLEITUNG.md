# Klassenleitung 0.3.3

Diese Vorlage funktioniert vollständig lokal und ohne Bolle, IServ, WebUntis oder ein anderes schulisches Verwaltungssystem.

## Instanziierung

Den Ordner `Organisation/Klassenleitung` in den Ordner `Organisation` des betreffenden Jahrgangs beziehungsweise der Klasse kopieren. Anschließend `Klassenleitung.ods` öffnen und im Blatt **Einstellungen** die Grunddaten eintragen.

```text
Unterricht/
└── Jahrgang_8/
    └── Organisation/
        └── Klassenleitung/
```

Die veröffentlichte Vorlage enthält keine personenbezogenen Daten. Erst die kopierte Arbeitsinstanz wird mit realen Angaben gefüllt und darf nicht mitveröffentlicht werden.

## Arbeitsprinzip

- Alle Aufgaben, Fristen und Nachfasspunkte werden ausschließlich unter **Offene Vorgänge** eingetragen.
- **Agenda** sortiert die offenen Vorgänge automatisch nach Fälligkeit.
- **Erledigt** zeigt abgeschlossene Vorgänge automatisch an; die Quellzeilen werden nicht gelöscht.
- Schülernamen oder Klassenbereiche werden direkt eingetragen; eine technische Schüler-ID ist nicht erforderlich.
- **Fehlzeiten** kann im Standalone-Betrieb offene Entschuldigungen kontrollieren; der verbindliche Nachweis bleibt im Klassenbuch oder Schulsystem.
- Fachblätter sind Register und Ablageübersichten, keine zusätzlichen Aufgabenlisten.
- Im Blatt **Schulinterne Systeme** kann die Standalone-Arbeitsweise später an die konkrete Schule angepasst werden.

Weitere Hinweise stehen in `Organisation/Klassenleitung/README.md`.

Die drei Personen und wenigen Vorgänge in der Vorlage sind ausdrücklich als Beispieldaten gekennzeichnet und können nach dem Ausprobieren gelöscht werden.

## Enthaltene Vorlagen

- `04_Gespraeche/Elterngespraech/`: Leitfaden, interne Gesprächsnotiz und Ergebnisprotokoll
- `01_Uebergabe_und_Grundlagen/Klassenuebergabe_Kurzprotokoll.odt`
- `07_Konferenzen_und_Zeugnisse/Klassenkonferenz_Vorbereitung_Ergebnisnotiz.odt`
- `08_Ausfluege_und_Veranstaltungen/Ausflug_Wandertag_Checkliste.odt`

Die Vorlagen sind neutrale Arbeitshilfen. Schulisch vorgeschriebene Formulare, Genehmigungswege und Ablagevorgaben bleiben verbindlich.
