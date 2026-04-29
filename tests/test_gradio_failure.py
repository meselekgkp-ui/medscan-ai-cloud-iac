import importlib.util
import time
from decimal import Decimal
from pathlib import Path

import pytest


def load_processing_module():
    module_path = Path("src/processing/app.py")
    spec = importlib.util.spec_from_file_location("processing_app_gradio_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gradio_timeout_wrapper_returns_result(monkeypatch):
    app = load_processing_module()

    expected_result = {
        "status": "COMPLETED",
        "medicalFinding": "NO_PNEUMONIA_SUSPECTED",
        "riskLevel": "LOW"
    }

    def fake_analyze_with_gradio(local_image_path):
        return expected_result

    monkeypatch.setattr(app, "analyze_with_gradio", fake_analyze_with_gradio)

    result = app.analyze_with_gradio_timeout(
        "fake-image.jpeg",
        timeout_seconds=1
    )

    assert result == expected_result


def test_gradio_timeout_wrapper_raises_timeout(monkeypatch):
    app = load_processing_module()

    def slow_analyze_with_gradio(local_image_path):
        time.sleep(0.2)
        return {"status": "COMPLETED"}

    monkeypatch.setattr(app, "analyze_with_gradio", slow_analyze_with_gradio)

    with pytest.raises(TimeoutError):
        app.analyze_with_gradio_timeout(
            "fake-image.jpeg",
            timeout_seconds=0.01
        )


def test_gradio_timeout_wrapper_raises_model_error(monkeypatch):
    app = load_processing_module()

    def failing_analyze_with_gradio(local_image_path):
        raise RuntimeError("Gradio service unavailable")

    monkeypatch.setattr(app, "analyze_with_gradio", failing_analyze_with_gradio)

    with pytest.raises(RuntimeError, match="Gradio service unavailable"):
        app.analyze_with_gradio_timeout(
            "fake-image.jpeg",
            timeout_seconds=1
        )


def test_build_model_error_result():
    app = load_processing_module()

    result = app.build_model_error_result("Gradio service unavailable")

    assert result["status"] == "MODEL_ERROR"
    assert result["medicalFinding"] == "UNKNOWN"
    assert result["riskLevel"] == "UNKNOWN"
    assert result["riskScore"] == Decimal("0")
    assert result["pneumoniaScore"] == Decimal("0")
    assert result["normalScore"] == Decimal("0")
    assert result["topLabel"] == "UNKNOWN"
    assert result["topScore"] == Decimal("0")
    assert result["modelScores"] == []
    assert "Gradio service unavailable" in result["hfError"]