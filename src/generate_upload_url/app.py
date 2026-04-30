import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    config=Config(signature_version="s3v4")
)

BUCKET_NAME = os.environ.get("BUCKET_NAME")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "medical-input/")
URL_EXPIRES_SECONDS = int(os.environ.get("URL_EXPIRES_SECONDS", "300"))

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png"
}


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


def lambda_handler(event, context):
    try:
        if not BUCKET_NAME:
            return response(500, {
                "error": "BUCKET_NAME environment variable is missing"
            })

        body = {}
        if event.get("body"):
            body = json.loads(event["body"])

        filename = body.get("filename", "xray-image.png")
        content_type = body.get("contentType", "image/png")

        if content_type not in ALLOWED_CONTENT_TYPES:
            return response(400, {
                "error": "Unsupported file type",
                "allowedContentTypes": list(ALLOWED_CONTENT_TYPES)
            })

        safe_filename = filename.replace(" ", "_")
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