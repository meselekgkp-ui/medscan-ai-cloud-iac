\# MedScan AI – Current AWS Resources



\## Region

us-east-1



\## S3 Buckets

\- Frontend bucket: medical-xray-web-ayman

\- Medical input bucket: medical-xray-input-ayman



\## S3 Prefixes

\- medical-input/

\- medical-processed/



\## API Gateway

\- API name: Pneumo-API

\- POST /upload-url

\- GET /result



\## Lambda Functions

\- GenerateUploadUrl

\- Med-test

\- GetMedicalResult



\## SQS

\- Main queue: medical-xray-processing-queue

\- Dead-letter queue: medical-xray-processing-dlq



\## DynamoDB

\- Table: ImageProcessingMetadata

\- Partition key: id

\- TTL attribute: expiresAt



\## CloudWatch

\- Dashboard: MedScanAI-Operations-Dashboard

\- Alarms:

&#x20; - MedScanAI-SQS-Backlog

&#x20; - MedScanAI-SQS-OldestMessageTooOld

&#x20; - MedScanAI-DLQ-HasMessages

&#x20; - MedScanAI-Lambda-Errors

&#x20; - MedScanAI-Lambda-HighDuration



\## Security

\- S3 SSE-KMS enabled for medical data bucket

\- S3 lifecycle deletion after 1 day

\- DynamoDB TTL after 1 day

\- Idempotency with S3 object key as DynamoDB id

