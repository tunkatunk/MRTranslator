"""OCR processing utilities built on top of Tesseract."""
from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from PIL import Image
import pytesseract


@dataclass(frozen=True)
class CroppedRegion:
    """Representation of a cropped manga region."""

    image: Image.Image
    orientation_hint: Optional[str] = None


@dataclass
class OCRResult:
    """Result returned by :class:`OCRProcessor`."""

    text: str
    confidence: float
    orientation: str
    timestamp: float


@dataclass
class _CacheEntry:
    text: str
    timestamp: float


class _ResultCache:
    """Cache that tracks the most recent OCR outputs."""

    def __init__(self, max_entries: int) -> None:
        self._entries: Deque[_CacheEntry] = deque(maxlen=max_entries)

    def register(self, text: str) -> Tuple[bool, float]:
        """Register text in the cache.

        Returns a tuple ``(is_new, timestamp)``.
        """

        now = time.time()
        for entry in self._entries:
            if entry.text == text:
                entry.timestamp = now
                return False, entry.timestamp
        entry = _CacheEntry(text=text, timestamp=now)
        self._entries.append(entry)
        return True, entry.timestamp

    def get_recent(self) -> List[_CacheEntry]:
        return list(self._entries)


class OCRProcessor:
    """High level OCR processor that wraps Tesseract.

    Parameters
    ----------
    lang:
        Tesseract language pack to use. Defaults to ``"jpn"``.
    cache_size:
        Number of recent OCR outputs to cache for deduplication.
    osd_lang:
        Language to use for orientation detection. Defaults to ``"jpn"``.
    """

    def __init__(
        self,
        *,
        lang: str = "jpn",
        cache_size: int = 10,
        osd_lang: Optional[str] = "jpn",
    ) -> None:
        if cache_size <= 0:
            raise ValueError("cache_size must be positive")
        self.lang = lang
        self.osd_lang = osd_lang
        self._cache = _ResultCache(cache_size)

    def run(self, regions: Iterable[CroppedRegion]) -> List[OCRResult]:
        """Run OCR over a collection of cropped regions."""

        results: List[OCRResult] = []
        for region in regions:
            orientation = self._detect_orientation(region)
            prepared = self._prepare_image(region.image, orientation)
            text, confidence = self._extract_text(prepared, orientation)
            if not text:
                continue
            is_new, timestamp = self._cache.register(text)
            if not is_new:
                continue
            results.append(
                OCRResult(
                    text=text,
                    confidence=confidence,
                    orientation=orientation,
                    timestamp=timestamp,
                )
            )
        return results

    # ------------------------------------------------------------------
    def _detect_orientation(self, region: CroppedRegion) -> str:
        if region.orientation_hint in {"horizontal", "vertical"}:
            return region.orientation_hint
        image = region.image
        angle: Optional[int] = None
        if self.osd_lang is not None:
            try:
                osd = pytesseract.image_to_osd(image, lang=self.osd_lang)
                angle = self._parse_osd_angle(osd)
            except pytesseract.TesseractNotFoundError:
                raise
            except pytesseract.TesseractError:
                angle = None
        if angle is None:
            width, height = image.size
            if height > width * 1.2:
                return "vertical"
            return "horizontal"
        if angle in {90, 270}:
            return "vertical"
        return "horizontal"

    @staticmethod
    def _parse_osd_angle(osd_output: str) -> Optional[int]:
        match = re.search(r"Orientation in degrees:\s*(\d+)", osd_output)
        if not match:
            return None
        return int(match.group(1)) % 360

    @staticmethod
    def _prepare_image(image: Image.Image, orientation: str) -> Image.Image:
        if orientation == "vertical":
            return image.rotate(90, expand=True)
        return image

    def _extract_text(self, image: Image.Image, orientation: str) -> Tuple[str, float]:
        config = "--psm 5" if orientation == "vertical" else "--psm 6"
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                config=config,
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.TesseractNotFoundError:
            raise
        except pytesseract.TesseractError:
            return "", 0.0

        lines: Dict[int, List[str]] = {}
        confidences: List[float] = []
        texts = data.get("text", [])
        confs = data.get("conf", [])
        line_numbers = data.get("line_num", [])
        for text, conf, line in zip(texts, confs, line_numbers):
            cleaned = text.strip()
            if not cleaned:
                continue
            lines.setdefault(int(line), []).append(cleaned)
            try:
                conf_value = float(conf)
            except (TypeError, ValueError):
                continue
            if conf_value >= 0:
                confidences.append(conf_value)
        if not lines:
            return "", 0.0
        ordered_lines = [" ".join(lines[key]) for key in sorted(lines.keys())]
        extracted_text = "\n".join(ordered_lines)
        confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
        return extracted_text, confidence

    def recent_history(self) -> List[Tuple[str, float]]:
        """Return cached OCR outputs for inspection or debugging."""

        return [(entry.text, entry.timestamp) for entry in self._cache.get_recent()]
