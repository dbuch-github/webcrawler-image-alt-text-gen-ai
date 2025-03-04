# Webcrawler Image Analyzer

Diese Streamlit-Anwendung nutzt den Webcrawler, um Bilder von Webseiten zu analysieren und tabellarisch darzustellen.

## Funktionen

- Eingabe einer Website-URL zur Analyse
- Festlegung einer Mindestgröße für Bilder in Kilobyte
- Automatische Behandlung von Cookie-Consent-Dialogen
- Erweiterte Optionen:
  - Headless-Modus (Browser im Hintergrund)
  - Browser-Auswahl (Chrome, Firefox oder automatisch)
  - Verzögerung nach Consent-Behandlung einstellbar
- Anzeige aller Überschriften (H1, H2, H3) der Webseite
- Tabellarische Auflistung aller Bilder mit:
  - Thumbnail-Vorschau
  - Bild-URL
  - ALT-Text
  - Dateigröße in Kilobyte

## Installation

1. Stellen Sie sicher, dass Python 3.7+ installiert ist
2. Installieren Sie die erforderlichen Abhängigkeiten:

```bash
pip install -r requirements.txt
```

## Ausführung

Starten Sie die Anwendung mit:

```bash
streamlit run app.py
```

Die Anwendung öffnet sich automatisch in Ihrem Standardbrowser.

## Verwendung

1. Geben Sie eine vollständige URL ein (mit http:// oder https://)
2. Legen Sie die gewünschte Mindestgröße für Bilder in Kilobyte fest (Standard: 10 KB)
3. Optional: Passen Sie die erweiterten Optionen an:
   - Deaktivieren Sie den Headless-Modus, um den Browser sichtbar zu machen
   - Wählen Sie einen spezifischen Browser aus
   - Passen Sie die Verzögerung nach der Consent-Behandlung an
4. Die Anwendung lädt die Webseite, behandelt automatisch Cookie-Consent-Dialoge und wartet die angegebene Zeit
5. Anschließend werden alle Bilder und Überschriften extrahiert
6. Es werden nur Bilder angezeigt, die die angegebene Mindestgröße erreichen oder überschreiten
7. Scrollen Sie durch die Tabelle, um alle gefundenen Bilder zu sehen

## Technische Details

- Verwendet Selenium für das Crawling der Webseiten
- Unterstützt sowohl Chrome als auch Firefox als Browser
- Verarbeitet automatisch Cookie-Banner und Consent-Formulare
- Lädt Bilder als Thumbnails für eine bessere Darstellung

## Hinweise

- Bei sehr großen Webseiten kann der Ladevorgang einige Zeit in Anspruch nehmen
- Manche Webseiten blockieren möglicherweise Crawler oder haben Bilder, die nicht direkt zugänglich sind
- Die Dateigröße wird über HTTP-Anfragen ermittelt und kann bei einigen Bildern nicht verfügbar sein
