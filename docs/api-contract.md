# API Contract – MedScan AI

Dieses Dokument beschreibt die HTTP-API, die das MedScan-AI-Frontend verwendet, um mit dem Backend zu kommunizieren.

Die API wird über Amazon API Gateway bereitgestellt und verbindet das Frontend mit den Lambda-Funktionen für die Upload-URL-Erstellung und die Ergebnisabfrage.

---

## 1. Überblick

Das Frontend verwendet zwei zentrale API-Endpunkte.

<table>
  <thead>
    <tr>
      <th>Methode</th>
      <th>Endpoint</th>
      <th>Zweck</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>POST</code></td>
      <td><code>/upload-url</code></td>
      <td>Erstellt eine Presigned URL für den direkten Upload nach Amazon S3.</td>
    </tr>
    <tr>
      <td><code>GET</code></td>
      <td><code>/result</code></td>
      <td>Liefert das Analyseergebnis aus DynamoDB zurück.</td>
    </tr>
  </tbody>
</table>

Der eigentliche Bild-Upload läuft nicht über API Gateway oder Lambda. Stattdessen erhält das Frontend eine zeitlich begrenzte Presigned URL und lädt das Bild direkt in den privaten medizinischen S3-Bucket hoch.

---

## 2. POST `/upload-url`

### Zweck

Der Endpunkt `/upload-url` erstellt eine temporäre Presigned URL für Amazon S3.

Diese URL erlaubt dem Browser, genau ein Bild direkt in den medizinischen S3-Bucket hochzuladen. Dadurch muss die Bilddatei nicht durch API Gateway oder Lambda übertragen werden.

---

### Request

```http
POST /upload-url
Content-Type: application/json
```

### Request Body

```json
{
  "filename": "xray-image.jpeg",
  "contentType": "image/jpeg"
}
```

### Request-Felder

<table>
  <thead>
    <tr>
      <th>Feld</th>
      <th>Typ</th>
      <th>Pflichtfeld</th>
      <th>Beschreibung</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>filename</code></td>
      <td><code>string</code></td>
      <td>Ja</td>
      <td>Ursprünglicher Dateiname des ausgewählten Bildes.</td>
    </tr>
    <tr>
      <td><code>contentType</code></td>
      <td><code>string</code></td>
      <td>Ja</td>
      <td>MIME-Type der hochgeladenen Datei.</td>
    </tr>
  </tbody>
</table>

### Unterstützte Content Types

<table>
  <thead>
    <tr>
      <th>Content Type</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>image/jpeg</code></td>
    </tr>
    <tr>
      <td><code>image/jpg</code></td>
    </tr>
    <tr>
      <td><code>image/png</code></td>
    </tr>
  </tbody>
</table>

---

### Erfolgreiche Response

```json
{
  "uploadUrl": "https://s3-presigned-upload-url",
  "key": "medical-input/20260429-100927-example.jpeg"
}
```

### Response-Felder

<table>
  <thead>
    <tr>
      <th>Feld</th>
      <th>Typ</th>
      <th>Beschreibung</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>uploadUrl</code></td>
      <td><code>string</code></td>
      <td>Temporäre Presigned URL für den direkten Upload nach S3.</td>
    </tr>
    <tr>
      <td><code>key</code></td>
      <td><code>string</code></td>
      <td>S3 Object Key des hochgeladenen Bildes. Dieser Key wird später für die Ergebnisabfrage verwendet.</td>
    </tr>
  </tbody>
</table>

### Beispielhafter S3 Object Key

```text
medical-input/20260429-100927-445e26a5-person1000_bacteria_2931.jpeg
```

---

### Fehlerantworten

#### Fehlender Dateiname oder Content-Type

```json
{
  "error": "filename and contentType are required"
}
```

#### Nicht unterstützter Dateityp

```json
{
  "error": "Unsupported content type"
}
```

---

## 3. Direkter Upload nach Amazon S3

Nach dem Aufruf von `/upload-url` lädt das Frontend die Bilddatei direkt mit der Presigned URL nach Amazon S3 hoch.

Der Upload erfolgt in den Prefix:

```text
medical-input/
```

### Upload-Ablauf

```text
Frontend
→ POST /upload-url
→ Presigned URL erhalten
→ Bild direkt nach S3 medical-input/ hochladen
```

Der Upload erzeugt anschließend ein S3 `ObjectCreated` Event.

Dieses Event startet die asynchrone Verarbeitung:

```text
S3 ObjectCreated Event
→ SQS Processing Queue
→ Processing Lambda
→ Hugging Face / Gradio AI Inference
→ DynamoDB Ergebnis
```

---

## 4. GET `/result`

### Zweck

Der Endpunkt `/result` liefert den aktuellen Status und das Analyseergebnis für ein hochgeladenes Bild zurück.

Das Frontend fragt diesen Endpunkt wiederholt ab, bis die Verarbeitung abgeschlossen ist.

---

### Request

```http
GET /result?id=<S3 object key>
```

Beispiel:

```http
GET /result?id=medical-input/20260429-100927-example.jpeg
```

---

### Query Parameter

<table>
  <thead>
    <tr>
      <th>Parameter</th>
      <th>Typ</th>
      <th>Pflichtfeld</th>
      <th>Beschreibung</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>id</code></td>
      <td><code>string</code></td>
      <td>Ja</td>
      <td>S3 Object Key des hochgeladenen Bildes. Der Parameter entspricht dem Partition Key in DynamoDB.</td>
    </tr>
  </tbody>
</table>

---

### Erfolgreiche Response

```json
{
  "id": "medical-input/20260429-100927-example.jpeg",
  "status": "NEEDS_URGENT_HUMAN_REVIEW",
  "medicalFinding": "PNEUMONIA_SUSPECTED",
  "riskLevel": "HIGH",
  "pneumoniaScore": 0.9996,
  "normalScore": 0.0003,
  "topLabel": "PNEUMONIA",
  "topScore": 0.9996,
  "medicalDescription": "Das Thorax-Röntgenbild wurde vom KI-Modell als auffällig eingestuft. Der Pneumonie-Score beträgt 99.96%, der Normal-Score beträgt 0.04%. Die Aufnahme sollte priorisiert durch medizinisches Fachpersonal überprüft werden. Diese Einschätzung ist keine medizinische Diagnose.",
  "disclaimer": "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."
}
```

### Response-Felder

<table>
  <thead>
    <tr>
      <th>Feld</th>
      <th>Typ</th>
      <th>Beschreibung</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>id</code></td>
      <td><code>string</code></td>
      <td>S3 Object Key und DynamoDB Partition Key.</td>
    </tr>
    <tr>
      <td><code>status</code></td>
      <td><code>string</code></td>
      <td>Technischer Verarbeitungsstatus.</td>
    </tr>
    <tr>
      <td><code>medicalFinding</code></td>
      <td><code>string</code></td>
      <td>Interpretierte KI-Klassifikation.</td>
    </tr>
    <tr>
      <td><code>riskLevel</code></td>
      <td><code>string</code></td>
      <td>Risikostufe: <code>LOW</code>, <code>MEDIUM</code> oder <code>HIGH</code>.</td>
    </tr>
    <tr>
      <td><code>pneumoniaScore</code></td>
      <td><code>number</code></td>
      <td>Wahrscheinlichkeit für Pneumonie.</td>
    </tr>
    <tr>
      <td><code>normalScore</code></td>
      <td><code>number</code></td>
      <td>Wahrscheinlichkeit für Normalbefund.</td>
    </tr>
    <tr>
      <td><code>topLabel</code></td>
      <td><code>string</code></td>
      <td>Höchste Modellklasse.</td>
    </tr>
    <tr>
      <td><code>topScore</code></td>
      <td><code>number</code></td>
      <td>Höchster Modellscore.</td>
    </tr>
    <tr>
      <td><code>medicalDescription</code></td>
      <td><code>string</code></td>
      <td>Beschreibung des Ergebnisses.</td>
    </tr>
    <tr>
      <td><code>disclaimer</code></td>
      <td><code>string</code></td>
      <td>Hinweis, dass es keine medizinische Diagnose ist.</td>
    </tr>
  </tbody>
</table>

---

## 5. Statuswerte

<table>
  <thead>
    <tr>
      <th>Status</th>
      <th>Bedeutung</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>PROCESSING</code></td>
      <td>Das Bild wird aktuell verarbeitet.</td>
    </tr>
    <tr>
      <td><code>COMPLETED</code></td>
      <td>Die Verarbeitung wurde abgeschlossen.</td>
    </tr>
    <tr>
      <td><code>NEEDS_HUMAN_REVIEW</code></td>
      <td>Das Ergebnis ist unklar und sollte medizinisch überprüft werden.</td>
    </tr>
    <tr>
      <td><code>NEEDS_URGENT_HUMAN_REVIEW</code></td>
      <td>Hoher Pneumonie-Score; dringende menschliche Überprüfung empfohlen.</td>
    </tr>
    <tr>
      <td><code>MODEL_ERROR</code></td>
      <td>Das externe KI-Modell konnte nicht erfolgreich aufgerufen werden.</td>
    </tr>
    <tr>
      <td><code>INVALID_FILE</code></td>
      <td>Die hochgeladene Datei ist ungültig oder nicht unterstützt.</td>
    </tr>
    <tr>
      <td><code>PROCESSING_FAILED</code></td>
      <td>Ein technischer Fehler ist während der Verarbeitung aufgetreten.</td>
    </tr>
    <tr>
      <td><code>NOT_FOUND</code></td>
      <td>Es wurde noch kein Ergebnis für diese ID gefunden.</td>
    </tr>
  </tbody>
</table>

---

## 6. Risikoklassifikation

Die Processing Lambda wandelt die Modellwerte in eine einfache Risikoklassifikation um.

<table>
  <thead>
    <tr>
      <th>Pneumonie-Score</th>
      <th>Risk Level</th>
      <th>Medical Finding</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>&gt;= 0.70</code></td>
      <td><code>HIGH</code></td>
      <td><code>PNEUMONIA_SUSPECTED</code></td>
    </tr>
    <tr>
      <td><code>&gt;= 0.40 und &lt; 0.70</code></td>
      <td><code>MEDIUM</code></td>
      <td><code>PNEUMONIA_UNCLEAR</code></td>
    </tr>
    <tr>
      <td><code>&lt; 0.40</code></td>
      <td><code>LOW</code></td>
      <td><code>NO_PNEUMONIA_SUSPECTED</code></td>
    </tr>
  </tbody>
</table>

---

## 7. Beispiel: LOW Risk Response

```json
{
  "id": "medical-input/20260429-074147-9c077609-00018388_000.png",
  "status": "COMPLETED",
  "medicalFinding": "NO_PNEUMONIA_SUSPECTED",
  "riskLevel": "LOW",
  "pneumoniaScore": 0.0868,
  "normalScore": 0.9132,
  "topLabel": "NORMAL",
  "topScore": 0.9132,
  "medicalDescription": "Das KI-Modell stuft das Thorax-Röntgenbild eher als unauffällig ein. Der Pneumonie-Score beträgt 8.68%, der Normal-Score beträgt 91.32%. Auch dieses Ergebnis ersetzt keine ärztliche Diagnose.",
  "disclaimer": "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."
}
```

---

## 8. Beispiel: HIGH Risk Response

```json
{
  "id": "medical-input/20260429-100927-445e26a5-person1000_bacteria_2931.jpeg",
  "status": "NEEDS_URGENT_HUMAN_REVIEW",
  "medicalFinding": "PNEUMONIA_SUSPECTED",
  "riskLevel": "HIGH",
  "pneumoniaScore": 0.9996,
  "normalScore": 0.0003,
  "topLabel": "PNEUMONIA",
  "topScore": 0.9996,
  "medicalDescription": "Das Thorax-Röntgenbild wurde vom KI-Modell als auffällig eingestuft. Der Pneumonie-Score beträgt 99.96%, der Normal-Score beträgt 0.04%. Die Aufnahme sollte priorisiert durch medizinisches Fachpersonal überprüft werden. Diese Einschätzung ist keine medizinische Diagnose.",
  "disclaimer": "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."
}
```

---

## 9. Fehlerfälle

### Fehlender Query Parameter

```json
{
  "error": "Missing id parameter"
}
```

### Ergebnis noch nicht vorhanden

```json
{
  "status": "NOT_FOUND",
  "message": "No result found for the provided id"
}
```

### Interner Fehler

```json
{
  "error": "Internal server error"
}
```

---

## 10. Designentscheidungen

### Warum Presigned URLs?

Presigned URLs ermöglichen einen sicheren, zeitlich begrenzten Direkt-Upload nach S3.

Vorteile:

- Kein permanenter AWS-Schlüssel im Frontend
- Bilddaten laufen nicht durch Lambda
- API Gateway wird nicht mit großen Dateien belastet
- Upload und Verarbeitung sind sauber getrennt

---

### Warum asynchrone Verarbeitung?

Die KI-Verarbeitung kann länger dauern als ein normaler HTTP-Request.

Deshalb wird der Upload vom Verarbeitungsprozess getrennt:

```text
Upload
→ S3 Event
→ SQS
→ Lambda Processing
→ DynamoDB
```

Das Frontend fragt danach das Ergebnis über `/result` ab.

---

### Warum SQS?

Amazon SQS entkoppelt S3 Upload und Lambda Processing.

Vorteile:

- Nachrichten bleiben erhalten, wenn Lambda kurzzeitig nicht verarbeitet
- Wiederholungen sind kontrollierbar
- Fehlerhafte Nachrichten können in eine Dead-Letter Queue verschoben werden
- Queue-Metriken können mit CloudWatch überwacht werden

---

### Warum DynamoDB?

DynamoDB speichert die Analyseergebnisse anhand eines eindeutigen Schlüssels.

Der S3 Object Key wird als `id` verwendet.

Dadurch kann das Frontend das Ergebnis direkt über denselben Key abfragen.

---

### Warum Idempotency?

S3 Events können mehrfach zugestellt werden.

Damit ein Bild nicht mehrfach verarbeitet wird, verwendet die Anwendung den S3 Object Key als eindeutige ID in DynamoDB.

Vor der Verarbeitung kann geprüft werden, ob für diese ID bereits ein Eintrag existiert.

---

## 11. End-to-End Ablauf

```text
1. Frontend ruft POST /upload-url auf
2. Backend erstellt Presigned URL und S3 Object Key
3. Frontend lädt Bild direkt nach S3 medical-input/ hoch
4. S3 sendet ObjectCreated Event an SQS
5. Processing Lambda verarbeitet das Bild
6. Processing Lambda ruft Hugging Face / Gradio KI-Modell auf
7. Processing Lambda speichert Ergebnis in DynamoDB
8. Frontend ruft GET /result?id=<object-key> auf
9. Backend liest DynamoDB
10. Frontend zeigt Ergebnis und Risikostufe an
```

---

## 12. Medizinischer Hinweis

Die API liefert ausschließlich eine technische KI-Vorhersage.

Das Ergebnis ist keine medizinische Diagnose und darf nicht als Grundlage für medizinische Entscheidungen ohne fachliche Überprüfung verwendet werden.

Alle Ergebnisse müssen durch qualifiziertes medizinisches Fachpersonal überprüft werden.