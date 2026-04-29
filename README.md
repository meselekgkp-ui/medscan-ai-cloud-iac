# MedScan AI – Serverless Thorax-Röntgenanalyse auf AWS

MedScan AI ist ein cloud-nativer, serverloser Prototyp zur Analyse von Thorax-Röntgenbildern.  
Das System ermöglicht den Upload eines Röntgenbildes über eine Weboberfläche, verarbeitet das Bild asynchron, ruft ein externes KI-Modell über Hugging Face Gradio auf, speichert das Ergebnis in DynamoDB und zeigt die Auswertung anschließend im Frontend an.

> Dieses Projekt ist ein technischer Cloud-Computing-Prototyp. Es ist kein medizinisches Diagnosesystem und ersetzt keine ärztliche oder fachmedizinische Beurteilung.

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
- Monitoring mit Amazon CloudWatch
- Infrastructure as Code mit AWS SAM

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
S3 Medical Input Bucket: medical-input/
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
Frontend zeigt das Ergebnis an
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
| S3 Server-Side Encryption | Schutz gespeicherter Bilddaten |
| Amazon CloudWatch | Logs, Metriken, Dashboard und Alarme |
| AWS SAM | Beschreibung der Infrastruktur als Code |

---

## 4. Aktuelle Demo-Ressourcen

Die aktuelle Demo-Umgebung verwendet folgende Ressourcen.

### Region

```text
us-east-1
US East (N. Virginia)
```

### S3 Buckets

```text
Frontend Bucket:
medical-xray-web-ayman

Medical Image Bucket:
medical-xray-input-ayman
```

### S3 Prefixes

```text
medical-input/
medical-processed/
```

### API Gateway

```text
API Name:
Pneumo-API

Routen:
POST /upload-url
GET /result
```

### Lambda Functions

```text
GenerateUploadUrl
Med-test
GetMedicalResult
```

### DynamoDB

```text
Tabelle:
ImageProcessingMetadata

Partition Key:
id

TTL-Attribut:
expiresAt
```

### SQS

```text
Processing Queue:
medical-xray-processing-queue

Dead-Letter Queue:
medical-xray-processing-dlq
```

### CloudWatch Alarms

```text
MedScanAI-SQS-Backlog
MedScanAI-SQS-OldestMessageTooOld
MedScanAI-DLQ-HasMessages
MedScanAI-Lambda-Errors
MedScanAI-Lambda-HighDuration
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

### Schritt 4: Upload des Bildes nach S3

Das Bild wird in den Prefix `medical-input/` hochgeladen.

Beispiel:

```text
medical-input/20260429-100927-445e26a5-person1000_bacteria_2931.jpeg
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
- Aufruf des Hugging Face Gradio KI-Modells
- Speicherung des verarbeiteten Bildes in S3
- Speicherung der Metadaten und KI-Ergebnisse in DynamoDB

### Schritt 7: Ergebnisabfrage durch das Frontend

Das Frontend ruft folgenden Endpunkt auf:

```http
GET /result?id=<S3 object key>
```

Die Lambda-Funktion `GetMedicalResult` liest das Ergebnis aus DynamoDB und gibt es an das Frontend zurück.

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

Beispiel eines gespeicherten Ergebnisses:

```json
{
  "medicalFinding": "PNEUMONIA_SUSPECTED",
  "riskLevel": "HIGH",
  "pneumoniaScore": 0.9996,
  "normalScore": 0.0003,
  "status": "NEEDS_URGENT_HUMAN_REVIEW"
}
```

---

## 7. Sicherheitskonzept

### 7.1 Trennung der Buckets

Das Projekt trennt den Frontend Bucket vom medizinischen Bilddaten-Bucket.

```text
medical-xray-web-ayman
medical-xray-input-ayman
```

Der Frontend Bucket enthält nur statische Webdateien.  
Der medizinische Bucket enthält hochgeladene und verarbeitete Röntgenbilder.

### 7.2 Presigned URLs

Der Browser erhält keine dauerhaften AWS-Zugangsdaten.  
Stattdessen erhält er eine zeitlich begrenzte Presigned URL für den Upload eines bestimmten Objekts nach S3.

### 7.3 Privater medizinischer Bilddaten-Bucket

Der medizinische Bilddaten-Bucket wird nicht als öffentliche Website verwendet.  
Der Zugriff erfolgt über Presigned URLs und über Lambda-Funktionen.

### 7.4 Verschlüsselung ruhender Daten

Der medizinische S3 Bucket verwendet serverseitige Verschlüsselung.  
Dadurch werden gespeicherte Bilddaten geschützt.

### 7.5 DynamoDB TTL

DynamoDB-Einträge enthalten ein `expiresAt`-Attribut.  
Dadurch können alte Metadaten automatisch nach Ablauf der Aufbewahrungsfrist gelöscht werden.

### 7.6 S3 Lifecycle Rule

Für den medizinischen S3 Bucket ist eine Lifecycle Rule konfiguriert.  
Diese löscht alte Bildobjekte automatisch.

### 7.7 Keine echten Patientendaten

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

### 9.3 Idempotency

S3 Events können mehrfach zugestellt werden.  
Deshalb verwendet die Processing Lambda den S3 Object Key als DynamoDB `id`.

Vor der Verarbeitung erstellt die Lambda-Funktion einen DynamoDB-Eintrag mit:

```text
status = PROCESSING
```

Wenn dasselbe Event erneut eintrifft, erkennt die Funktion, dass das Bild bereits verarbeitet wurde oder gerade verarbeitet wird.

Dadurch werden doppelte Verarbeitung und doppelte Ergebnisdatensätze vermieden.

### 9.4 Fehlerstatus

Wenn die Verarbeitung fehlschlägt, aktualisiert die Lambda-Funktion DynamoDB mit:

```text
status = PROCESSING_FAILED
```

Danach wird der Fehler erneut ausgelöst, damit SQS die Nachricht wiederholen oder später in die DLQ verschieben kann.

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
| MedScanAI-SQS-Backlog | Es befinden sich sichtbare Nachrichten in der Processing Queue |
| MedScanAI-SQS-OldestMessageTooOld | Eine Nachricht wartet zu lange in der Queue |
| MedScanAI-DLQ-HasMessages | Es befinden sich fehlgeschlagene Nachrichten in der Dead-Letter Queue |
| MedScanAI-Lambda-Errors | Die Processing Lambda erzeugt Fehler |
| MedScanAI-Lambda-HighDuration | Die Processing Lambda benötigt ungewöhnlich lange |

---

## 12. Operational Failure Test

Zur Überprüfung des Monitorings wurde der SQS Trigger der Processing Lambda temporär deaktiviert.

### Testszenario

```text
SQS Trigger deaktiviert
Bild über Frontend hochgeladen
S3 sendet Event an SQS
Lambda verarbeitet die Nachricht nicht
Nachricht bleibt sichtbar in SQS
CloudWatch Alarm wechselt in den ALARM-Zustand
```

### Erwartetes Ergebnis

```text
MedScanAI-SQS-Backlog = ALARM
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

Die Infrastruktur ist zusätzlich als AWS SAM Template beschrieben.

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

Die IaC-Version verwendet Ressourcennamen mit `-iac`, damit die bestehende funktionierende Demo-Umgebung nicht ersetzt wird.

---

## 14. Projektstruktur

```text
medscan-ai-iac/
│   .gitignore
│   README.md
│   template.yaml
│
├── docs/
│   ├── current-resources.md
│   └── iac-validation.md
│
├── diagrams/
│
├── screenshots/
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

## 15. Lokale Voraussetzungen

Die lokale Entwicklungsumgebung verwendet:

```text
Windows
PowerShell
Python 3.11
AWS SAM CLI
```

SAM CLI prüfen:

```powershell
sam --version
```

Region setzen:

```powershell
$env:AWS_DEFAULT_REGION="us-east-1"
$env:AWS_REGION="us-east-1"
```

Optional: SAM Telemetry deaktivieren:

```powershell
$env:SAM_CLI_TELEMETRY="0"
```

---

## 16. SAM Template validieren

Befehl:

```powershell
sam validate --template-file template.yaml --region us-east-1
```

Erwartetes Ergebnis:

```text
template.yaml is a valid SAM Template
```

---

## 17. SAM Projekt bauen

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

## 18. Deployment-Hinweis

Das SAM Template wurde erfolgreich validiert und lokal gebaut.

Ein automatisches Deployment wurde nicht ausgeführt, da das AWS Academy Learner Lab bestimmte IAM- und CloudFormation-Berechtigungen einschränken kann.  
Die bestehende funktionierende Demo-Umgebung wurde deshalb nicht ersetzt.

In einem vollständigen AWS Account könnte das Projekt mit folgendem Befehl deployed werden:

```powershell
sam deploy --guided --region us-east-1
```

---

## 19. Warum diese Dienste verwendet wurden

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

---

## 20. Warum bestimmte Dienste nicht verwendet wurden

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
Im AWS Academy Learner Lab war die Erstellung von CloudFront durch IAM-Berechtigungen eingeschränkt.  
Deshalb verwendet die aktuelle Demo den S3 Static Website Endpoint.

Mögliche Production-Verbesserung:

```text
CloudFront + HTTPS + Origin Access Control
```

### Warum keine private VPC?

Die verwendeten Serverless-Dienste benötigen für diesen Prototyp keine privaten Subnetze.  
Eine VPC würde die Architektur komplexer machen, ohne für diesen Use Case einen klaren Nutzen zu bringen.

---

## 21. Einschränkungen

Dieses Projekt ist ein Prototyp und hat folgende Einschränkungen:

- Es ist kein Medizinprodukt.
- Es liefert keine klinische Diagnose.
- Das KI-Modell wird extern über Hugging Face aufgerufen.
- Der S3 Website Endpoint verwendet in der aktuellen Demo HTTP.
- Es gibt noch keine Benutzeranmeldung.
- Es dürfen keine echten Patientendaten hochgeladen werden.
- Das Deployment wurde wegen möglicher AWS-Academy-Berechtigungsgrenzen nicht über SAM ausgeführt.

---

## 22. Mögliche Weiterentwicklungen

Mögliche Verbesserungen für eine produktionsnähere Version:

- Amazon CloudFront mit HTTPS
- Amazon Cognito für Benutzeranmeldung
- Benutzerbezogene Ergebniszugriffe
- Eigene Domain mit ACM-Zertifikat
- Hosting des KI-Modells innerhalb von AWS, zum Beispiel mit Amazon SageMaker
- Strukturierte Logs mit Correlation IDs
- Automatisierte Tests
- CI/CD Pipeline mit GitHub Actions
- Stärkere IAM Least-Privilege-Rollen
- Modellbewertung mit Accuracy, False Positives und False Negatives

---

## 23. Medizinischer Hinweis

Dieses Projekt dient ausschließlich Bildungs- und Demonstrationszwecken.

Das KI-Ergebnis ist nur eine technische Vorhersage und keine medizinische Diagnose.  
Alle Ergebnisse müssen von qualifiziertem medizinischem Fachpersonal überprüft werden, bevor medizinische Entscheidungen getroffen werden.

---

## 24. Projektstatus

Aktueller Stand:

```text
Funktionierende Demo implementiert
S3 Frontend funktioniert
API Gateway Routen funktionieren
Lambda Processing funktioniert
SQS Processing Queue funktioniert
DynamoDB Ergebnispeicherung funktioniert
DynamoDB TTL implementiert
S3 Lifecycle Rule implementiert
CloudWatch Dashboard implementiert
CloudWatch Alarms implementiert
Idempotency implementiert
Infrastructure as Code vorbereitet
SAM Validation erfolgreich
SAM Build erfolgreich
```

---

## 25. Autor

```text
Ayman Meseleklayame
Master Wirtschaftsinformatik
Cloud Computing Portfolio Project
Technische Hochschule Deggendorf
Summer Term 2026
```