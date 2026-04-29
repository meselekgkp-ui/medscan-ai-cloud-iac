\# API Contract – MedScan AI



Dieses Dokument beschreibt die HTTP-API, die das MedScan-AI-Frontend verwendet, um mit dem Backend zu kommunizieren.



Die API wird über Amazon API Gateway bereitgestellt und verbindet das Frontend mit den Lambda-Funktionen für Upload-URL-Erstellung und Ergebnisabfrage.



\---



\## 1. Überblick



Das Frontend verwendet zwei zentrale API-Endpunkte:



| Methode | Endpoint | Zweck |

|---|---|---|

| POST | `/upload-url` | Erstellt eine Presigned URL für den direkten Upload nach Amazon S3 |

| GET | `/result` | Liefert das Analyseergebnis aus DynamoDB zurück |



Der eigentliche Bild-Upload läuft nicht über API Gateway oder Lambda. Stattdessen erhält das Frontend eine zeitlich begrenzte Presigned URL und lädt das Bild direkt in den privaten medizinischen S3-Bucket hoch.



\---



\## 2. POST /upload-url



\### Zweck



Der Endpunkt `/upload-url` erstellt eine temporäre Presigned URL für Amazon S3.



Diese URL erlaubt dem Browser, genau ein Bild direkt in den medizinischen S3-Bucket hochzuladen. Dadurch muss die Bilddatei nicht durch API Gateway oder Lambda übertragen werden.



\---



\### Request



```http

POST /upload-url

Content-Type: application/json

```



\### Request Body



```json

{

&#x20; "filename": "xray-image.jpeg",

&#x20; "contentType": "image/jpeg"

}

```



\### Request-Felder



| Feld | Typ | Pflichtfeld | Beschreibung |

|---|---|---|---|

| `filename` | string | ja | Ursprünglicher Dateiname des ausgewählten Bildes |

| `contentType` | string | ja | MIME-Type der Datei |



Unterstützte Content Types:



```text

image/jpeg

image/jpg

image/png

```



\---



\### Erfolgreiche Response



```json

{

&#x20; "uploadUrl": "https://s3-presigned-upload-url",

&#x20; "key": "medical-input/20260429-100927-example.jpeg"

}

```



\### Response-Felder



| Feld | Typ | Beschreibung |

|---|---|---|

| `uploadUrl` | string | Temporäre Presigned URL für den direkten Upload nach S3 |

| `key` | string | S3 Object Key des hochgeladenen Bildes |



Der Wert `key` ist wichtig, weil das Frontend ihn später verwendet, um das Analyseergebnis über `/result` abzufragen.



\---



\### Beispielhafter S3 Object Key



```text

medical-input/20260429-100927-445e26a5-person1000\_bacteria\_2931.jpeg

```



\---



\### Mögliche Fehlerantworten



\#### Fehlender Dateiname oder Content-Type



```json

{

&#x20; "error": "filename and contentType are required"

}

```



\#### Nicht unterstützter Dateityp



```json

{

&#x20; "error": "Unsupported content type"

}

```



\---



\## 3. Direkter Upload nach Amazon S3



Nach dem Aufruf von `/upload-url` lädt das Frontend die Bilddatei direkt mit der Presigned URL nach Amazon S3 hoch.



Der Upload erfolgt in den Prefix:



```text

medical-input/

```



Ablauf:



```text

Frontend

→ POST /upload-url

→ Presigned URL erhalten

→ Bild direkt nach S3 medical-input/ hochladen

```



Der Upload erzeugt anschließend ein S3 ObjectCreated Event.



Dieses Event startet die asynchrone Verarbeitung:



```text

S3 ObjectCreated Event

→ SQS Processing Queue

→ Processing Lambda

→ Hugging Face / Gradio AI Inference

→ DynamoDB Ergebnis

```



\---



\## 4. GET /result



\### Zweck



Der Endpunkt `/result` liefert den aktuellen Status und das Analyseergebnis für ein hochgeladenes Bild zurück.



Das Frontend fragt diesen Endpunkt wiederholt ab, bis die Verarbeitung abgeschlossen ist.



\---



\### Request



```http

GET /result?id=<S3 object key>

```



Beispiel:



```http

GET /result?id=medical-input/20260429-100927-example.jpeg

```



\---



\### Query Parameter



| Parameter | Typ | Pflichtfeld | Beschreibung |

|---|---|---|---|

| `id` | string | ja | S3 Object Key des hochgeladenen Bildes |



Der Parameter `id` entspricht dem Partition Key in DynamoDB.



\---



\### Erfolgreiche Response



```json

{

&#x20; "id": "medical-input/20260429-100927-example.jpeg",

&#x20; "status": "NEEDS\_URGENT\_HUMAN\_REVIEW",

&#x20; "medicalFinding": "PNEUMONIA\_SUSPECTED",

&#x20; "riskLevel": "HIGH",

&#x20; "pneumoniaScore": 0.9996,

&#x20; "normalScore": 0.0003,

&#x20; "topLabel": "PNEUMONIA",

&#x20; "topScore": 0.9996,

&#x20; "medicalDescription": "Das Thorax-Röntgenbild wurde vom KI-Modell als auffällig eingestuft. Der Pneumonie-Score beträgt 99.96%, der Normal-Score beträgt 0.04%. Die Aufnahme sollte priorisiert durch medizinisches Fachpersonal überprüft werden. Diese Einschätzung ist keine medizinische Diagnose.",

&#x20; "disclaimer": "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."

}

```



\---



\### Response-Felder



| Feld | Typ | Beschreibung |

|---|---|---|

| `id` | string | S3 Object Key und DynamoDB Partition Key |

| `status` | string | Technischer Verarbeitungsstatus |

| `medicalFinding` | string | Medizinisch interpretierte KI-Klassifikation |

| `riskLevel` | string | Risikostufe: LOW, MEDIUM oder HIGH |

| `pneumoniaScore` | number | Wahrscheinlichkeit für Pneumonie |

| `normalScore` | number | Wahrscheinlichkeit für Normalbefund |

| `topLabel` | string | Höchste Modellklasse |

| `topScore` | number | Höchster Modellscore |

| `medicalDescription` | string | Beschreibung des Ergebnisses |

| `disclaimer` | string | Hinweis, dass es keine medizinische Diagnose ist |



\---



\## 5. Statuswerte



| Status | Bedeutung |

|---|---|

| `PROCESSING` | Das Bild wird aktuell verarbeitet |

| `COMPLETED` | Die Verarbeitung wurde abgeschlossen |

| `NEEDS\_HUMAN\_REVIEW` | Das Ergebnis ist unklar und sollte medizinisch überprüft werden |

| `NEEDS\_URGENT\_HUMAN\_REVIEW` | Hoher Pneumonie-Score; dringende menschliche Überprüfung empfohlen |

| `MODEL\_ERROR` | Das externe KI-Modell konnte nicht erfolgreich aufgerufen werden |

| `INVALID\_FILE` | Die hochgeladene Datei ist ungültig oder nicht unterstützt |

| `PROCESSING\_FAILED` | Ein technischer Fehler ist während der Verarbeitung aufgetreten |

| `NOT\_FOUND` | Es wurde noch kein Ergebnis für diese ID gefunden |



\---



\## 6. Risikoklassifikation



Die Processing Lambda wandelt die Modellwerte in eine einfache Risikoklassifikation um.



| Pneumonie-Score | Risk Level | Medical Finding |

|---|---|---|

| `>= 0.70` | `HIGH` | `PNEUMONIA\_SUSPECTED` |

| `>= 0.40` und `< 0.70` | `MEDIUM` | `PNEUMONIA\_UNCLEAR` |

| `< 0.40` | `LOW` | `NO\_PNEUMONIA\_SUSPECTED` |



\---



\## 7. Beispiel: LOW Risk Response



```json

{

&#x20; "id": "medical-input/20260429-074147-9c077609-00018388\_000.png",

&#x20; "status": "COMPLETED",

&#x20; "medicalFinding": "NO\_PNEUMONIA\_SUSPECTED",

&#x20; "riskLevel": "LOW",

&#x20; "pneumoniaScore": 0.0868,

&#x20; "normalScore": 0.9132,

&#x20; "topLabel": "NORMAL",

&#x20; "topScore": 0.9132,

&#x20; "medicalDescription": "Das KI-Modell stuft das Thorax-Röntgenbild eher als unauffällig ein. Der Pneumonie-Score beträgt 8.68%, der Normal-Score beträgt 91.32%. Auch dieses Ergebnis ersetzt keine ärztliche Diagnose.",

&#x20; "disclaimer": "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."

}

```



\---



\## 8. Beispiel: HIGH Risk Response



```json

{

&#x20; "id": "medical-input/20260429-100927-445e26a5-person1000\_bacteria\_2931.jpeg",

&#x20; "status": "NEEDS\_URGENT\_HUMAN\_REVIEW",

&#x20; "medicalFinding": "PNEUMONIA\_SUSPECTED",

&#x20; "riskLevel": "HIGH",

&#x20; "pneumoniaScore": 0.9996,

&#x20; "normalScore": 0.0003,

&#x20; "topLabel": "PNEUMONIA",

&#x20; "topScore": 0.9996,

&#x20; "medicalDescription": "Das Thorax-Röntgenbild wurde vom KI-Modell als auffällig eingestuft. Der Pneumonie-Score beträgt 99.96%, der Normal-Score beträgt 0.04%. Die Aufnahme sollte priorisiert durch medizinisches Fachpersonal überprüft werden. Diese Einschätzung ist keine medizinische Diagnose.",

&#x20; "disclaimer": "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."

}

```



\---



\## 9. Fehlerfälle



\### Fehlender Query Parameter



Wenn `id` fehlt:



```json

{

&#x20; "error": "Missing id parameter"

}

```



\### Ergebnis noch nicht vorhanden



Wenn noch kein DynamoDB-Eintrag existiert:



```json

{

&#x20; "status": "NOT\_FOUND",

&#x20; "message": "No result found for the provided id"

}

```



\### Interner Fehler



```json

{

&#x20; "error": "Internal server error"

}

```



\---



\## 10. Designentscheidungen



\### Warum Presigned URLs?



Presigned URLs ermöglichen einen sicheren, zeitlich begrenzten Direkt-Upload nach S3.



Vorteile:



\- Kein permanenter AWS-Schlüssel im Frontend

\- Bilddaten laufen nicht durch Lambda

\- API Gateway wird nicht mit großen Dateien belastet

\- Upload und Verarbeitung sind sauber getrennt



\---



\### Warum asynchrone Verarbeitung?



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



\---



\### Warum SQS?



Amazon SQS entkoppelt S3 Upload und Lambda Processing.



Vorteile:



\- Nachrichten bleiben erhalten, wenn Lambda kurzzeitig nicht verarbeitet

\- Wiederholungen sind kontrollierbar

\- Fehlerhafte Nachrichten können in eine Dead-Letter Queue verschoben werden

\- Queue-Metriken können mit CloudWatch überwacht werden



\---



\### Warum DynamoDB?



DynamoDB speichert die Analyseergebnisse anhand eines eindeutigen Schlüssels.



Der S3 Object Key wird als `id` verwendet.



Dadurch kann das Frontend das Ergebnis direkt über denselben Key abfragen.



\---



\### Warum Idempotency?



S3 Events können mehrfach zugestellt werden.



Damit ein Bild nicht mehrfach verarbeitet wird, verwendet die Anwendung den S3 Object Key als eindeutige ID in DynamoDB.



Vor der Verarbeitung kann geprüft werden, ob für diese ID bereits ein Eintrag existiert.



\---



\## 11. End-to-End Ablauf



```text

1\. Frontend ruft POST /upload-url auf

2\. Backend erstellt Presigned URL und S3 Object Key

3\. Frontend lädt Bild direkt nach S3 medical-input/ hoch

4\. S3 sendet ObjectCreated Event an SQS

5\. Processing Lambda verarbeitet das Bild

6\. Processing Lambda ruft Hugging Face / Gradio KI-Modell auf

7\. Processing Lambda speichert Ergebnis in DynamoDB

8\. Frontend ruft GET /result?id=<object-key> auf

9\. Backend liest DynamoDB

10\. Frontend zeigt Ergebnis und Risikostufe an

```



\---



\## 12. Medizinischer Hinweis



Die API liefert ausschließlich eine technische KI-Vorhersage.



Das Ergebnis ist keine medizinische Diagnose und darf nicht als Grundlage für medizinische Entscheidungen ohne fachliche Überprüfung verwendet werden.



Alle Ergebnisse müssen durch qualifiziertes medizinisches Fachpersonal überprüft werden.

