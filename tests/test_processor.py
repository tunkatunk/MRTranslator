import math
from typing import Any, Dict

import pytest
from PIL import Image

from mrtranslator.ocr.processor import CroppedRegion, OCRProcessor


@pytest.fixture
def sample_image() -> Image.Image:
    return Image.new("L", (64, 128), color=255)


def test_run_deduplicates_outputs(monkeypatch: pytest.MonkeyPatch, sample_image: Image.Image) -> None:
    def fake_osd(image: Image.Image, lang: str) -> str:
        return "Orientation in degrees: 0"

    def fake_data(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {
            "text": ["こんにちは", "世界"],
            "conf": ["95", "85"],
            "line_num": [1, 1],
        }

    monkeypatch.setattr("pytesseract.image_to_osd", fake_osd)
    monkeypatch.setattr("pytesseract.image_to_data", fake_data)

    processor = OCRProcessor(cache_size=5)
    regions = [CroppedRegion(sample_image), CroppedRegion(sample_image)]
    results = processor.run(regions)

    assert len(results) == 1
    assert results[0].text == "こんにちは 世界"
    assert math.isclose(results[0].confidence, (95 + 85) / 2 / 100)


def test_vertical_orientation_changes_psm(monkeypatch: pytest.MonkeyPatch, sample_image: Image.Image) -> None:
    def fake_data(image: Image.Image, lang: str, config: str, output_type: Any) -> Dict[str, Any]:
        assert config == "--psm 5"
        return {
            "text": ["縦", "書き"],
            "conf": ["88", "92"],
            "line_num": [1, 1],
        }

    monkeypatch.setattr("pytesseract.image_to_data", fake_data)

    processor = OCRProcessor(cache_size=5)
    regions = [CroppedRegion(sample_image, orientation_hint="vertical")]
    results = processor.run(regions)

    assert len(results) == 1
    assert results[0].orientation == "vertical"
    assert math.isclose(results[0].confidence, (88 + 92) / 2 / 100)
    history = processor.recent_history()
    assert len(history) == 1
    assert history[0][0] == "縦 書き"
