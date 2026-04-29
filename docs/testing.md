# Testing – MedScan AI

Dieses Dokument beschreibt die Teststrategie des Projekts **MedScan AI**.

Ziel der Tests ist es, zentrale Hilfsfunktionen und API-Logik automatisiert zu überprüfen, ohne echte AWS-Ressourcen aufzurufen.

---

## 1. Überblick

Das Projekt verwendet `pytest` für automatisierte Unit Tests.

Die Tests werden lokal ausgeführt und zusätzlich automatisch über GitHub Actions geprüft.

Aktueller Stand:

```text
8 passed
```

---

## 2. Warum Unit Tests?

Unit Tests prüfen kleine, isolierte Teile der Anwendung.

In diesem Projekt werden keine echten S3 Buckets, DynamoDB Tabellen oder SQS Queues im Test verwendet. Stattdessen werden zentrale Logikbausteine lokal geprüft.

Das hat mehrere Vorteile:

- Tests laufen schnell.
- Tests verursachen keine AWS-Kosten.
- Tests benötigen keine echten AWS-Zugangsdaten.
- Fehler in Hilfsfunktionen werden früh erkannt.
- GitHub Actions kann die Tests automatisch bei jedem Push ausführen.

---

## 3. Lokale Testausführung

Voraussetzung ist Python 3.11.

Zuerst werden die Entwicklungsabhängigkeiten installiert:

```powershell
python -m pip install -r requirements-dev.txt
```

Danach werden die Tests ausgeführt:

```powershell
python -m pytest -q
```

Erwartetes Ergebnis:

```text
8 passed
```

---

## 4. Test Dependencies

Die Entwicklungsabhängigkeiten befinden sich in:

```text
requirements-dev.txt
```

Aktuell werden verwendet:

```text
pytest
boto3
botocore
pillow
gradio_client
```

Diese Abhängigkeiten werden nur für lokale Tests und CI benötigt.  
Sie sind nicht automatisch Teil jeder Lambda-Funktion.

---

## 5. Teststruktur

Die Tests befinden sich im Ordner:

```text
tests/
```

Aktuelle Struktur:

```text
tests/
├── conftest.py
├── test_generate_upload_url.py
└── test_processing_helpers.py
```

---

## 6. Getestete Bereiche

### 6.1 GenerateUploadUrl Lambda

Datei:

```text
tests/test_generate_upload_url.py
```

Diese Tests prüfen:

- Ob eine Presigned Upload URL erzeugt wird
- Ob der S3 Object Key mit `medical-input/` beginnt
- Ob Leerzeichen im Dateinamen ersetzt werden
- Ob unterstützte Bildtypen akzeptiert werden
- Ob nicht unterstützte Dateitypen abgelehnt werden

Beispiel:

```text
image/jpeg -> accepted
application/pdf -> rejected
```

---

### 6.2 Processing Helper Functions

Datei:

```text
tests/test_processing_helpers.py
```

Diese Tests prüfen:

- Umwandlung von Zahlen in `Decimal`
- Verhalten bei ungültigen Decimal-Werten
- SHA-256 Hash-Berechnung
- Direkte S3 Event-Struktur
- S3 Event innerhalb einer SQS Nachricht
- Ignorieren eines S3 Test Events

---

## 7. Warum keine echten AWS-Ressourcen im Unit Test?

Echte AWS-Ressourcen werden in Unit Tests bewusst nicht verwendet.

Stattdessen wird lokale Logik getestet.

Gründe:

- Unit Tests sollen schnell und stabil sein.
- Tests sollen ohne AWS Credentials laufen.
- Tests sollen keine Kosten erzeugen.
- AWS Academy Learner Lab kann Berechtigungen einschränken.
- Externe Dienste wie Hugging Face sollen nicht bei jedem Testlauf aufgerufen werden.

Echte End-to-End-Tests wären eine spätere Erweiterung.

---

## 8. GitHub Actions Integration

Die Tests laufen automatisch in GitHub Actions.

Workflow-Datei:

```text
.github/workflows/ci.yml
```

Der Workflow führt folgende Schritte aus:

```text
Checkout repository
Set up Python
Install AWS SAM CLI
Validate SAM template
Build SAM project
Install test dependencies
Run unit tests
Check Python syntax
```

Der relevante Testschritt im Workflow heißt `Run unit tests`.

Er führt folgenden Befehl aus:

```powershell
python -m pytest -q
```

---

## 9. Aktuelles CI-Ergebnis

Der aktuelle CI-Lauf zeigt:

```text
Build Succeeded
8 passed
```

Ein Screenshot des erfolgreichen CI-Laufs befindet sich im Ordner:

```text
screenshots/
```

Beispiel:

```text
screenshots/github-actions-unit-tests-passed.png
```

---

## 10. Grenzen der aktuellen Tests

Die aktuellen Tests prüfen bewusst nur ausgewählte Teile der Anwendung.

Nicht getestet werden derzeit:

- echter Upload in Amazon S3
- echte DynamoDB Schreib- und Leseoperationen
- echte SQS Nachrichtenverarbeitung
- echter Aufruf des Hugging Face Gradio Modells
- vollständiger End-to-End Ablauf im Browser

Diese Tests wären Integration Tests oder End-to-End Tests und könnten später ergänzt werden.

---

## 11. Fazit

Die Tests erhöhen die Qualität und Wartbarkeit des Projekts.

Zusammen mit GitHub Actions wird automatisch geprüft, ob:

- das SAM Template valide ist,
- das Projekt gebaut werden kann,
- Python-Code syntaktisch korrekt ist,
- zentrale Hilfsfunktionen korrekt funktionieren.

Damit ist das Projekt besser dokumentiert, reproduzierbarer und professioneller aufgebaut.