import json
import importlib.util
from pathlib import Path


def load_module(monkeypatch):
    monkeypatch.setenv("BUCKET_NAME", "medical-xray-input-test")
    monkeypatch.setenv("UPLOAD_PREFIX", "medical-input/")
    monkeypatch.setenv("URL_EXPIRES_SECONDS", "300")

    module_path = Path("src/generate_upload_url/app.py")
    spec = importlib.util.spec_from_file_location("generate_upload_url_app", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_upload_url_success(monkeypatch):
    app = load_module(monkeypatch)

    def fake_generate_presigned_url(ClientMethod, Params, ExpiresIn):
        assert ClientMethod == "put_object"
        assert Params["Bucket"] == "medical-xray-input-test"
        assert Params["Key"].startswith("medical-input/")
        assert Params["ContentType"] == "image/jpeg"
        assert ExpiresIn == 300
        return "https://example.com/fake-presigned-url"

    monkeypatch.setattr(app.s3, "generate_presigned_url", fake_generate_presigned_url)

    event = {
        "body": json.dumps({
            "filename": "test xray.jpeg",
            "contentType": "image/jpeg"
        })
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["uploadUrl"] == "https://example.com/fake-presigned-url"
    assert body["bucket"] == "medical-xray-input-test"
    assert body["key"].startswith("medical-input/")
    assert "test_xray.jpeg" in body["key"]
    assert body["expiresIn"] == 300


def test_generate_upload_url_rejects_unsupported_content_type(monkeypatch):
    app = load_module(monkeypatch)

    event = {
        "body": json.dumps({
            "filename": "document.pdf",
            "contentType": "application/pdf"
        })
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["error"] == "Unsupported file type"


def test_generate_upload_url_rejects_path_traversal_filename(monkeypatch):
    app = load_module(monkeypatch)

    event = {
        "body": json.dumps({
            "filename": "../../../../etc/test.jpeg",
            "contentType": "image/jpeg"
        })
    }

    result = app.lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["error"] == "Invalid filename"