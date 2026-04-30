import json
import os
import re
from decimal import Decimal

import boto3


# =========================
# AWS Clients
# =========================
dynamodb = boto3.resource("dynamodb")


# =========================
# Environment Variables
# =========================
TABLE_NAME = os.environ.get("TABLE_NAME", "ImageProcessingMetadata")
table = dynamodb.Table(TABLE_NAME)


# =========================
# Constants
# =========================
VALID_ID_PATTERN = re.compile(
    r"^medical-input/[A-Za-z0-9._\-/]+$"
)


# =========================
# Helper: Decimal -> JSON
# DynamoDB returns Decimal values.
# json.dumps cannot serialize Decimal directly.
# =========================
def decimal_default(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)

    raise TypeError


# =========================
# Helper: JSON response
# =========================
def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps(body, default=decimal_default)
    }


# =========================
# Helper: extract query parameter
# Supports HTTP API / REST API event shapes
# =========================
def get_query_param(event, name):
    params = event.get("queryStringParameters") or {}
    return params.get(name)


# =========================
# Helper: validate result id
# =========================
def is_valid_result_id(image_id):
    if not image_id:
        return False

    if not isinstance(image_id, str):
        return False

    if len(image_id) > 512:
        return False

    if not VALID_ID_PATTERN.match(image_id):
        return False

    if ".." in image_id:
        return False

    return True


# =========================
# Main Lambda Handler
# =========================
def lambda_handler(event, context):
    try:
        image_id = get_query_param(event, "id")

        if not image_id:
            return response(400, {
                "error": "Missing id parameter"
            })

        if not is_valid_result_id(image_id):
            return response(400, {
                "error": "Invalid id parameter",
                "message": "The id must be a valid S3 object key under medical-input/."
            })

        dynamodb_response = table.get_item(
            Key={
                "id": image_id
            }
        )

        item = dynamodb_response.get("Item")

        if not item:
            return response(404, {
                "status": "NOT_FOUND",
                "message": "No result found for the provided id",
                "id": image_id
            })

        return response(200, {
            "id": item.get("id", image_id),
            "status": item.get("status", "UNKNOWN"),
            "medicalFinding": item.get("medicalFinding", "UNKNOWN"),
            "riskLevel": item.get("riskLevel", "UNKNOWN"),
            "riskScore": item.get("riskScore", 0),
            "pneumoniaScore": item.get("pneumoniaScore", 0),
            "normalScore": item.get("normalScore", 0),
            "topLabel": item.get("topLabel", "UNKNOWN"),
            "topScore": item.get("topScore", 0),
            "medicalDescription": item.get(
                "medicalDescription",
                "Das Ergebnis ist noch nicht vollständig verfügbar."
            ),
            "disclaimer": item.get(
                "disclaimer",
                "Dieses Ergebnis ist nur eine technische KI-Vorhersage und keine medizinische Diagnose."
            ),
            "originalFile": item.get("originalFile", ""),
            "processedUrl": item.get("processedUrl", ""),
            "createdAt": item.get("createdAt", ""),
            "updatedAt": item.get("updatedAt", item.get("timestamp", "")),
            "expiresAt": item.get("expiresAt", "")
        })

    except Exception as e:
        print("Error reading medical result:", str(e))
        return response(500, {
            "error": "Internal server error"
        })