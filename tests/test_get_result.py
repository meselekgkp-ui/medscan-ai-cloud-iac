import json
import importlib.util
from decimal import Decimal
from pathlib import Path


def load_module(monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "ImageProcessingMetadataTest")

    module_path = Path("src/get_result/app.py")
    spec = importlib.util.spec_from_file_location("get_result_app", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTable:
    def __init__(self, item=None):
        self.item = item
        self.received_key = None

    def get_item(self, Key):
        self.received_key = Key
        if self.item is None:
            return {}
        return {"Item": self.item}


def test_get_result_missing_id_returns_400(monkeypatch):
    app = load_module(monkeypatch)

    event = {
        "queryStringParameters": {}
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["error"] == "Missing id parameter"


def test_get_result_invalid_id_returns_400(monkeypatch):
    app = load_module(monkeypatch)

    event = {
        "queryStringParameters": {
            "id": "../secret.txt"
        }
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["error"] == "Invalid id parameter"


def test_get_result_not_found_returns_404(monkeypatch):
    app = load_module(monkeypatch)

    fake_table = FakeTable(item=None)
    monkeypatch.setattr(app, "table", fake_table)

    image_id = "medical-input/test-image.jpeg"

    event = {
        "queryStringParameters": {
            "id": image_id
        }
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert body["status"] == "NOT_FOUND"
    assert body["id"] == image_id
    assert fake_table.received_key == {"id": image_id}


def test_get_result_success_returns_item(monkeypatch):
    app = load_module(monkeypatch)

    image_id = "medical-input/test-image.jpeg"

    fake_item = {
        "id": image_id,
        "status": "COMPLETED",
        "medicalFinding": "NO_PNEUMONIA_SUSPECTED",
        "riskLevel": "LOW",
        "riskScore": Decimal("0.12"),
        "pneumoniaScore": Decimal("0.12"),
        "normalScore": Decimal("0.88"),
        "topLabel": "NORMAL",
        "topScore": Decimal("0.88"),
        "medicalDescription": "Test description",
        "disclaimer": "Test disclaimer",
        "originalFile": image_id,
        "processedUrl": "s3://bucket/medical-processed/test-image.jpeg",
        "createdAt": "2026-04-29T10:00:00+00:00",
        "updatedAt": "2026-04-29T10:01:00+00:00",
        "expiresAt": 1777543942
    }

    fake_table = FakeTable(item=fake_item)
    monkeypatch.setattr(app, "table", fake_table)

    event = {
        "queryStringParameters": {
            "id": image_id
        }
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["id"] == image_id
    assert body["status"] == "COMPLETED"
    assert body["medicalFinding"] == "NO_PNEUMONIA_SUSPECTED"
    assert body["riskLevel"] == "LOW"
    assert body["pneumoniaScore"] == 0.12
    assert body["normalScore"] == 0.88
    assert body["topLabel"] == "NORMAL"
    assert body["expiresAt"] == 1777543942


def test_is_valid_result_id_accepts_valid_medical_input_key(monkeypatch):
    app = load_module(monkeypatch)

    assert app.is_valid_result_id(
        "medical-input/20260429-100927-test.jpeg"
    ) is True


def test_is_valid_result_id_rejects_wrong_prefix(monkeypatch):
    app = load_module(monkeypatch)

    assert app.is_valid_result_id(
        "medical-processed/test.jpeg"
    ) is False


def test_is_valid_result_id_rejects_double_dot(monkeypatch):
    app = load_module(monkeypatch)

    assert app.is_valid_result_id("medical-input/../secret.jpeg") is False


def test_is_valid_result_id_rejects_too_long_id(monkeypatch):
    app = load_module(monkeypatch)

    long_id = "medical-input/" + "a" * 500
    assert app.is_valid_result_id(long_id) is False


def test_get_result_dynamodb_error_returns_500(monkeypatch):
    app = load_module(monkeypatch)

    class FailingTable:
        def get_item(self, Key):
            raise RuntimeError("DynamoDB unavailable")

    monkeypatch.setattr(app, "table", FailingTable())

    event = {
        "queryStringParameters": {
            "id": "medical-input/test-image.jpeg"
        }
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 500
    assert body["error"] == "Internal server error"