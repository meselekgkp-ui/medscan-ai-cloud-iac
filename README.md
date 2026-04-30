# MedScan AI – Serverless Thorax-Röntgenanalyse auf AWS

[![MedScan AI CI](https://github.com/meselekgkp-ui/medscan-ai-cloud-iac/actions/workflows/ci.yml/badge.svg)](https://github.com/meselekgkp-ui/medscan-ai-cloud-iac/actions/workflows/ci.yml)

MedScan AI ist ein cloud-nativer, serverloser Prototyp zur Analyse von Thorax-Röntgenbildern auf AWS.

Das System ermöglicht den Upload eines Röntgenbildes über eine Weboberfläche, verarbeitet das Bild asynchron, ruft ein externes KI-Modell über Hugging Face Gradio auf, speichert das Ergebnis in DynamoDB und stellt die Auswertung anschließend über eine API bereit.

> Dieses Projekt ist ein technischer Cloud-Computing-Prototyp. Es ist kein Medizinprodukt, kein klinisches Diagnosesystem und ersetzt keine ärztliche oder fachmedizinische Beurteilung.

---

## 1. Projektziel

Ziel des Projekts ist die Umsetzung einer sicheren, skalierbaren und überwachbaren Serverless-Architektur auf AWS für einen KI-gestützten medizinischen Bildverarbeitungs-Use-Case.

Der Schwerpunkt liegt auf:

- Serverless Computing mit AWS Lambda
- Statischem Webhosting mit Amazon S3
- Direktem Browser-Upload nach S3 über Presigned URLs
- Asynchroner Verarbeitung mit Amazon SQS
- Fehlerisolation durch eine Dead-Letter Queue
- Speicherung von Metadaten und KI-Ergebnissen in Amazon DynamoDB
- Automatischer Datenlöschung durch DynamoDB TTL und S3 Lifecycle Rules
- Verschlüsselung ruhender Daten mit S3 Server-Side Encryption und AWS KMS
- Monitoring mit Amazon CloudWatch
- Infrastructure as Code mit AWS SAM
- Automatisierter Validierung über GitHub Actions CI
- Sicherheitsrelevanter Eingabevalidierung
- Robuster Fehlerbehandlung bei externen KI-Modellaufrufen

---

## 2. Architekturüberblick

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
| Amazon S3 | Hosting des Frontends sowie Speicherung der hochgeladenen und verarbeiteten Bilder |
| Amazon API Gateway | HTTP-Endpunkte für Upload-URL und Ergebnisabfrage |
| AWS Lambda | Upload-URL-Erzeugung, Bildverarbeitung und Ergebnisabfrage |
| Amazon SQS | Entkopplung zwischen Upload und Verarbeitung |
| SQS Dead-Letter Queue | Fehlerisolation nach mehrfach fehlgeschlagener Verarbeitung |
| Amazon DynamoDB | Speicherung von Metadaten, Statusinformationen und KI-Ergebnissen |
| DynamoDB TTL | Automatische Löschung alter Metadaten |
| S3 SSE-KMS | Verschlüsselung ruhender Bilddaten |
| Amazon CloudWatch | Logs, Metriken, Dashboard und Alarme |
| AWS SAM | Infrastructure as Code |
| GitHub Actions | CI-Prüfung mit Build, Validierung und Tests |

---

## 4. Deployment-Umgebung

Die Anwendung wurde in einer AWS Academy Learner Lab Umgebung getestet und deployed.

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

## 5. Verarbeitungsablauf

1. Der Benutzer öffnet das S3 Static Website Frontend.
2. Das Frontend ruft `POST /upload-url` auf.
3. Die Lambda-Funktion `GenerateUploadUrl` erzeugt eine zeitlich begrenzte Presigned S3 Upload URL.
4. Das Bild wird direkt in den Prefix `medical-input/` im medizinischen S3 Bucket hochgeladen.
5. S3 sendet ein `ObjectCreated` Event an die SQS Processing Queue.
6. Die Processing Lambda wird durch SQS ausgelöst.
7. Die Processing Lambda validiert das Bild, berechnet Hashes, erstellt eine verkleinerte Version und ruft das Hugging Face Gradio Modell auf.
8. Das verarbeitete Bild wird unter `medical-processed/` gespeichert.
9. Das Ergebnis wird in DynamoDB gespeichert.
10. Über `GET /result?id=<S3 object key>` kann das Ergebnis abgefragt werden.

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

Beispiel eines finalen Testergebnisses:

```text
status: COMPLETED
medicalFinding: NO_PNEUMONIA_SUSPECTED
riskLevel: LOW
topLabel: NORMAL
```

---

## 7. Sicherheitskonzept

### Presigned URLs

Der Browser erhält keine dauerhaften AWS-Zugangsdaten. Stattdessen wird eine zeitlich begrenzte Presigned URL erzeugt.

### AWS Signature Version 4

Da der medizinische S3 Bucket mit AWS KMS verschlüsselt ist, werden Presigned URLs mit AWS Signature Version 4 erzeugt.

Vor dem Fix führte eine ältere Signaturform zu folgendem Fehler:

```text
Requests specifying Server Side Encryption with AWS KMS managed keys require AWS Signature Version 4.
```

Nach dem Fix enthalten die Upload URLs Parameter wie:

```text
X-Amz-Algorithm=AWS4-HMAC-SHA256
X-Amz-Signature=...
```

### Filename Sanitization

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

### Result-ID-Validierung

Die Result API akzeptiert nur gültige IDs unter:

```text
medical-input/
```

Ungültige IDs, falsche Prefixes oder zu lange IDs werden abgelehnt.

### Keine internen Fehlermeldungen in API Responses

Interne Exceptions werden nur in CloudWatch Logs geschrieben. Die API gibt stattdessen generische Fehlerantworten zurück:

```json
{
  "error": "Internal server error"
}
```

### Datenlöschung

Das Projekt verwendet:

- DynamoDB TTL über das Attribut `expiresAt`
- S3 Lifecycle Rule zur automatischen Löschung alter Bildobjekte

### Keine echten Patientendaten

Das Projekt ist ein universitäres und technisches Demonstrationsprojekt. Es dürfen keine echten Patientendaten hochgeladen werden.

---

## 8. CIA+ Security Mapping

| Sicherheitsziel | Umsetzung |
|---|---|
| Confidentiality | S3-Verschlüsselung, privater medizinischer Bucket, Presigned URLs, IAM-basierter Zugriff |
| Integrity | SHA-256 Hashes, Idempotency, DynamoDB-Metadaten |
| Availability | SQS Queue, Lambda Retries, DLQ, CloudWatch Alarms |
| Authenticity | API Gateway und IAM-Rollen steuern Dienstzugriffe |
| Non-repudiation | CloudWatch Logs, Zeitstempel und DynamoDB-Verarbeitungsstatus |

---

## 9. Zuverlässigkeit und Fehlerbehandlung

### SQS-Entkopplung

Die Architektur nutzt:

```text
S3 -> SQS -> Lambda
```

statt einer direkten Kopplung:

```text
S3 -> Lambda
```

Dadurch wird die Verarbeitung robuster und fehlertoleranter.

### Dead-Letter Queue

Fehlgeschlagene Nachrichten werden nach mehreren Versuchen in eine DLQ verschoben.

### SQS Visibility Timeout

Die Processing Lambda hat einen Timeout von 90 Sekunden. Der SQS Visibility Timeout wurde auf 540 Sekunden gesetzt.

```text
90 seconds × 6 = 540 seconds
```

Dadurch wird verhindert, dass dieselbe Nachricht zu früh erneut verarbeitet wird.

### Idempotency

Die Processing Lambda verwendet den S3 Object Key als DynamoDB `id`.

Vor der Verarbeitung wird ein Eintrag mit folgendem Status erstellt:

```text
PROCESSING
```

Dadurch werden doppelte S3 Events erkannt und doppelte Verarbeitung wird vermieden.

### Gradio Timeout

Der externe Hugging Face / Gradio Modellaufruf ist mit einem Timeout-Wrapper abgesichert.

### Gradio Client Lazy Singleton

Der Gradio Client wird als lazy singleton gecacht. Dadurch muss der Client in warmen Lambda-Containern nicht bei jeder Verarbeitung neu erstellt werden.

### PNG/RGBA Handling

Bilder mit Modus `RGBA` oder `P` werden nach `RGB` konvertiert. Dadurch erhält das Modell konsistente Bilddaten.

---

## 10. Monitoring

Das Projekt enthält ein CloudWatch Dashboard und mehrere Alarme.

Überwacht werden unter anderem:

```text
Lambda Invocations
Lambda Errors
Lambda Duration
SQS visible messages
SQS not visible messages
SQS oldest message age
DLQ messages
```

CloudWatch Logs dokumentieren:

```text
Start der Verarbeitung
S3 Object Key
Bildvalidierung
Hugging Face Ergebnis
DynamoDB Speicherung
Duplicate Detection
Fehlerfälle
```

---

## 11. Infrastructure as Code

Die Infrastruktur ist als AWS SAM Template beschrieben:

```text
template.yaml
```

Das Template definiert:

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

Der aktuelle Stack wurde manuell mit AWS SAM deployed:

```text
medscan-ai-iac
```

---

## 12. GitHub, CI und Deployment

GitHub dient in diesem Projekt als Source-of-Truth für:

- Anwendungscode
- Infrastructure as Code
- Unit Tests
- technische Dokumentation
- GitHub Actions CI

GitHub Actions führt aktuell Continuous Integration aus:

- SAM Template Validation
- SAM Build
- Python Syntax Check
- Unit Tests mit pytest

GitHub Actions führt aktuell kein automatisches AWS Deployment aus.

Das Deployment erfolgt manuell mit AWS SAM:

```powershell
sam build
sam deploy
```

Grund dafür ist die AWS Academy Learner Lab Umgebung. Diese verwendet temporäre Credentials und eingeschränkte IAM-/CloudFormation-Berechtigungen. Dadurch ist eine stabile automatische CD-Pipeline von GitHub nach AWS in diesem Projekt nicht sinnvoll umgesetzt worden.

Der Zusammenhang ist daher:

```text
GitHub = Code, Tests, Dokumentation, IaC
AWS = Laufende Cloud-Infrastruktur
SAM deploy = manuelle Brücke zwischen GitHub-Code und AWS-Umgebung
```

---

## 13. Projektstruktur

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
    ├── get_result/
    │   └── app.py
    └── processing/
        ├── app.py
        └── requirements.txt
```

---

## 14. Testing

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

## 15. Finales End-to-End-Testergebnis

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

## 16. Lokale Voraussetzungen

```text
Windows
PowerShell
Python 3.11
AWS SAM CLI
Git
```

AWS Region setzen:

```powershell
$env:AWS_DEFAULT_REGION="us-east-1"
$env:AWS_REGION="us-east-1"
```

Tests ausführen:

```powershell
python -m pytest -q
```

SAM validieren:

```powershell
sam validate --template-file template.yaml --region us-east-1
```

SAM bauen:

```powershell
sam build --template-file template.yaml
```

Deploy nach der ersten Konfiguration:

```powershell
sam deploy
```

Erwartetes Ergebnis bei unverändertem Stack:

```text
No changes to deploy. Stack medscan-ai-iac is up to date.
```

---

## 17. Nützliche Befehle

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

## 18. Wichtige behobene Fehler

### 18.1 Falsche Logmeldung in GetMedicalResult

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
- weniger Verwechslung zwischen GenerateUploadUrl und GetMedicalResult
- einfacheres Debugging

### 18.2 PNG/RGBA Verarbeitung

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

### 18.3 Presigned URL Signature Version

Problem:

Presigned URLs mit alter Signatur funktionierten nicht mit SSE-KMS.

Fix:

```text
AWS Signature Version 4
```

Nutzen:

- Uploads in KMS-verschlüsselte Buckets funktionieren korrekt

### 18.4 Unsichere Dateinamen

Problem:

Ein Dateiname wie `../../../../etc/test.jpeg` konnte zu ungewöhnlichen S3 Object Keys führen.

Fix:

```text
Filename Sanitization
```

Nutzen:

- saubere Object Keys
- weniger Missbrauchspotenzial
- bessere Eingabevalidierung

### 18.5 Gradio/Hugging Face Timeout

Problem:

Ein externer Modellaufruf konnte hängen.

Fix:

```text
Timeout Wrapper
```

Nutzen:

- Lambda hängt nicht unbegrenzt
- Fehlerfälle werden kontrolliert behandelt

### 18.6 Gradio Client Performance

Problem:

Der Gradio Client wurde bei jedem Bild neu erstellt.

Fix:

```text
Lazy Singleton Cache
```

Nutzen:

- bessere Performance in warmen Lambda-Containern
- weniger unnötige Initialisierung

### 18.7 Processing Result Handling

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

## 19. Was bewusst nicht umgesetzt wurde

### Kein automatisches GitHub-to-AWS Deployment

Es wurde keine vollständige CD-Pipeline eingerichtet.

Grund:

Die AWS Academy Learner Lab Umgebung nutzt temporäre Credentials und eingeschränkte IAM-Berechtigungen. Eine stabile automatische Deployment-Pipeline über GitHub Actions wäre dadurch unzuverlässig und für dieses Portfolio-Projekt nicht notwendig.

Stattdessen:

```text
GitHub Actions = CI, Build, Tests
AWS SAM = manuelles Deployment
```

### Kein CloudFront

CloudFront wäre für eine produktionsnahe Version sinnvoll, besonders für HTTPS, Caching und einen professionellen Webzugriff.

Grund für Nicht-Umsetzung:

Für den Prototyp wurde der einfache S3 Static Website Endpoint verwendet. In der AWS Academy Umgebung war die zusätzliche CloudFront-Konfiguration nicht der Schwerpunkt.

Mögliche Verbesserung:

```text
CloudFront + HTTPS + Origin Access Control
```

### Keine Benutzeranmeldung

Es wurde keine Authentifizierung mit Amazon Cognito umgesetzt.

Grund:

Der Fokus lag auf der Serverless-Verarbeitungskette, S3 Uploads, SQS, Lambda, DynamoDB, Monitoring und IaC.

Mögliche Verbesserung:

```text
Amazon Cognito + API Gateway Authorizer
```

### Kein Rate Limiting / WAF

Rate Limiting oder AWS WAF wurden nicht umgesetzt.

Grund:

Für den universitären Prototyp lag der Schwerpunkt auf Architektur, Verarbeitung, Security Basics und Monitoring.

Mögliche Verbesserung:

```text
API Gateway Usage Plans
AWS WAF
Request throttling
```

### Kein internes Modellhosting in AWS

Das KI-Modell wird extern über Hugging Face Gradio aufgerufen.

Grund:

Der Fokus lag auf Cloud-Integration und Serverless-Orchestrierung, nicht auf Training oder Hosting eines eigenen medizinischen Modells.

Mögliche Verbesserung:

```text
Amazon SageMaker Endpoint
```

### Keine private VPC

Die Lambda-Funktionen wurden nicht in eine private VPC gelegt.

Grund:

Die verwendeten Serverless-Dienste benötigen für diesen Prototyp keine privaten Subnetze. Eine VPC hätte zusätzliche Komplexität erzeugt, ohne für diesen Use Case einen klaren Mehrwert zu liefern.

---

## 20. AI-Assisted Review and Development Note

Während der Entwicklung wurde ein KI-Assistent, darunter Claude, unterstützend eingesetzt.

Die KI-Unterstützung wurde verwendet für:

- Code Review
- Erkennung möglicher Sicherheits- und Logikfehler
- Vorschläge für zusätzliche Unit Tests
- Verbesserung der Fehlerbehandlung
- Hinweise zu Dokumentation und Struktur
- Überprüfung von Edge Cases wie unsicheren Dateinamen, falschen Logmeldungen und Bildmodus-Problemen

Beispiele für durch Review identifizierte und anschließend geprüfte Verbesserungen:

- falsche Logmeldung im `GetMedicalResult` Handler
- unsichere Dateinamen / Path-Traversal-ähnliche Eingaben
- PNG/RGBA zu RGB Konvertierung
- Gradio Timeout Handling
- Gradio Client Caching
- zusätzliche Unit Tests und Security Tests

Alle Änderungen wurden vom Projektentwickler geprüft, lokal getestet, deployed und mit einem End-to-End-Test gegen die AWS-Umgebung verifiziert.

Die Verantwortung für Architektur, Implementierung, Testing, Deployment und Dokumentation liegt beim Projektentwickler.

---

## 21. Warum diese Dienste verwendet wurden

### Warum Amazon S3?

S3 eignet sich für statisches Webhosting und Objektspeicherung.

### Warum API Gateway?

API Gateway stellt HTTP-Endpunkte für Frontend und Backend bereit.

### Warum AWS Lambda?

Lambda passt gut zum ereignisgesteuerten Serverless-Modell und vermeidet Serveradministration.

### Warum Amazon SQS?

SQS entkoppelt Upload und Verarbeitung und erhöht die Fehlertoleranz.

### Warum DynamoDB?

DynamoDB eignet sich für Metadaten und Statusinformationen anhand eines eindeutigen Object Keys.

### Warum CloudWatch?

CloudWatch bietet Logs, Metriken, Dashboards und Alarme.

### Warum AWS SAM?

SAM macht die Serverless-Architektur reproduzierbar, versionierbar und dokumentierbar.

### Warum GitHub Actions?

GitHub Actions überprüft automatisch, ob das Projekt baubar und testbar bleibt.

---

## 22. Warum bestimmte Dienste nicht verwendet wurden

### Warum nicht EC2?

EC2 würde Serveradministration, Patching und Skalierung erfordern. Für diesen Prototyp ist Lambda passender.

### Warum nicht RDS?

Das Projekt benötigt keine relationalen Joins oder komplexen Transaktionen. DynamoDB ist ausreichend und serverlos.

### Warum nicht nur direkt S3 zu Lambda?

SQS ergänzt Pufferung, Wiederholungslogik und Fehlerisolation.

### Warum keine private VPC?

Die verwendeten Serverless-Dienste benötigen für diesen Prototyp keine privaten Subnetze. Eine VPC würde die Architektur komplexer machen, ohne für diesen Use Case einen klaren Nutzen zu bringen.

---

## 23. Einschränkungen

Dieses Projekt ist ein Prototyp und hat folgende Einschränkungen:

- Es ist kein Medizinprodukt.
- Es liefert keine klinische Diagnose.
- Das KI-Modell wird extern über Hugging Face aufgerufen.
- Der S3 Website Endpoint verwendet in der aktuellen Demo HTTP.
- Es gibt noch keine Benutzeranmeldung.
- Es dürfen keine echten Patientendaten hochgeladen werden.
- GitHub Actions führt kein automatisches AWS Deployment aus.
- Die API-Endpunkte sind für den Prototyp öffentlich erreichbar.
- Für eine produktionsnahe Version wären Authentifizierung, Autorisierung und Rate Limiting notwendig.

---

## 24. Mögliche Weiterentwicklungen

- Amazon CloudFront mit HTTPS
- Amazon Cognito für Benutzeranmeldung
- Benutzerbezogene Ergebniszugriffe
- API Gateway Authorizer
- Rate Limiting / Usage Plans / AWS WAF
- Eigene Domain mit ACM-Zertifikat
- Hosting des KI-Modells innerhalb von AWS, zum Beispiel mit Amazon SageMaker
- Strukturierte JSON Logs mit Correlation IDs
- Vollautomatisierte Integration Tests
- CI/CD Deployment Pipeline mit GitHub Actions in einem normalen AWS Account
- Stärkere IAM Least-Privilege-Rollen
- Modellbewertung mit Accuracy, False Positives und False Negatives
- CloudWatch Synthetics Canary für API-Verfügbarkeit

---

## 25. Medizinischer Hinweis

Dieses Projekt dient ausschließlich Bildungs- und Demonstrationszwecken.

Das KI-Ergebnis ist nur eine technische Vorhersage und keine medizinische Diagnose.  
Alle Ergebnisse müssen von qualifiziertem medizinischem Fachpersonal überprüft werden, bevor medizinische Entscheidungen getroffen werden.

---

## 26. Projektstatus

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
SAM Deployment manuell erfolgreich
GitHub Actions CI erfolgreich
Unit Tests: 19 passed
End-to-End Test erfolgreich
Kein automatisches GitHub-to-AWS CD eingerichtet
```

---

## 27. Autor

```text
Ayman Meseleklayame
Master Wirtschaftsinformatik
Cloud Computing Portfolio Project
Technische Hochschule Deggendorf
Summer Term 2026
```