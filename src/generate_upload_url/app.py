import json
import os
import re
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config


# =========================
# AWS Client
# =========================
# Signature Version 4 is required when the S3 bucket uses SSE-KMS.
s3 = boto3.client(
    "s3",
    config=Config(signature_version="s3v4")
)


# =========================
# Environment Variables
# =========================
BUCKET_NAME = os.environ.get("BUCKET_NAME")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "medical-input/")
URL_EXPIRES_SECONDS = int(os.environ.get("URL_EXPIRES_SECONDS", "300"))


# =========================
# Constants
# =========================
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png"
}

SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


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
        "body": json.dumps(body, default=str)
    }


# =========================
# Helper: sanitize filename
# =========================
def sanitize_filename(filename):
    """
    Creates a safe filename for S3 object keys.

    Important:
    - Rejects path separators.
    - Rejects '..' to prevent traversal-like object keys.
    - Allows only simple safe filename characters.
    """

    if not isinstance(filename, str):
        raise ValueError("Invalid filename")

    filename = filename.strip()

    if not filename:
        raise ValueError("Invalid filename")

    # Reject folders and traversal-like names.
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("Invalid filename")

    # Replace spaces with underscores.
    safe_filename = filename.replace(" ", "_")

    # Replace remaining unsafe characters with underscores.
    safe_filename = re.sub(r"[^A-Za-z0-9._-]", "_", safe_filename)

    if (
        not safe_filename
        or safe_filename in [".", ".."]
        or not SAFE_FILENAME_PATTERN.match(safe_filename)
    ):
        raise ValueError("Invalid filename")

    return safe_filename


# =========================
# Main Lambda Handler
# =========================
def lambda_handler(event, context):
    try:
        # CORS preflight
        request_context = event.get("requestContext", {})
        http_info = request_context.get("http", {})
        method = http_info.get("method") or event.get("httpMethod")

        if method == "OPTIONS":
            return response(200, {
                "message": "CORS preflight OK"
            })

        if not BUCKET_NAME:
            return response(500, {
                "error": "BUCKET_NAME environment variable is missing"
            })

        body = {}

        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except json.JSONDecodeError:
                return response(400, {
                    "error": "Invalid JSON body"
                })

        filename = body.get("filename", "xray-image.png")
        content_type = body.get("contentType", "image/png")

        if content_type not in ALLOWED_CONTENT_TYPES:
            return response(400, {
                "error": "Unsupported file type",
                "allowedContentTypes": sorted(list(ALLOWED_CONTENT_TYPES))
            })

        try:
            safe_filename = sanitize_filename(filename)
        except ValueError:
            return response(400, {
                "error": "Invalid filename",
                "message": "Filename must not contain path separators, '..', or unsafe characters."
            })

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        object_key = f"{UPLOAD_PREFIX}{timestamp}-{unique_id}-{safe_filename}"

        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": object_key,
                "ContentType": content_type
            },
            ExpiresIn=URL_EXPIRES_SECONDS
        )

        return response(200, {
            "uploadUrl": upload_url,
            "bucket": BUCKET_NAME,
            "key": object_key,
            "expiresIn": URL_EXPIRES_SECONDS
        })

    except Exception as e:
        print("Error generating upload URL:", str(e))
        return response(500, {
            "error": "Internal server error"
        })