# Gemeinsame persönliche QR-Identität

Eine Person erhält für ein Schuljahr genau eine persönliche QR-Karte. Dieselbe Karte funktioniert im SE- und HB-Collector.

Der QR-Code enthält einen zufälligen persönlichen Token, aber weder Namen, Bewertung noch konkrete Sitzung. Die aktive Sitzung wird erst durch den sechsstelligen Sitzungscode oder den aktuellen Sitzungs-QR bestimmt.

Der QR-Generator ist die einzige Anwendung, die persönliche Identitäten erzeugt oder aktualisiert. SE und HB lesen das gemeinsame Register `Collector-Daten/identities.sqlite3` ausschließlich für die Zuordnung.

## Eigenschaften

- unveränderter Token bei erneutem Import derselben Schüler-ID im selben Schuljahr
- neuer Token für ein neues Schuljahr
- unabhängig von IP-Adresse, Unterrichtsfach und Collector
- historische Sitzungen behalten ihren damaligen Namenslistenstand
- keine konkurrierenden Tokens in den Collector-Datenbanken

Das Identitätsregister und die ausgegebenen Karten sind geschützt aufzubewahren und dürfen nicht veröffentlicht werden.
