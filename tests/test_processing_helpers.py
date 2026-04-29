import json
import importlib.util
from decimal import Decimal
from pathlib import Path


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
