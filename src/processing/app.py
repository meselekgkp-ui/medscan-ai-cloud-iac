import json
import boto3
import urllib.parse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from PIL import Image
import io
import os
import tempfile
import hashlib

from botocore.exceptions import ClientError
from gradio_client import Client, handle_file


# =========================
# AWS Clients
# =========================
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


# =========================
# Environment Variables
# =========================
TABLE_NAME = os.environ.get("TABLE_NAME", "ImageProcessingMetadata")
HF_SPACE_ID = os.environ.get(
    "HF_SPACE_ID",
    "Zakia/pneumonia-detection-with-fast.ai-and-gradio"
)
TTL_RETENTION_DAYS = int(os.environ.get("TTL_RETENTION_DAYS", "1"))
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "10"))

table = dynamodb.Table(TABLE_NAME)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png"
}


# =========================
# Helper: JSON Response
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
# Helper: float -> Decimal
# DynamoDB does not accept float directly
# =========================
def to_decimal(value):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


# =========================
# Helper: SHA-256
# =========================
def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


# =========================
# Helper: normalize S3 event from direct S3 or SQS
# =========================
def get_s3_record_from_event(event):
    """
    Supports:
    1. Direct S3 trigger
    2. S3 event delivered through SQS
    """

    first_record = event["Records"][0]

    # SQS -> Lambda
    if first_record.get("eventSource") == "aws:sqs":
        body = json.loads(first_record["body"])

        # S3 sometimes sends a test event without Records
        if "Records" not in body:
            print("Ignoring non-S3 test message from SQS:", body)
            return None

        return body["Records"][0]

    # Direct S3 -> Lambda
    return first_record


# =========================
# Helper: Idempotency / Duplicate Protection
# =========================
def should_process_image(key, bucket_name):
    """
    Idempotency check:
    - Uses S3 object key as DynamoDB id.
    - If the image was already processed, skip it.
    - If no item exists, create a PROCESSING record.
    """

    now_utc = datetime.now(timezone.utc)
    expires_at = int((now_utc + timedelta(days=TTL_RETENTION_DAYS)).timestamp())

    processing_item = {
        "id": key,
        "pipeline": "MedicalChestXrayTriage",
        "bucket": bucket_name,
        "originalFile": key,
        "originalS3Url": f"s3://{bucket_name}/{key}",
        "status": "PROCESSING",
        "createdAt": now_utc.isoformat(),
        "updatedAt": now_utc.isoformat(),
        "expiresAt": expires_at,
        "retentionDays": TTL_RETENTION_DAYS,
        "ttlPurpose": "Automatic deletion of medical AI metadata after retention period"
    }

    try:
        table.put_item(
            Item=processing_item,
            ConditionExpression="attribute_not_exists(id)"
        )

        print(f"✅ Idempotency lock created for: {key}")
        return True, now_utc, expires_at

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code != "ConditionalCheckFailedException":
            raise e

        existing_response = table.get_item(Key={"id": key})
        existing_item = existing_response.get("Item", {})
        existing_status = existing_item.get("status", "UNKNOWN")

        print(f"⚠️ Duplicate event detected for: {key}")
        print(f"Existing status: {existing_status}")

        already_finished_statuses = [
            "COMPLETED",
            "NEEDS_HUMAN_REVIEW",
            "NEEDS_URGENT_HUMAN_REVIEW",
            "MODEL_ERROR",
            "INVALID_FILE"
        ]

        if existing_status in already_finished_statuses:
            print("✅ Image already processed. Skipping duplicate event.")
            return False, None, None

        if existing_status == "PROCESSING":
            print("⏳ Image is already being processed. Skipping duplicate event.")
            return False, None, None

        if existing_status == "PROCESSING_FAILED":
            print("🔁 Previous processing failed. Retrying processing.")

            retry_time = datetime.now(timezone.utc)
            retry_expires_at = int(
                (retry_time + timedelta(days=TTL_RETENTION_DAYS)).timestamp()
            )

            table.update_item(
                Key={"id": key},
                UpdateExpression=(
                    "SET #s = :s, updatedAt = :u, expiresAt = :e, retryReason = :r"
                ),
                ExpressionAttributeNames={
                    "#s": "status"
                },
                ExpressionAttributeValues={
                    ":s": "PROCESSING",
                    ":u": retry_time.isoformat(),
                    ":e": retry_expires_at,
                    ":r": "Retry after previous processing failure"
                }
            )

            return True, retry_time, retry_expires_at

        print("⚠️ Existing item has unknown status. Skipping for safety.")
        return False, None, None


# =========================
# Helper: Save invalid file status
# =========================
def save_invalid_file_status(
    key,
    bucket_name,
    reason,
    created_at_utc,
    expires_at,
    content_type=None,
    original_size=None,
    original_sha256=None
):
    now_utc = datetime.now(timezone.utc)

    item = {
        "id": key,
        "pipeline": "MedicalChestXrayTriage",
        "bucket": bucket_name,
        "originalFile": key,
        "originalS3Url": f"s3://{bucket_name}/{key}",
        "contentType": content_type or "unknown",
        "originalSize": original_size or 0,
        "originalSha256": original_sha256 or "",
        "status": "INVALID_FILE",
        "validationError": reason,
        "createdAt": created_at_utc.isoformat(),
        "updatedAt": now_utc.isoformat(),
        "expiresAt": expires_at,
        "retentionDays": TTL_RETENTION_DAYS,
        "ttlPurpose": "Automatic deletion of medical AI metadata after retention period",
        "disclaimer": (
            "Dieses Ergebnis ist nur eine technische KI-Vorhersage "
            "und keine medizinische Diagnose."
        )
    }

    table.put_item(Item=item)
    print(f"⚠️ Invalid file saved in DynamoDB: {reason}")


# =========================
# Helper: analyze image with Hugging Face Gradio Space
# =========================
def analyze_with_gradio(local_image_path):
    """
    Calls Hugging Face Gradio Space and returns pneumonia/normal scores.
    """

    client = Client(HF_SPACE_ID)

    result = client.predict(
        img=handle_file(local_image_path),
        api_name="/predict"
    )

    print("Gradio Result Type:", type(result))
    print("Gradio Result Raw:", result)

    scores = []

    if isinstance(result, dict):
        confidences = result.get("confidences", [])

        for item in confidences:
            label = str(item.get("label", "")).upper()
            score = float(item.get("confidence", 0))
            scores.append({
                "label": label,
                "score": score
            })

    elif isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                label = str(item.get("label", "")).upper()
                score = float(item.get("score", item.get("confidence", 0)))
                scores.append({
                    "label": label,
                    "score": score
                })

    pneumonia_score = 0.0
    normal_score = 0.0
    top_label = "UNKNOWN"
    top_score = 0.0

    for item in scores:
        label = item["label"]
        score = item["score"]

        if "PNEUMONIA" in label:
            pneumonia_score = score

        if "NORMAL" in label:
            normal_score = score

        if score > top_score:
            top_score = score
            top_label = label

    if pneumonia_score >= 0.70:
        medical_finding = "PNEUMONIA_SUSPECTED"
        risk_level = "HIGH"
        status = "NEEDS_URGENT_HUMAN_REVIEW"
        description = (
            f"Das Thorax-Röntgenbild wurde vom KI-Modell als auffällig eingestuft. "
            f"Der Pneumonie-Score beträgt {pneumonia_score * 100:.2f}%, "
            f"der Normal-Score beträgt {normal_score * 100:.2f}%. "
            f"Die Aufnahme sollte priorisiert durch medizinisches Fachpersonal überprüft werden. "
            f"Diese Einschätzung ist keine medizinische Diagnose."
        )

    elif pneumonia_score >= 0.40:
        medical_finding = "PNEUMONIA_UNCLEAR"
        risk_level = "MEDIUM"
        status = "NEEDS_HUMAN_REVIEW"
        description = (
            f"Das KI-Modell erkennt ein unklar auffälliges Muster. "
            f"Der Pneumonie-Score beträgt {pneumonia_score * 100:.2f}%, "
            f"der Normal-Score beträgt {normal_score * 100:.2f}%. "
            f"Eine medizinische Überprüfung ist erforderlich."
        )

    else:
        medical_finding = "NO_PNEUMONIA_SUSPECTED"
        risk_level = "LOW"
        status = "COMPLETED"
        description = (
            f"Das KI-Modell stuft das Thorax-Röntgenbild eher als unauffällig ein. "
            f"Der Pneumonie-Score beträgt {pneumonia_score * 100:.2f}%, "
            f"der Normal-Score beträgt {normal_score * 100:.2f}%. "
            f"Auch dieses Ergebnis ersetzt keine ärztliche Diagnose."
        )

    return {
        "medicalFinding": medical_finding,
        "riskLevel": risk_level,
        "riskScore": to_decimal(pneumonia_score),
        "pneumoniaScore": to_decimal(pneumonia_score),
        "normalScore": to_decimal(normal_score),
        "topLabel": top_label,
        "topScore": to_decimal(top_score),
        "modelScores": [
            {
                "label": item["label"],
                "score": to_decimal(item["score"])
            }
            for item in scores
        ],
        "status": status,
        "medicalDescription": description,
        "hfRawResult": json.dumps(result, default=str)
    }


# =========================
# Main Lambda Handler
# =========================
def lambda_handler(event, context):
    print("=== Medical X-Ray Processing Lambda started ===")

    key = None
    bucket_name = None
    temp_file_path = None

    try:
        record = get_s3_record_from_event(event)

        if record is None:
            return response(200, {
                "message": "Ignored non-S3 event"
            })

        bucket_name = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        print(f"Processing medical image: {key} from bucket: {bucket_name}")

        # Avoid endless loop
        if key.startswith("medical-processed/") or key.startswith("processed/"):
            print(f"Skipping already processed file: {key}")
            return response(200, {
                "message": "Skipped processed file"
            })

        # Only process medical-input/
        if not key.startswith("medical-input/"):
            print(f"Skipping file outside medical-input/: {key}")
            return response(200, {
                "message": "Skipped non-input file"
            })

        # Idempotency check
        should_process, created_at_utc, expires_at = should_process_image(
            key,
            bucket_name
        )

        if not should_process:
            return response(200, {
                "message": "Duplicate event skipped",
                "id": key
            })

        # Load original image from S3
        s3_response = s3.get_object(Bucket=bucket_name, Key=key)
        file_content = s3_response["Body"].read()

        original_size = s3_response.get("ContentLength", len(file_content))
        content_type = s3_response.get("ContentType", "application/octet-stream")
        original_sha256 = sha256_hex(file_content)

        print(f"Content-Type: {content_type}")
        print(f"Original size: {original_size}")
        print(f"Original SHA-256: {original_sha256}")

        # File size validation
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if original_size > max_bytes:
            save_invalid_file_status(
                key=key,
                bucket_name=bucket_name,
                reason=f"File is larger than {MAX_FILE_SIZE_MB} MB",
                created_at_utc=created_at_utc,
                expires_at=expires_at,
                content_type=content_type,
                original_size=original_size,
                original_sha256=original_sha256
            )
            return response(200, {
                "message": "Invalid file skipped",
                "reason": "File too large",
                "id": key
            })

        # Content type validation
        if content_type not in ALLOWED_CONTENT_TYPES:
            save_invalid_file_status(
                key=key,
                bucket_name=bucket_name,
                reason=f"Unsupported content type: {content_type}",
                created_at_utc=created_at_utc,
                expires_at=expires_at,
                content_type=content_type,
                original_size=original_size,
                original_sha256=original_sha256
            )
            return response(200, {
                "message": "Invalid file skipped",
                "reason": "Unsupported content type",
                "id": key
            })

        # Open image with PIL
        try:
            image = Image.open(io.BytesIO(file_content))
            image.verify()
        except Exception as validation_error:
            save_invalid_file_status(
                key=key,
                bucket_name=bucket_name,
                reason=f"Image validation failed: {str(validation_error)}",
                created_at_utc=created_at_utc,
                expires_at=expires_at,
                content_type=content_type,
                original_size=original_size,
                original_sha256=original_sha256
            )
            return response(200, {
                "message": "Invalid image skipped",
                "reason": str(validation_error),
                "id": key
            })

        # Reopen image after verify()
        image = Image.open(io.BytesIO(file_content))
        original_width, original_height = image.size
        image_format = image.format or "JPEG"

        # Create processed/resized image
        img_copy = image.copy()
        img_copy.thumbnail((1200, 1200), Image.LANCZOS)

        buffer = io.BytesIO()

        if image_format.upper() in ["JPEG", "JPG"] and img_copy.mode in ["RGBA", "P"]:
            img_copy = img_copy.convert("RGB")

        img_copy.save(buffer, format=image_format, optimize=True, quality=85)
        processed_content = buffer.getvalue()
        processed_sha256 = sha256_hex(processed_content)

        filename_only = key.split("/")[-1]
        processed_key = (
            f"medical-processed/"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
            f"{filename_only}"
        )

        s3.put_object(
            Bucket=bucket_name,
            Key=processed_key,
            Body=processed_content,
            ContentType=content_type
        )

        print(f"Processed image saved: {processed_key}")
        print(f"Processed SHA-256: {processed_sha256}")

        # Temporary file for Gradio
        file_extension = ".jpg"
        if content_type == "image/png":
            file_extension = ".png"

        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # AI analysis
        try:
            medical_result = analyze_with_gradio(temp_file_path)

        except Exception as hf_error:
            print("Gradio/Hugging Face error:", str(hf_error))

            medical_result = {
                "medicalFinding": "UNKNOWN",
                "riskLevel": "UNKNOWN",
                "riskScore": Decimal("0"),
                "pneumoniaScore": Decimal("0"),
                "normalScore": Decimal("0"),
                "topLabel": "UNKNOWN",
                "topScore": Decimal("0"),
                "modelScores": [],
                "status": "MODEL_ERROR",
                "medicalDescription": (
                    "Die automatische KI-Analyse konnte nicht durchgeführt werden. "
                    "Eine menschliche Überprüfung ist erforderlich."
                ),
                "hfRawResult": "",
                "hfError": str(hf_error)
            }

        print("Medical Result:", medical_result)

        finished_at_utc = datetime.now(timezone.utc)

        item = {
            "id": key,
            "pipeline": "MedicalChestXrayTriage",

            # TTL / Idempotency fields
            "createdAt": created_at_utc.isoformat(),
            "updatedAt": finished_at_utc.isoformat(),
            "expiresAt": expires_at,
            "retentionDays": TTL_RETENTION_DAYS,
            "ttlPurpose": "Automatic deletion of medical AI metadata after retention period",

            "originalFile": key,
            "originalS3Url": f"s3://{bucket_name}/{key}",
            "processedUrl": f"s3://{bucket_name}/{processed_key}",

            "bucket": bucket_name,
            "contentType": content_type,
            "originalSize": original_size,
            "originalWidth": original_width,
            "originalHeight": original_height,
            "originalSha256": original_sha256,
            "processedSha256": processed_sha256,

            "hfModelId": HF_SPACE_ID,
            "timestamp": finished_at_utc.isoformat(),

            "medicalFinding": medical_result["medicalFinding"],
            "riskLevel": medical_result["riskLevel"],
            "riskScore": medical_result["riskScore"],
            "pneumoniaScore": medical_result["pneumoniaScore"],
            "normalScore": medical_result["normalScore"],
            "topLabel": medical_result["topLabel"],
            "topScore": medical_result["topScore"],
            "modelScores": medical_result["modelScores"],
            "status": medical_result["status"],
            "medicalDescription": medical_result["medicalDescription"],

            "hfRawResult": medical_result.get("hfRawResult", ""),
            "hfError": medical_result.get("hfError", ""),

            "disclaimer": (
                "Dieses Ergebnis ist nur eine technische KI-Vorhersage "
                "und keine medizinische Diagnose."
            )
        }

        table.put_item(Item=item)

        print("✅ Medical triage metadata saved successfully")
        print(f"✅ DynamoDB ID saved as: {key}")

        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return response(200, {
            "message": "Medical image processed successfully",
            "id": key,
            "result": {
                "medicalFinding": medical_result["medicalFinding"],
                "riskLevel": medical_result["riskLevel"],
                "status": medical_result["status"]
            }
        })

    except Exception as e:
        print("❌ Processing error:", str(e))

        if key is not None:
            try:
                table.update_item(
                    Key={"id": key},
                    UpdateExpression="SET #s = :s, updatedAt = :u, errorMessage = :e",
                    ExpressionAttributeNames={
                        "#s": "status"
                    },
                    ExpressionAttributeValues={
                        ":s": "PROCESSING_FAILED",
                        ":u": datetime.now(timezone.utc).isoformat(),
                        ":e": str(e)
                    }
                )
                print("⚠️ DynamoDB status updated to PROCESSING_FAILED")

            except Exception as update_error:
                print("⚠️ Could not update failure status:", str(update_error))

        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

        # Important: raise error so SQS can retry and eventually send to DLQ
        raise e