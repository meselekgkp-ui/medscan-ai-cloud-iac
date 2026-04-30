import json
import importlib.util
from decimal import Decimal
from pathlib import Path
import io
from PIL import Image


def load_module():
    module_path = Path("src/processing/app.py")
    spec = importlib.util.spec_from_file_location("processing_app", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_to_decimal_valid_number():
    app = load_module()
    assert app.to_decimal(0.75) == Decimal("0.75")


def test_to_decimal_invalid_value_returns_zero():
    app = load_module()
    assert app.to_decimal("not-a-number") == Decimal("0")


def test_sha256_hex():
    app = load_module()
    assert app.sha256_hex(b"hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_get_s3_record_from_direct_s3_event():
    app = load_module()

    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "medical-xray-input-test"},
                    "object": {"key": "medical-input/test.jpeg"}
                }
            }
        ]
    }

    record = app.get_s3_record_from_event(event)

    assert record["s3"]["bucket"]["name"] == "medical-xray-input-test"
    assert record["s3"]["object"]["key"] == "medical-input/test.jpeg"


def test_get_s3_record_from_sqs_event():
    app = load_module()

    s3_event_body = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "medical-xray-input-test"},
                    "object": {"key": "medical-input/from-sqs.jpeg"}
                }
            }
        ]
    }

    event = {
        "Records": [
            {
                "eventSource": "aws:sqs",
                "body": json.dumps(s3_event_body)
            }
        ]
    }

    record = app.get_s3_record_from_event(event)

    assert record["s3"]["bucket"]["name"] == "medical-xray-input-test"
    assert record["s3"]["object"]["key"] == "medical-input/from-sqs.jpeg"


def test_get_s3_record_ignores_s3_test_event_from_sqs():
    app = load_module()

    s3_test_event_body = {
        "Service": "Amazon S3",
        "Event": "s3:TestEvent",
        "Bucket": "medical-xray-input-test"
    }

    event = {
        "Records": [
            {
                "eventSource": "aws:sqs",
                "body": json.dumps(s3_test_event_body)
            }
        ]
    }

    assert app.get_s3_record_from_event(event) is None


def make_gradio_result(pneumonia_score, normal_score):
    return {
        "label": "PNEUMONIA" if pneumonia_score > normal_score else "NORMAL",
        "confidences": [
            {"label": "PNEUMONIA", "confidence": pneumonia_score},
            {"label": "NORMAL", "confidence": normal_score}
        ]
    }


def test_analyze_with_gradio_classifies_high_risk(monkeypatch):
    app = load_module()

    class FakeClient:
        def __init__(self, space_id): pass
        def predict(self, img, api_name):
            return make_gradio_result(0.95, 0.05)

    monkeypatch.setattr(app, "Client", FakeClient)
    monkeypatch.setattr(app, "handle_file", lambda x: x)

    result = app.analyze_with_gradio("fake.jpeg")

    assert result["status"] == "NEEDS_URGENT_HUMAN_REVIEW"
    assert result["riskLevel"] == "HIGH"
    assert result["medicalFinding"] == "PNEUMONIA_SUSPECTED"
    assert float(result["pneumoniaScore"]) == 0.95


def test_analyze_with_gradio_classifies_medium_risk(monkeypatch):
    app = load_module()

    class FakeClient:
        def __init__(self, space_id): pass
        def predict(self, img, api_name):
            return make_gradio_result(0.55, 0.45)

    monkeypatch.setattr(app, "Client", FakeClient)
    monkeypatch.setattr(app, "handle_file", lambda x: x)

    result = app.analyze_with_gradio("fake.jpeg")

    assert result["status"] == "NEEDS_HUMAN_REVIEW"
    assert result["riskLevel"] == "MEDIUM"
    assert result["medicalFinding"] == "PNEUMONIA_UNCLEAR"


def test_analyze_with_gradio_classifies_low_risk(monkeypatch):
    app = load_module()

    class FakeClient:
        def __init__(self, space_id): pass
        def predict(self, img, api_name):
            return make_gradio_result(0.02, 0.98)

    monkeypatch.setattr(app, "Client", FakeClient)
    monkeypatch.setattr(app, "handle_file", lambda x: x)

    result = app.analyze_with_gradio("fake.jpeg")

    assert result["status"] == "COMPLETED"
    assert result["riskLevel"] == "LOW"
    assert result["medicalFinding"] == "NO_PNEUMONIA_SUSPECTED"


def test_rgba_png_converts_to_rgb_before_save():
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    img_copy = img.copy()

    if img_copy.mode in ["RGBA", "P"]:
        img_copy = img_copy.convert("RGB")

    assert img_copy.mode == "RGB"

    buffer = io.BytesIO()
    img_copy.save(buffer, format="JPEG", quality=85)
    assert len(buffer.getvalue()) > 0
