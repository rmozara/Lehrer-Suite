# SE · Selbstevaluation 1.0.0

Der SE-Collector führt strukturierte Selbstevaluationen auf Schülergeräten durch und überträgt die Ergebnisse in `Selbstevaluation.ods`.

## Vorbereitung

1. Außerhalb des Programmordners einen persönlichen Arbeitsordner für Klasse, Unterrichtsreihe oder Thema wählen. Die Ordnerstruktur ist frei wählbar.
2. `Selbstevaluation.ods` dort automatisch beim ersten Start anlegen lassen oder aus `templates` kopieren.
3. Namensliste, Schüler-IDs, Fach, Kürzel, Schulname, Zeitraum und Bewertungsparameter kontrollieren. Drei Beispielpersonen zeigen die vorgesehenen Eingabespalten.
4. SE starten und diesen Arbeitsordner auswählen.

## Start

Linux:

```bash
./run_on_linux.sh
```

Windows: `run_on_windows.bat` doppelklicken.

Die Lehreroberfläche öffnet sich lokal unter `http://127.0.0.1:8765/admin`.

Ist noch kein gemeinsames Lehrerpasswort eingerichtet, zeigt SE stattdessen im Browser den Hinweis, zuerst QR zu starten. SE erzeugt kein eigenes Zufallspasswort.

## Unterrichtsablauf

1. Eine Sitzung für Klasse, Formular und Zeitraum anlegen.
2. Sitzung öffnen und den sechsstelligen Sitzungscode anzeigen.
3. Die Lernenden scannen ihre persönliche QR-Karte und geben den Sitzungscode ein.
4. Antworten prüfen und verbindlich abgeben.
5. Abgabestand beobachten und Sitzung schließen.
6. Ergebnisse in `Selbstevaluation.ods` übernehmen und Auswertung oder Rückmeldebögen erzeugen.
7. Eine abgeschlossene Sitzung bei Bedarf archivieren; archivierte Sitzungen können wiederhergestellt oder endgültig gelöscht werden.

## Zugangswege

- **Direktmodus:** persönliche QR-Karte scannen und Sitzungscode eingeben.
- **Zwei-QR-Ausweichweg:** zuerst den aktuellen Sitzungs-QR, danach die persönliche QR-Karte scannen oder als Bild auswählen.
- **Persönlicher Code:** kann verwendet werden, wenn die Kamera die QR-Karte nicht erkennt.
- **Smartboard:** die auf der Sitzungsseite genannte Adresse mit `/anzeige` im Browser öffnen und den Sitzungscode eingeben. Dort erscheinen keine Namen, Punkte oder Noten.

## Ausgaben

- aktualisierte `Selbstevaluation.ods`
- A4-Auswertung pro Person
- QR-Ersatzanzeige für vergessene Karten
- automatische Sicherungen vor Aktualisierungen

## Datenschutz

Alle Sitzungen und Antworten bleiben lokal. SE liest die gemeinsame Schüleridentität aus `Collector-Daten`; eine einmal ausgegebene Jahreskarte kann auch für HB verwendet werden.

## Hinweise

- Schülergerät und Lehrerrechner müssen sich im selben WLAN befinden.
- VPN sollte während der Evaluation deaktiviert sein.
- SE und HB dürfen wegen des gemeinsamen Unterrichtsports nicht gleichzeitig laufen.
