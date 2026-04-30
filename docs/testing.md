# Testing – MedScan AI

Dieses Dokument beschreibt die Teststrategie und die finalen Testergebnisse des Projekts **MedScan AI**.

Ziel der Tests ist es, zentrale Hilfsfunktionen, API-Logik, Fehlerbehandlung und sicherheitsrelevante Eingabevalidierung automatisiert zu überprüfen, ohne echte AWS-Ressourcen in Unit Tests aufzurufen.

---

## 1. Überblick

Das Projekt verwendet `pytest` für automatisierte Unit Tests.

Die Tests werden lokal ausgeführt und können zusätzlich über GitHub Actions geprüft werden.

Aktueller Stand:

```text
19 passed
```

Die Tests prüfen unter anderem:

- Upload-URL-Erzeugung
- Dateitypvalidierung
- Dateinamen-Sanitization
- Result-API-Validierung
- DynamoDB-Result-Handling
- Gradio/Hugging-Face-Timeouts
- Fehlerbehandlung bei externen Modellaufrufen
- Processing-Hilfsfunktionen
- S3/SQS Event-Normalisierung

---

## 2. Warum Unit Tests?

Unit Tests prüfen kleine, isolierte Teile der Anwendung.

In diesem Projekt werden in Unit Tests keine echten S3 Buckets, DynamoDB Tabellen oder SQS Queues verwendet. Stattdessen werden zentrale Logikbausteine lokal geprüft.

Das hat mehrere Vorteile:

- Tests laufen schnell.
- Tests verursachen keine AWS-Kosten.
- Tests benötigen keine echten AWS-Zugangsdaten.
- Fehler in Hilfsfunktionen werden früh erkannt.
- Sicherheitsrelevante Eingaben können reproduzierbar geprüft werden.
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
19 passed
```

Optional kann die Testliste angezeigt werden:

```powershell
python -m pytest --collect-only -q
```

---

## 4. Test Dependencies

Die Entwicklungsabhängigkeiten befinden sich in:

```text
requirements-dev.txt
```

Aktuell werden unter anderem verwendet:

```text
pytest
boto3
botocore
pillow
gradio_client
```

Diese Abhängigkeiten werden nur für lokale Tests und CI benötigt. Sie sind nicht automatisch Teil jeder Lambda-Funktion.

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
├── test_get_result.py
├── test_gradio_failure.py
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

- ob eine Presigned Upload URL erzeugt wird
- ob der S3 Object Key mit `medical-input/` beginnt
- ob Leerzeichen im Dateinamen ersetzt werden
- ob unterstützte Bildtypen akzeptiert werden
- ob nicht unterstützte Dateitypen abgelehnt werden
- ob gefährliche Dateinamen mit Pfad-Traversal blockiert werden

Beispiele:

```text
image/jpeg -> accepted
application/pdf -> rejected
../../../../etc/test.jpeg -> rejected
```

Die Dateinamen-Sanitization verhindert ungewöhnliche oder gefährliche S3 Object Keys wie:

```text
medical-input/../../../../etc/test.jpeg
```

---

### 6.2 GetMedicalResult Lambda

Datei:

```text
tests/test_get_result.py
```

Diese Tests prüfen:

- fehlender `id` Parameter führt zu HTTP 400
- ungültiger `id` Parameter führt zu HTTP 400
- nicht vorhandene Ergebnisse führen zu HTTP 404
- vorhandene DynamoDB-Ergebnisse werden korrekt zurückgegeben
- gültige `medical-input/` IDs werden akzeptiert
- falsche Prefixes werden abgelehnt

Damit wird verhindert, dass beliebige oder unsichere IDs an die Result-API übergeben werden.

---

### 6.3 Gradio / Hugging Face Fehlerbehandlung

Datei:

```text
tests/test_gradio_failure.py
```

Diese Tests prüfen:

- erfolgreicher Aufruf über den Timeout-Wrapper
- Timeout beim externen Modellaufruf
- Fehler beim externen Modellaufruf
- Erzeugung eines sicheren Fallback-Ergebnisses bei Modellfehlern

Das Ziel ist, dass die Processing Lambda nicht unkontrolliert hängt, wenn Hugging Face oder Gradio langsam oder nicht verfügbar ist.

---

### 6.4 Processing Helper Functions

Datei:

```text
tests/test_processing_helpers.py
```

Diese Tests prüfen:

- Umwandlung von Zahlen in `Decimal`
- Verhalten bei ungültigen Decimal-Werten
- SHA-256 Hash-Berechnung
- direkte S3 Event-Struktur
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
- Fehler sollen reproduzierbar und unabhängig von Netzwerken oder Cloud-Zustand sein.

Echte End-to-End-Tests werden separat manuell gegen die deployte AWS-Infrastruktur durchgeführt.

---

## 8. GitHub Actions Integration

Die Tests laufen automatisch in GitHub Actions.

Workflow-Datei:

```text
.github/workflows/ci.yml
```

Der Workflow führt typischerweise folgende Schritte aus:

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

Der relevante Testschritt heißt:

```text
Run unit tests
```

und führt folgenden Befehl aus:

```powershell
python -m pytest -q
```

---

## 9. Finales lokales Testergebnis

Der finale lokale Testlauf zeigt:

```text
19 passed
```

Zusätzlich wurde das SAM-Projekt erfolgreich gebaut:

```text
Build Succeeded
```

Der finale Deploy-Check zeigte:

```text
No changes to deploy. Stack medscan-ai-iac is up to date.
```

---

## 10. End-to-End-Test der AWS-Pipeline

Neben den Unit Tests wurde die deployte AWS-Pipeline manuell getestet.

Getesteter Ablauf:

```text
API Gateway
→ GenerateUploadUrl Lambda
→ S3 Presigned URL
→ S3 Upload mit SSE-KMS
→ S3 Event
→ SQS Queue
→ Processing Lambda
→ Hugging Face / Gradio Modell
→ processed image in S3
→ DynamoDB metadata
→ GetMedicalResult API
```

Der finale API-Result-Test lieferte:

```text
status: COMPLETED
medicalFinding: NO_PNEUMONIA_SUSPECTED
riskLevel: LOW
topLabel: NORMAL
```

Damit wurde bestätigt, dass der vollständige Serverless-Workflow erfolgreich funktioniert.

---

## 11. Sicherheitsrelevante Tests und Fixes

Im Projekt wurden mehrere sicherheitsrelevante Punkte umgesetzt und getestet:

### 11.1 AWS Signature Version 4

Da der S3 Bucket serverseitig mit AWS KMS verschlüsselt wird, müssen Presigned URLs mit AWS Signature Version 4 erzeugt werden.

Umgesetzt in:

```text
src/generate_upload_url/app.py
```

### 11.2 Filename Sanitization

Gefährliche Dateinamen wie:

```text
../../../../etc/test.jpeg
```

werden mit HTTP 400 abgelehnt.

Erwartete Antwort:

```json
{
  "error": "Invalid filename",
  "message": "Filename must not contain path separators, '..', or unsafe characters."
}
```

### 11.3 Keine internen Fehlermeldungen in API Responses

Interne Exceptions werden nur in CloudWatch Logs geschrieben.

Die API gibt stattdessen eine generische Antwort zurück:

```json
{
  "error": "Internal server error"
}
```

### 11.4 Result-ID-Validierung

Die Result API akzeptiert nur IDs unter:

```text
medical-input/
```

Dadurch werden ungültige oder unerwartete IDs abgelehnt.

### 11.5 Gradio Timeout

Der externe Hugging Face / Gradio Modellaufruf wird über einen Timeout-Wrapper abgesichert.

Dadurch wartet die Lambda-Funktion nicht unbegrenzt auf einen externen Dienst.

### 11.6 SQS Visibility Timeout

Der SQS Visibility Timeout wurde an die Lambda-Ausführungszeit angepasst, um doppelte Verarbeitung während langer Lambda-Laufzeiten zu vermeiden.

### 11.7 PNG/RGBA-Verarbeitung

Bilder mit `RGBA` oder `P` Modus werden in `RGB` konvertiert, damit das Modell konsistente Eingaben erhält.

---

## 12. Grenzen der aktuellen Tests

Die Unit Tests prüfen bewusst nur ausgewählte Teile der Anwendung.

Nicht vollständig automatisiert getestet werden derzeit:

- echter Upload in Amazon S3
- echte DynamoDB Schreib- und Leseoperationen in CI
- echte SQS Nachrichtenverarbeitung in CI
- echter Aufruf des Hugging Face Gradio Modells in CI
- vollständiger Browser-End-to-End-Test

Diese Punkte wurden manuell gegen die deployte AWS-Infrastruktur getestet.

---

## 13. Fazit

Die Tests erhöhen die Qualität und Wartbarkeit des Projekts.

Zusammen mit GitHub Actions wird automatisch geprüft, ob:

- das SAM Template valide ist,
- das Projekt gebaut werden kann,
- Python-Code syntaktisch korrekt ist,
- zentrale Hilfsfunktionen korrekt funktionieren,
- sicherheitsrelevante Eingaben validiert werden,
- Fehlerfälle kontrolliert behandelt werden.

Der finale Stand ist:

```text
19 passed
SAM build succeeded
AWS stack up to date
End-to-end pipeline completed successfully
```

Damit ist das Projekt besser dokumentiert, reproduzierbarer und professioneller aufgebaut.