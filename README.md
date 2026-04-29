# MedScan AI – Serverless Chest X-ray Analysis on AWS

MedScan AI is a cloud-native serverless prototype for analyzing chest X-ray images with an external AI model.  
The system allows a user to upload an X-ray image through a web frontend, processes the image asynchronously, calls a Hugging Face Gradio model, stores the analysis result in DynamoDB, and exposes the result back to the frontend.

> This project is a technical cloud computing prototype. It is not a medical diagnostic system and does not replace medical assessment by qualified healthcare professionals.

---

## 1. Project Goal

The goal of this project is to demonstrate a secure, scalable and observable serverless architecture on AWS for an AI-assisted medical image processing use case.

The project focuses on:

- Serverless computing with AWS Lambda
- Static frontend hosting with Amazon S3
- Direct browser-to-S3 upload using presigned URLs
- Asynchronous processing with Amazon SQS
- Failure isolation using a dead-letter queue
- Metadata and prediction storage in Amazon DynamoDB
- Data retention using DynamoDB TTL and S3 lifecycle rules
- Operational monitoring with Amazon CloudWatch
- Infrastructure as Code using AWS SAM

---

## 2. High-Level Architecture

The system follows an event-driven serverless architecture.

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
Lambda: Med-test / Processing Lambda
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
Frontend displays result