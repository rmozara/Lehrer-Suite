# Beispiel-Durchlauf: QR → SE → HB

Dieser Ordner ist ausschließlich Anschauungsmaterial. Er zeigt eine mögliche persönliche Arbeitsstruktur außerhalb des Programmordners. Die Namen `Anna Beispiel`, `Ben Beispiel` und `Carla Beispiel` sowie die Schüler-IDs `8a-01` bis `8a-03` sind synthetisch.

Die Struktur ist eine Empfehlung, keine technische Pflicht. Eigene Arbeitsordner können an anderer Stelle liegen und anders benannt sein.

```text
Beispielschule/
└── 2026-27/
    ├── Organisation/
    │   └── QR-Karten/
    │       └── Namensliste.ods
    └── Unterricht/
        └── 8a/
            └── Physik/
                └── Beispiel-Thema/
                    ├── SE/
                    │   └── Selbstevaluation.ods
                    └── HB/
                        └── Hefterbewertung.ods
```

- `Namensliste.ods` zeigt die gemeinsame Ausgangsliste für QR.
- `Selbstevaluation.ods` enthält synthetische Beispielabgaben im Blatt `Rohdaten`.
- `Hefterbewertung.ods` enthält synthetische Selbst-, Peer- und Lehrerbewertungen.

QR-Karten- und Rückmelde-PDFs sind nicht enthalten. Die Produktionsfunktionen konnten mit den vorhandenen Python-Abhängigkeiten ausgeführt werden; die abschließende LibreOffice-Konvertierung war in der abgeschotteten Release-Umgebung wegen fehlender IPC-Unterstützung nicht möglich.

Der Beispiel-Durchlauf enthält bewusst keine Datenbanken, Identitätstokens, Passwörter, Netzwerkeinstellungen, Backups oder sonstigen Laufzeitzustand. Für eine eigene Klasse die Vorlagen aus den drei Programmordnern in eigene Arbeitsordner kopieren und dort bearbeiten; diesen Beispielordner nicht als produktive Installation verwenden.
