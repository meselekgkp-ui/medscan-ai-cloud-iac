# MedScan AI – Serverless Thorax-Röntgenanalyse auf AWS

[![MedScan AI CI](https://github.com/meselekgkp-ui/medscan-ai-cloud-iac/actions/workflows/ci.yml/badge.svg)](https://github.com/meselekgkp-ui/medscan-ai-cloud-iac/actions/workflows/ci.yml)

MedScan AI ist ein cloud-nativer, serverloser Prototyp zur Analyse von Thorax-Röntgenbildern auf AWS.

Das System ermöglicht den Upload eines Röntgenbildes über eine Weboberfläche, verarbeitet das Bild asynchron, ruft ein externes KI-Modell über Hugging Face Gradio auf, speichert das Ergebnis in DynamoDB und stellt die Auswertung anschließend über eine API bereit.

> Dieses Projekt ist ein technischer Cloud-Computing-Prototyp. Es ist kein Medizinprodukt, kein Diagnosesystem und ersetzt keine ärztliche oder fachmedizinische Beurteilung.

---

## 1. Projektziel

Ziel des Projekts ist die Umsetzung einer sicheren, skalierbaren und überwachbaren Serverless-Architektur auf AWS für einen KI-gestützten medizinischen Bildverarbeitungs-Use-Case.

Der Schwerpunkt liegt auf folgenden Themen:

- Serverless Computing mit AWS Lambda
- Statisches Webhosting mit Amazon S3
- Direkter Browser-Upload nach S3 über Presigned URLs
- Asynchrone Verarbeitung mit Amazon SQS
- Fehlerisolation durch eine Dead-Letter Queue
- Speicherung von Metadaten und KI-Ergebnissen in Amazon DynamoDB
- Automatische Datenlöschung durch DynamoDB TTL und S3 Lifecycle Rules
- Verschlüsselung ruhender Daten mit S3 Server-Side Encryption und AWS KMS
- Monitoring mit Amazon CloudWatch
- Infrastructure as Code mit AWS SAM
- Automatische Validierung über GitHub Actions CI
- Sicherheitsrelevante Eingabevalidierung
- Robuste Fehlerbehandlung bei externen KI-Modellaufrufen

---

## 2. Architekturüberblick

Das System folgt einer ereignisgesteuerten Serverless-Architektur.

```text
User / Browser
      |
      v
S3 Static Website Frontend
      |
      v
API Gateway: POST /upload-url
      |
      v
Lambda: GenerateUploadUrl
      |
      v
Presigned S3 Upload URL
      |
      v
S3 Medical Image Bucket: medical-input/
      |
      v
S3 ObjectCreated Event
      |
      v
SQS Processing Queue
      |
      v
Lambda: Processing Function
      |
      +--> Hugging Face Gradio AI Model
      |
      +--> S3 Processed Image: medical-processed/
      |
      v
DynamoDB: ImageProcessingMetadata
      |
      v
API Gateway: GET /result
      |
      v
Lambda: GetMedicalResult
      |
      v
Frontend / API Client zeigt das Ergebnis an
```

---

## 3. Verwendete AWS-Dienste

| Dienst | Aufgabe im Projekt |
|---|---|
| Amazon S3 | Hosting des statischen Frontends sowie Speicherung der hochgeladenen und verarbeiteten Bilder |
| Amazon API Gateway | Bereitstellung der HTTP-Endpunkte für Upload-URL und Ergebnisabfrage |
| AWS Lambda | Generierung der Upload-URL, Bildverarbeitung und Ergebnisabfrage |
| Amazon SQS | Entkopplung zwischen Upload und Verarbeitung |
| SQS Dead-Letter Queue | Speicherung fehlgeschlagener Nachrichten nach mehreren Verarbeitungsversuchen |
| Amazon DynamoDB | Speicherung von Metadaten, Statusinformationen und KI-Ergebnissen |
| DynamoDB TTL | Automatische Löschung alter Metadaten |
| S3 Server-Side Encryption / AWS KMS | Schutz ruhender Bilddaten |
| Amazon CloudWatch | Logs, Metriken, Dashboard und Alarme |
| AWS SAM | Beschreibung der Infrastruktur als Code |
| GitHub Actions | Automatische Validierung, Build-Prüfung und Unit Tests |

---

## 4. Aktuelle Deployment-Ressourcen

Die aktuelle AWS-SAM-Deployment-Umgebung verwendet folgende Ressourcen.

### Region

```text
us-east-1
US East (N. Virginia)
```

### CloudFormation Stack

```text
medscan-ai-iac
```

### API Gateway

```text
https://3rhly6kvse.execute-api.us-east-1.amazonaws.com/prod
```

Routen:

```text
POST /upload-url
GET /result
```

### S3 Buckets

```text
Frontend Bucket:
medical-xray-web-ayman-iac

Medical Image Bucket:
medical-xray-input-ayman-iac
```

### S3 Prefixes

```text
medical-input/
medical-processed/
```

### Lambda Functions

```text
GenerateUploadUrlFunction
ProcessingFunction
GetMedicalResultFunction
```

Beispiel für den physischen Namen der Processing Lambda:

```text
medscan-ai-processing
```

### DynamoDB

```text
Tabelle:
ImageProcessingMetadataIac

Partition Key:
id

TTL-Attribut:
expiresAt
```

### SQS

```text
Processing Queue:
medical-xray-processing-queue-iac

Dead-Letter Queue:
medical-xray-processing-dlq-iac
```

### CloudWatch Dashboard

```text
MedScanAI-Operations-Dashboard-IaC
```

---

## 5. Ablauf der Verarbeitung

### Schritt 1: Öffnen des Frontends

Der Benutzer öffnet die MedScan-AI-Weboberfläche.  
Das Frontend wird als statische Website in Amazon S3 gehostet.

### Schritt 2: Anfrage einer Upload-URL

Das Frontend ruft folgenden API-Endpunkt auf:

```http
POST /upload-url
```

API Gateway leitet die Anfrage an die Lambda-Funktion `GenerateUploadUrl` weiter.

### Schritt 3: Erstellung einer Presigned URL

Die Lambda-Funktion erstellt eine zeitlich begrenzte Presigned URL für Amazon S3.

Dadurch kann der Browser das Bild direkt in den S3 Bucket hochladen, ohne dass das Bild durch API Gateway oder Lambda übertragen werden muss.

Die Presigned URL verwendet AWS Signature Version 4, damit der Upload mit SSE-KMS kompatibel ist.

### Schritt 4: Upload des Bildes nach S3

Das Bild wird in den Prefix `medical-input/` hochgeladen.

Beispiel:

```text
medical-input/20260430-025040-93451b24-test2.jpeg
```

### Schritt 5: S3 sendet ein Event an SQS

Sobald ein neues Objekt in `medical-input/` erstellt wird, sendet Amazon S3 ein `ObjectCreated`-Event an die SQS Processing Queue.

### Schritt 6: Verarbeitung durch Lambda

Die Processing Lambda wird über ein SQS Event Source Mapping ausgelöst.

Die Funktion führt folgende Schritte aus:

- Lesen des S3 Object Keys aus dem Event
- Prüfung auf doppelte Verarbeitung durch Idempotency
- Download des Originalbildes aus S3
- Validierung von Dateityp und Dateigröße
- Berechnung eines SHA-256 Hashes
- Erstellung einer verkleinerten Bildversion
- Konvertierung problematischer Bildmodi wie `RGBA` oder `P` nach `RGB`
- Aufruf des Hugging Face Gradio KI-Modells
- Speicherung des verarbeiteten Bildes in S3
- Speicherung der Metadaten und KI-Ergebnisse in DynamoDB

### Schritt 7: Ergebnisabfrage

Das Frontend oder ein API-Client ruft folgenden Endpunkt auf:

```http
GET /result?id=<S3 object key>
```

Die Lambda-Funktion `GetMedicalResult` liest das Ergebnis aus DynamoDB und gibt es zurück.

---

## 6. KI-Modell

Das Projekt verwendet ein externes Hugging Face Gradio Space:

```text
Zakia/pneumonia-detection-with-fast.ai-and-gradio
```

Das Modell liefert Klassifikationswerte für:

```text
NORMAL
PNEUMONIA
```

Die Processing Lambda wandelt diese Werte in eine einfache Risikoklassifikation um.

| Pneumonie-Score | Ergebnis |
|---|---|
| >= 0.70 | Hohes Risiko / dringende menschliche Überprüfung |
| >= 0.40 und < 0.70 | Mittleres Risiko / menschliche Überprüfung erforderlich |
| < 0.40 | Niedriges Risiko |

Beispiel eines finalen Ergebnisses:

```text
status: COMPLETED
medicalFinding: NO_PNEUMONIA_SUSPECTED
riskLevel: LOW
topLabel: NORMAL
```

---

## 7. Sicherheitskonzept

### 7.1 Trennung der Buckets

Das Projekt trennt den Frontend Bucket vom medizinischen Bilddaten-Bucket.

```text
medical-xray-web-ayman-iac
medical-xray-input-ayman-iac
```

Der Frontend Bucket enthält nur statische Webdateien.  
Der medizinische Bucket enthält hochgeladene und verarbeitete Röntgenbilder.

### 7.2 Presigned URLs

Der Browser erhält keine dauerhaften AWS-Zugangsdaten.  
Stattdessen erhält er eine zeitlich begrenzte Presigned URL für den Upload eines bestimmten Objekts nach S3.

### 7.3 AWS Signature Version 4

Da der medizinische S3 Bucket serverseitig mit AWS KMS verschlüsselt ist, werden Presigned URLs mit AWS Signature Version 4 erzeugt.

Vor dem Fix wurde eine ältere Signaturform erzeugt, was bei SSE-KMS zu folgendem Fehler führte:

```text
Requests specifying Server Side Encryption with AWS KMS managed keys require AWS Signature Version 4.
```

Nach dem Fix enthalten die Upload URLs Parameter wie:

```text
X-Amz-Algorithm=AWS4-HMAC-SHA256
X-Amz-Signature=...
```

### 7.4 Privater medizinischer Bilddaten-Bucket

Der medizinische Bilddaten-Bucket wird nicht als öffentliche Website verwendet.  
Der Zugriff erfolgt über Presigned URLs und über Lambda-Funktionen.

### 7.5 Verschlüsselung ruhender Daten

Der medizinische S3 Bucket verwendet serverseitige Verschlüsselung mit AWS KMS.

Dadurch werden gespeicherte Bilddaten geschützt.

### 7.6 Dateinamen-Sanitization

Upload-Dateinamen werden validiert und bereinigt.

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

Dadurch werden ungewöhnliche oder gefährliche S3 Object Keys verhindert.

### 7.7 Result-ID-Validierung

Die Result API akzeptiert nur gültige IDs unter:

```text
medical-input/
```

Ungültige IDs, falsche Prefixes oder zu lange IDs werden abgelehnt.

### 7.8 Keine internen Fehlermeldungen in API Responses

Interne Exceptions werden nur in CloudWatch Logs geschrieben.  
Die API gibt stattdessen eine generische Antwort zurück:

```json
{
  "error": "Internal server error"
}
```

### 7.9 Korrekte CloudWatch Logs

Ein Copy-Paste-Fehler im `GetMedicalResult` Handler wurde korrigiert.

Vorher:

```text
Error generating upload URL
```

Korrekt:

```text
Error reading medical result
```

Dadurch sind Fehler in CloudWatch eindeutig der richtigen Lambda-Funktion zuordenbar.

### 7.10 DynamoDB TTL

DynamoDB-Einträge enthalten ein `expiresAt`-Attribut.  
Dadurch können alte Metadaten automatisch nach Ablauf der Aufbewahrungsfrist gelöscht werden.

### 7.11 S3 Lifecycle Rule

Für den medizinischen S3 Bucket ist eine Lifecycle Rule konfiguriert.  
Diese löscht alte Bildobjekte automatisch.

### 7.12 Keine echten Patientendaten

Das Projekt ist ein universitäres und technisches Demonstrationsprojekt.  
Es dürfen keine echten Patientendaten hochgeladen werden.

---

## 8. CIA+ Security Mapping

| Sicherheitsziel | Umsetzung im Projekt |
|---|---|
| Confidentiality | S3-Verschlüsselung, privater medizinischer Bucket, Presigned URLs, IAM-basierter Zugriff |
| Integrity | SHA-256 Hashes, Idempotency, DynamoDB-Metadatensätze |
| Availability | SQS Queue, Lambda Retries, DLQ, CloudWatch Alarms |
| Authenticity | API Gateway und IAM-Rollen steuern, welche Dienste welche Aktionen ausführen dürfen |
| Non-repudiation | CloudWatch Logs, Zeitstempel, DynamoDB-Einträge und Verarbeitungsstatus |

---

## 9. Zuverlässigkeitskonzept

### 9.1 Asynchrone Verarbeitung mit SQS

SQS entkoppelt den Upload von der eigentlichen Bildverarbeitung.

Ohne SQS:

```text
S3 -> Lambda
```

Mit SQS:

```text
S3 -> SQS -> Lambda
```

Dadurch wird die Architektur robuster, weil Upload und Verarbeitung nicht direkt voneinander abhängig sind.

### 9.2 Dead-Letter Queue

Wenn eine Nachricht mehrfach nicht verarbeitet werden kann, wird sie in eine Dead-Letter Queue verschoben.

Dadurch entstehen keine endlosen Wiederholungsversuche und fehlerhafte Nachrichten können gezielt untersucht werden.

### 9.3 SQS Visibility Timeout

Der SQS Visibility Timeout wurde an die Lambda-Ausführungszeit angepasst.

Die Processing Lambda hat einen Timeout von 90 Sekunden.  
Der Visibility Timeout der SQS Queue wurde auf 540 Sekunden gesetzt.

```text
90 seconds × 6 = 540 seconds
```

Dadurch wird verhindert, dass dieselbe Nachricht während einer laufenden Lambda-Ausführung zu früh erneut verarbeitet wird.

### 9.4 Idempotency

S3 Events können mehrfach zugestellt werden.  
Deshalb verwendet die Processing Lambda den S3 Object Key als DynamoDB `id`.

Vor der Verarbeitung erstellt die Lambda-Funktion einen DynamoDB-Eintrag mit:

```text
status = PROCESSING
```

Wenn dasselbe Event erneut eintrifft, erkennt die Funktion, dass das Bild bereits verarbeitet wurde oder gerade verarbeitet wird.

Dadurch werden doppelte Verarbeitung und doppelte Ergebnisdatensätze vermieden.

### 9.5 Fehlerstatus

Wenn die Verarbeitung fehlschlägt, aktualisiert die Lambda-Funktion DynamoDB mit:

```text
status = PROCESSING_FAILED
```

Danach wird der Fehler erneut ausgelöst, damit SQS die Nachricht wiederholen oder später in die DLQ verschieben kann.

### 9.6 Externer Modellaufruf mit Timeout

Der externe Hugging Face / Gradio Modellaufruf wird über einen Timeout-Wrapper abgesichert.

Dadurch wartet die Lambda-Funktion nicht unbegrenzt auf einen externen Dienst.

### 9.7 Gradio Client Lazy Singleton

Der Gradio Client wird als lazy singleton gecacht.  
Dadurch muss der Client in warmen Lambda-Containern nicht bei jeder Verarbeitung neu erstellt werden.

### 9.8 PNG/RGBA Handling

Bilder mit Modus `RGBA` oder `P` werden nach `RGB` konvertiert.

Dadurch erhält das Hugging Face Modell konsistente Bilddaten und das Risiko von Modellfehlern bei PNG-Dateien mit Transparenz wird reduziert.

---

## 10. Monitoring und Betrieb

Das Projekt enthält ein CloudWatch Dashboard und mehrere CloudWatch Alarms.

### 10.1 Lambda-Metriken

Das Dashboard überwacht:

```text
Invocations
Errors
Duration
```

### 10.2 SQS-Metriken

Das Dashboard überwacht:

```text
ApproximateNumberOfMessagesVisible
ApproximateNumberOfMessagesNotVisible
ApproximateAgeOfOldestMessage
NumberOfMessagesSent
NumberOfMessagesReceived
NumberOfMessagesDeleted
```

### 10.3 DLQ-Metriken

Das Dashboard überwacht, ob fehlgeschlagene Nachrichten in der Dead-Letter Queue vorhanden sind.

### 10.4 CloudWatch Logs

Die Processing Lambda schreibt Logs für:

```text
Start der Verarbeitung
S3 Object Key
Bildvalidierung
Hugging Face Ergebnis
DynamoDB Speicherung
Erkennung doppelter Events
Fehlerfälle
```

---

## 11. CloudWatch Alarms

| Alarm | Bedeutung |
|---|---|
| SQS Backlog Alarm | Es befinden sich sichtbare Nachrichten in der Processing Queue |
| SQS Oldest Message Alarm | Eine Nachricht wartet zu lange in der Queue |
| DLQ Alarm | Es befinden sich fehlgeschlagene Nachrichten in der Dead-Letter Queue |
| Lambda Errors Alarm | Die Processing Lambda erzeugt Fehler |
| Lambda High Duration Alarm | Die Processing Lambda benötigt ungewöhnlich lange |

---

## 12. Operational Failure Test

Zur Überprüfung des Monitorings kann der SQS Trigger der Processing Lambda temporär deaktiviert werden.

### Testszenario

```text
SQS Trigger deaktiviert
Bild über Frontend/API hochgeladen
S3 sendet Event an SQS
Lambda verarbeitet die Nachricht nicht
Nachricht bleibt sichtbar in SQS
CloudWatch Alarm wechselt in den ALARM-Zustand
```

### Erwartetes Ergebnis

```text
SQS Backlog Alarm = ALARM
```

### Wiederherstellung

Der SQS Trigger wird wieder aktiviert.  
Lambda verarbeitet die wartende Nachricht.  
Die Queue wird geleert und der Alarm kehrt in den OK-Zustand zurück.

### Nutzen dieses Tests

Der Test zeigt, dass das Monitoring nicht nur dekorativ ist.  
Es erkennt ein reales Betriebsproblem in der asynchronen Verarbeitungskette.

---

## 13. Infrastructure as Code

Die Infrastruktur ist als AWS SAM Template beschrieben.

```text
template.yaml
```

Das SAM Template definiert:

- S3 Frontend Bucket
- S3 Medical Image Bucket
- S3 Lifecycle Rule
- S3 Encryption
- S3 Event Notification zu SQS
- SQS Processing Queue
- SQS Dead-Letter Queue
- DynamoDB Tabelle mit TTL
- HTTP API Gateway
- Lambda Functions
- SQS Event Source Mapping
- CloudWatch Alarms
- CloudWatch Dashboard

Der aktuelle Stack wurde erfolgreich in AWS deployed:

```text
medscan-ai-iac
```

---

## 14. Projektstruktur

```text
medscan-ai-cloud-iac/
│   .gitignore
│   README.md
│   requirements-dev.txt
│   template.yaml
│
├── docs/
│   ├── api-contract.md
│   ├── threat-model.md
│   ├── current-resources.md
│   ├── iac-validation.md
│   └── testing.md
│
├── diagrams/
│
├── screenshots/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── tests/
│   ├── conftest.py
│   ├── test_generate_upload_url.py
│   ├── test_get_result.py
│   ├── test_gradio_failure.py
│   └── test_processing_helpers.py
│
└── src/
    ├── generate_upload_url/
    │   └── app.py
    │
    ├── get_result/
    │   └── app.py
    │
    └── processing/
        ├── app.py
        └── requirements.txt
```

---

## 15. Testing

Das Projekt verwendet `pytest` für automatisierte Unit Tests.

Aktueller Stand:

```text
19 passed
```

Testausführung:

```powershell
python -m pytest -q
```

Testliste anzeigen:

```powershell
python -m pytest --collect-only -q
```

Getestete Bereiche:

- Upload-URL-Erzeugung
- Dateitypvalidierung
- Dateinamen-Sanitization
- Result-API-Validierung
- DynamoDB-Result-Handling
- Gradio/Hugging-Face-Timeouts
- Fehlerbehandlung bei externen Modellaufrufen
- Processing-Hilfsfunktionen
- S3/SQS Event-Normalisierung
- Security Edge Cases wie Path Traversal im Dateinamen

Weitere Details befinden sich in:

```text
docs/testing.md
```

---

## 16. Finales End-to-End-Testergebnis

Die deployte AWS-Pipeline wurde erfolgreich manuell getestet.

Getesteter Ablauf:

```text
API Gateway
→ GenerateUploadUrl Lambda
→ S3 Presigned URL
→ encrypted S3 upload
→ SQS
→ Processing Lambda
→ Hugging Face / Gradio model
→ processed image in S3
→ DynamoDB
→ GetMedicalResult API
```

Finales Ergebnis:

```text
status: COMPLETED
medicalFinding: NO_PNEUMONIA_SUSPECTED
riskLevel: LOW
topLabel: NORMAL
```

Damit wurde bestätigt, dass der vollständige Serverless-Workflow erfolgreich funktioniert.

---

## 17. Continuous Integration

Das Repository verwendet GitHub Actions für eine einfache CI-Prüfung.

Bei jedem Push auf den `main` Branch wird automatisch geprüft:

- Python-Version
- SAM CLI Installation
- SAM Template Validation
- SAM Build
- Python Syntax Check
- Unit Tests mit pytest

Die Workflow-Datei befindet sich unter:

```text
.github/workflows/ci.yml
```

Dadurch wird sichergestellt, dass das SAM-Projekt weiterhin validierbar und baubar ist.

---

## 18. Lokale Voraussetzungen

Die lokale Entwicklungsumgebung verwendet:

```text
Windows
PowerShell
Python 3.11
AWS SAM CLI
Git
```

SAM CLI prüfen:

```powershell
sam --version
```

AWS Region setzen:

```powershell
$env:AWS_DEFAULT_REGION="us-east-1"
$env:AWS_REGION="us-east-1"
```

Optional: SAM Telemetry deaktivieren:

```powershell
$env:SAM_CLI_TELEMETRY="0"
```

---

## 19. Entwicklungsabhängigkeiten installieren

Für lokale Tests:

```powershell
python -m pip install -r requirements-dev.txt
```

Für die Processing Lambda liegen die Runtime-Abhängigkeiten zusätzlich in:

```text
src/processing/requirements.txt
```

---

## 20. SAM Template validieren

Befehl:

```powershell
sam validate --template-file template.yaml --region us-east-1
```

Erwartetes Ergebnis:

```text
template.yaml is a valid SAM Template
```

---

## 21. SAM Projekt bauen

Befehl:

```powershell
sam build --template-file template.yaml
```

Erwartetes Ergebnis:

```text
Build Succeeded

Built Artifacts  : .aws-sam\build
Built Template   : .aws-sam\build\template.yaml
```

---

## 22. Deployment

Das Projekt wurde erfolgreich mit AWS SAM deployed.

Standardbefehl nach der ersten Konfiguration:

```powershell
sam deploy
```

Erwartetes Ergebnis bei unverändertem Stack:

```text
No changes to deploy. Stack medscan-ai-iac is up to date.
```

Falls das Projekt neu deployed werden soll:

```powershell
sam deploy --guided --region us-east-1
```

Wichtige Parameter:

```text
Stack Name: medscan-ai-iac
Region: us-east-1
ExistingLambdaRoleArn: arn:aws:iam::<account-id>:role/LabRole
```

Hinweis: In AWS Academy Learner Lab können bestimmte IAM- und CloudFormation-Berechtigungen eingeschränkt sein. Das Projekt verwendet deshalb einen vorhandenen LabRole-ARN.

---

## 23. Nützliche lokale Befehle

### Tests ausführen

```powershell
python -m pytest -q
```

### Testliste anzeigen

```powershell
python -m pytest --collect-only -q
```

### AWS Identität prüfen

```powershell
aws sts get-caller-identity
```

### Stack Outputs anzeigen

```powershell
aws cloudformation describe-stacks `
  --stack-name medscan-ai-iac `
  --region us-east-1 `
  --query "Stacks[0].Outputs" `
  --output table
```

### S3 Inhalte prüfen

```powershell
aws s3 ls s3://medical-xray-input-ayman-iac --recursive --region us-east-1
```

### Processing Lambda Logs lesen

```powershell
aws logs tail "/aws/lambda/medscan-ai-processing" --since 10m --region us-east-1
```

### Result API testen

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "$API/result?id=$([uri]::EscapeDataString($resultId))"
```

### Invalid Filename Test

```powershell
try {
  Invoke-WebRequest `
    -Method POST `
    -Uri "$API/upload-url" `
    -ContentType "application/json" `
    -Body '{"filename":"../../../../etc/test.jpeg","contentType":"image/jpeg"}' `
    -ErrorAction Stop
}
catch {
  $_.Exception.Response.StatusCode.value__
  $_.ErrorDetails.Message
}
```

Erwartetes Ergebnis:

```text
400
{"error": "Invalid filename", "message": "Filename must not contain path separators, '..', or unsafe characters."}
```

---

## 24. Wichtige behobene Fehler

### 24.1 Falsche Logmeldung in GetMedicalResult

Problem:

```text
Error generating upload URL
```

Diese Meldung stand fälschlicherweise im `get_result` Handler.

Fix:

```text
Error reading medical result
```

Nutzen:

- bessere CloudWatch Logs
- schnellere Fehlersuche
- keine Verwechslung mit GenerateUploadUrl Lambda

### 24.2 PNG/RGBA Verarbeitung

Problem:

Bilder mit `RGBA` oder `P` Modus wurden nicht immer in `RGB` konvertiert.

Fix:

```text
RGBA/P images -> RGB
```

Nutzen:

- stabilere Bildverarbeitung
- weniger Modellfehler bei PNG-Dateien
- konsistentere Eingaben für das KI-Modell

### 24.3 Presigned URL Signature Version

Problem:

Presigned URLs mit alter Signatur funktionierten nicht mit SSE-KMS.

Fix:

```text
AWS Signature Version 4
```

Nutzen:

- Uploads in KMS-verschlüsselte Buckets funktionieren korrekt

### 24.4 Unsichere Dateinamen

Problem:

Ein Dateiname wie:

```text
../../../../etc/test.jpeg
```

konnte zu ungewöhnlichen S3 Object Keys führen.

Fix:

```text
Filename Sanitization
```

Nutzen:

- saubere Object Keys
- weniger Missbrauchspotenzial
- bessere Eingabevalidierung

### 24.5 Gradio/Hugging Face Timeout

Problem:

Ein externer Modellaufruf könnte hängen.

Fix:

```text
Timeout Wrapper
```

Nutzen:

- Lambda hängt nicht unbegrenzt
- Fehlerfälle werden kontrolliert behandelt

### 24.6 Gradio Client wird gecacht

Problem:

Der Gradio Client wurde bei jedem Bild neu erstellt.

Fix:

```text
Lazy Singleton Cache
```

Nutzen:

- bessere Performance in warmen Lambda-Containern
- weniger unnötige Initialisierung

### 24.7 Processing Result Handling

Problem:

Nach einem erfolgreichen Gradio-Aufruf wurde versehentlich eine Error-Variable verwendet.

Fix:

```text
Success path uses real model result
Failure path uses safe fallback result
```

Nutzen:

- erfolgreiche Modellantworten werden korrekt als `COMPLETED` gespeichert
- Fehlerfälle werden sauber als `MODEL_ERROR` behandelt

---

## 25. Warum diese Dienste verwendet wurden

### Warum Amazon S3?

S3 eignet sich für statisches Webhosting und Objektspeicherung.  
Das Frontend ist statisch und Röntgenbilder sind objektbasierte Dateien.

### Warum API Gateway?

API Gateway stellt einfache HTTP-Endpunkte für die Kommunikation zwischen Frontend und Backend bereit.

### Warum AWS Lambda?

Lambda passt gut zum ereignisgesteuerten Verarbeitungsmodell und vermeidet Serveradministration.

### Warum Amazon SQS?

SQS entkoppelt Upload und Verarbeitung.  
Dadurch wird die Architektur robuster und fehlertoleranter.

### Warum DynamoDB?

DynamoDB eignet sich für Metadaten und Statusinformationen, die über einen eindeutigen Schlüssel abgefragt werden.

### Warum CloudWatch?

CloudWatch bietet Logs, Metriken, Dashboards und Alarme für den Betrieb und die Überwachung.

### Warum AWS SAM?

SAM macht die Serverless-Architektur reproduzierbar, versionierbar und dokumentierbar.

### Warum GitHub Actions?

GitHub Actions überprüft automatisch, ob das SAM Template valide ist, das Projekt gebaut werden kann und die automatisierten Tests erfolgreich sind.

---

## 26. Warum bestimmte Dienste nicht verwendet wurden

### Warum nicht EC2?

EC2 würde Serveradministration, Betriebssystempflege, Skalierung und Patching erfordern.  
Für diesen ereignisgesteuerten Prototyp ist Lambda einfacher und passender.

### Warum nicht RDS?

Das Projekt speichert Metadaten anhand eines eindeutigen Object Keys.  
Es sind keine relationalen Joins oder komplexen Transaktionen erforderlich.  
DynamoDB ist deshalb ausreichend und serverlos.

### Warum nicht nur direkt S3 zu Lambda?

Eine direkte Verbindung von S3 zu Lambda funktioniert grundsätzlich.  
SQS ergänzt jedoch Pufferung, Wiederholungslogik und Fehlerisolation.

### Warum kein CloudFront in der aktuellen Demo?

CloudFront wäre für eine Produktionsumgebung sinnvoll, da es HTTPS und Edge Caching unterstützt.  
In der aktuellen AWS Academy Umgebung wurde die einfache S3 Static Website Variante verwendet.

Mögliche Production-Verbesserung:

```text
CloudFront + HTTPS + Origin Access Control
```

### Warum keine private VPC?

Die verwendeten Serverless-Dienste benötigen für diesen Prototyp keine privaten Subnetze.  
Eine VPC würde die Architektur komplexer machen, ohne für diesen Use Case einen klaren Nutzen zu bringen.

---

## 27. Einschränkungen

Dieses Projekt ist ein Prototyp und hat folgende Einschränkungen:

- Es ist kein Medizinprodukt.
- Es liefert keine klinische Diagnose.
- Das KI-Modell wird extern über Hugging Face aufgerufen.
- Der S3 Website Endpoint verwendet in der aktuellen Demo HTTP.
- Es gibt noch keine Benutzeranmeldung.
- Es dürfen keine echten Patientendaten hochgeladen werden.
- Die GitHub Actions CI validiert, baut und testet das Projekt, führt aber kein AWS Deployment aus.
- Die API-Endpunkte sind für den Prototyp öffentlich erreichbar.
- Für eine produktionsnahe Version wären Authentifizierung, Autorisierung und Rate Limiting notwendig.

---

## 28. Mögliche Weiterentwicklungen

Mögliche Verbesserungen für eine produktionsnähere Version:

- Amazon CloudFront mit HTTPS
- Amazon Cognito für Benutzeranmeldung
- Benutzerbezogene Ergebniszugriffe
- API Gateway Authorizer
- Rate Limiting / Usage Plans / AWS WAF
- Eigene Domain mit ACM-Zertifikat
- Hosting des KI-Modells innerhalb von AWS, zum Beispiel mit Amazon SageMaker
- Strukturierte JSON Logs mit Correlation IDs
- Vollautomatisierte Integration Tests
- CI/CD Deployment Pipeline mit GitHub Actions
- Stärkere IAM Least-Privilege-Rollen
- Modellbewertung mit Accuracy, False Positives und False Negatives
- CloudWatch Synthetics Canary für API-Verfügbarkeit

---

## 29. Medizinischer Hinweis

Dieses Projekt dient ausschließlich Bildungs- und Demonstrationszwecken.

Das KI-Ergebnis ist nur eine technische Vorhersage und keine medizinische Diagnose.  
Alle Ergebnisse müssen von qualifiziertem medizinischem Fachpersonal überprüft werden, bevor medizinische Entscheidungen getroffen werden.

---

## 30. Projektstatus

Aktueller Stand:

```text
Funktionierende Serverless-Pipeline implementiert
S3 Frontend funktioniert
API Gateway Routen funktionieren
Presigned Upload mit Signature V4 funktioniert
S3 SSE-KMS Upload funktioniert
SQS Processing Queue funktioniert
Processing Lambda funktioniert
Hugging Face / Gradio Modellaufruf funktioniert
Processed Image Speicherung funktioniert
DynamoDB Ergebnispeicherung funktioniert
GetMedicalResult API funktioniert
DynamoDB TTL implementiert
S3 Lifecycle Rule implementiert
CloudWatch Dashboard implementiert
CloudWatch Alarms implementiert
Idempotency implementiert
Filename Sanitization implementiert
Result ID Validation implementiert
Gradio Timeout implementiert
Gradio Client Lazy Singleton implementiert
PNG/RGBA Handling implementiert
Infrastructure as Code implementiert
SAM Validation erfolgreich
SAM Build erfolgreich
SAM Deployment erfolgreich
GitHub Actions CI erfolgreich
Unit Tests: 19 passed
End-to-End Test erfolgreich
```

---

## 31. Autor

```text
Ayman Meseleklayame
Master Wirtschaftsinformatik
Cloud Computing Portfolio Project
Technische Hochschule Deggendorf
Summer Term 2026
```