# Threat Model

## 1. Ziel und Umfang

Dieses Dokument beschreibt die wichtigsten Bedrohungen für das MedScan AI Projekt und die Gegenmaßnahmen, die im Rahmen der aktuellen Architektur umgesetzt wurden.
Der Fokus liegt auf dem serverlosen AWS-System, das hochgeladene Thorax-Röntgenbilder verarbeitet und Analyseergebnisse zurückliefert.

## 2. Wichtige Assets

- Hochgeladene Bilddaten in Amazon S3
- Analyse-Ergebnisse und Metadaten in Amazon DynamoDB
- Presigned URLs für S3-Uploads
- API-Endpunkte für Upload und Ergebnisabfrage
- AWS-Lambda-Funktionen zur Verarbeitung und Ergebnisbereitstellung
- CloudWatch Logs und Alarme
- IAM-Rollen und Berechtigungen

## 3. Annahmen

- Die AWS-Anmeldedaten für den Dienstbetrieb sind sicher gespeichert.
- Der Besucherzugriff auf das Frontend ist über einen öffentlichen S3-Website-Endpunkt möglich, aber der medizinische Datenbucket ist nicht öffentlich.
- Das Projekt dient als Technikprototyp; keine echten Patientendaten sollten verwendet werden.

## 4. Hauptbedrohungen

### 4.1 Unbefugter Zugriff auf hochgeladene Bilder

- Beschreibung: Ein Angreifer kann versuchen, direkt auf Objekte im S3 Bucket zuzugreifen.
- Gegenmaßnahme: Der medizinische Bucket ist privat und der Upload erfolgt über zeitlich begrenzte Presigned URLs.

### 4.2 Missbrauch der Presigned URL

- Beschreibung: Ein Presigned URL kann abgefangen oder weiterverbreitet werden.
- Gegenmaßnahme: Presigned URLs haben eine kurze Ablaufzeit und gelten nur für genau ein Objekt.

### 4.3 Unautorisierte API-Anfragen

- Beschreibung: Ein Angreifer versucht, die API-Endpunkte `/upload-url` oder `/result` zu missbrauchen.
- Gegenmaßnahme: API Gateway sollte idealerweise mit IAM oder anderen Zugriffskontrollen abgesichert sein; in der aktuellen Demo sollten sensible Endpunkte weiterhin stark limitierte Eingaben akzeptieren.

### 4.4 Unsichere Verarbeitung der Bilddaten

- Beschreibung: Ein manipuliertes Bild könnte die Verarbeitung stören oder ungewünschte Ergebnisse erzeugen.
- Gegenmaßnahme: Die Processing Lambda validiert Dateityp und -größe und führt Idempotency-Prüfungen durch.

### 4.5 Fehlende Protokollierung und Alarmierung

- Beschreibung: Ein Vorfall wird nicht erkannt, weil Log- und Alarmmechanismen nicht vorhanden sind.
- Gegenmaßnahme: CloudWatch Logs, Dashboard und Alarme wurden konfiguriert, um Fehler, SQS-Backlog und hohe Latenzen zu melden.

### 4.6 Übermäßige Berechtigungen (Privilege Escalation)

- Beschreibung: Eine Lambda-Funktion besitzt weitergehende IAM-Berechtigungen als notwendig.
- Gegenmaßnahme: IAM-Rollen sollten dem Prinzip "Least Privilege" folgen, um nur den notwendigen Zugriff auf S3, SQS, DynamoDB und andere Dienste zu gewähren.

## 5. Zusätzliche Sicherheitsmaßnahmen

- **Datenverschlüsselung**: Ruhende Daten in S3 werden serverseitig verschlüsselt.
- **Datenisolation**: Frontend-Bucket und medizinischer Bucket sind getrennt.
- **Zuverlässigkeit**: Dead-Letter Queue verhindert endlose Wiederholungen bei Verarbeitungsfehlern.
- **TTL & Lifecycle**: Automatische Löschung älterer Einträge in DynamoDB und S3 reduziert die Angriffsfläche.

## 6. Empfehlungen für zukünftige Verbesserungen

- Stärkere Authentifizierung für API-Endpunkte (z. B. Cognito, API Keys, JWT).
- Einsatz von CloudFront mit Origin Access Control für das Frontend.
- Input-Sanitization und Deep-Packet-Inspection für eingehende Anfragen.
- Regelmäßige Überprüfung der IAM-Rollen und Berechtigungen.
- Verwendung eines Secrets Managers für alle sensiblen Zugangsdaten.
- Aktivierung von AWS Config und GuardDuty für zusätzliches Monitoring.
