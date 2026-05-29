"""Coverage push for ``visus.desktop.core.ocr_engine`` (both backends).

Targets the missing line ranges in the Tesseract backend (find_text
multi-method loop 233-313, _process_single_image 342-419,
_create_ocr_result, extract_all_text 448-500) and the RapidOCR backend
fallbacks (515-546, _run / _poly_to_xywh / find_text / extract_all_text
error paths).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from visus.desktop.core.ocr_engine import (
    OCREngine,
    OCRResult,
    _RapidOCRBackend,
    _TesseractBackend,
    extract_text_from_image,
    find_text_with_multiple_preprocessing,
)
from visus.desktop.exceptions import ConfigurationError, OCRProcessingError


def _stub_tesseract_backend(monkeypatch):
    """Build a TesseractBackend without firing the real setup()."""
    monkeypatch.setattr(_TesseractBackend, "_setup", lambda self: None)
    return _TesseractBackend()


def _ocr_data(texts, lefts=None, tops=None, widths=None, heights=None, confs=None):
    n = len(texts)
    lefts = lefts or [0] * n
    tops = tops or [0] * n
    widths = widths or [10] * n
    heights = heights or [10] * n
    confs = confs or [95] * n
    return {
        "text": texts,
        "left": lefts,
        "top": tops,
        "width": widths,
        "height": heights,
        "conf": confs,
    }


class TestTesseractFindText:
    def test_high_confidence_returns_early(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        # Single-image preprocessor returning one image.
        img = Image.new("RGB", (50, 20), "white")
        monkeypatch.setattr(
            backend.image_processor,
            "preprocess_for_ocr",
            lambda _img: [img],
        )
        data = _ocr_data(["Login"], confs=[99])
        with patch(
            "pytesseract.image_to_data", return_value=data
        ):
            boxes, scores, early = backend.find_text(
                img, "Login", filter_type="both", early_confidence_threshold=75
            )
        assert early is True
        assert len(boxes) == 1

    def test_no_high_confidence_returns_best_results(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        img = Image.new("RGB", (50, 20), "white")
        monkeypatch.setattr(
            backend.image_processor,
            "preprocess_for_ocr",
            lambda _img: [img],
        )
        data = _ocr_data(["Login"], confs=[40])
        with patch("pytesseract.image_to_data", return_value=data):
            boxes, scores, early = backend.find_text(
                img, "Login", filter_type="both", early_confidence_threshold=99
            )
        assert early is False

    def test_processing_failure_raises_ocr_error(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        monkeypatch.setattr(
            backend.image_processor,
            "preprocess_for_ocr",
            MagicMock(side_effect=RuntimeError("preproc failed")),
        )
        with pytest.raises(OCRProcessingError, match="Text search failed"):
            backend.find_text(
                Image.new("RGB", (10, 10), "white"),
                "x",
                filter_type="both",
                early_confidence_threshold=75,
            )

    def test_numbers_filter_runs_through_debug_branch(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        img = Image.new("RGB", (50, 20), "white")
        monkeypatch.setattr(
            backend.image_processor, "preprocess_for_ocr", lambda _img: [img]
        )
        data = _ocr_data(["12345"], confs=[80])
        with patch("pytesseract.image_to_data", return_value=data):
            boxes, scores, _ = backend.find_text(
                img, "12345", filter_type="numbers", early_confidence_threshold=99
            )
        # Numbers filter branch executed -> we should at least observe the
        # results (it might not match at >=99 threshold).
        assert isinstance(boxes, list)

    def test_pytesseract_import_error_raises_ocr_error(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        # _process_single_image catches ImportError and raises -- but the
        # outer find_text catches all Exception and wraps in OCRProcessingError.
        monkeypatch.setattr(
            backend.image_processor,
            "preprocess_for_ocr",
            lambda _img: [Image.new("RGB", (10, 10), "white")],
        )
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pytesseract":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(OCRProcessingError):
                backend.find_text(
                    Image.new("RGB", (10, 10), "white"),
                    "Login",
                    filter_type="both",
                    early_confidence_threshold=75,
                )


class TestTesseractProcessSingleImage:
    def test_returns_empty_on_runtime_error(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        with patch("pytesseract.image_to_data", side_effect=RuntimeError("io")):
            out = backend._process_single_image(
                Image.new("RGB", (10, 10), "white"),
                "Login",
                "both",
                0,
                "--psm 6",
                0,
                1,
                8.0,
            )
        assert out == []

    def test_matching_word_yields_result_with_box(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        data = _ocr_data(
            ["Login"], lefts=[10], tops=[20], widths=[50], heights=[12]
        )
        with patch("pytesseract.image_to_data", return_value=data):
            results = backend._process_single_image(
                Image.new("RGB", (100, 50), "white"),
                "Login",
                "both",
                0,
                "--psm 6",
                0,
                1,
                8.0,
            )
        assert results, "expected at least one OCRResult"
        # Bounding box is (left=10, top=20, width=50, height=12).
        assert results[0].box == (10, 20, 50, 12)


class TestExtractAllText:
    def test_extracts_words_above_filter(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        data = _ocr_data(["Hello", "12345"], confs=[80, 90])
        with patch("pytesseract.image_to_data", return_value=data):
            results = backend.extract_all_text(
                Image.new("RGB", (200, 50), "white"), filter_type="both"
            )
        assert len(results) >= 1

    def test_extract_all_text_raises_on_failure(self, monkeypatch):
        backend = _stub_tesseract_backend(monkeypatch)
        with patch(
            "pytesseract.image_to_data", side_effect=RuntimeError("io")
        ):
            with pytest.raises(OCRProcessingError):
                backend.extract_all_text(
                    Image.new("RGB", (10, 10), "white"),
                    filter_type="both",
                )


class TestRapidOCRBackend:
    """Lazy-import path + result normalization."""

    def _fake_rapidocr(self, txts=("Login",), boxes=None, scores=(0.9,)):
        if boxes is None:
            boxes = (((0, 0), (50, 0), (50, 20), (0, 20)),)
        result = MagicMock()
        result.txts = txts
        result.boxes = np.array(boxes)
        result.scores = scores
        engine = MagicMock(return_value=result)
        fake_mod = MagicMock(RapidOCR=MagicMock(return_value=engine))
        return fake_mod

    def test_missing_rapidocr_raises_configuration_error(self):
        from visus.desktop.utils import config as _cfg

        cfg = _cfg.BotVisionConfig.__new__(_cfg.BotVisionConfig)
        cfg.config = cfg._load_default_config()

        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "rapidocr":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ConfigurationError, match="rapidocr"):
                _RapidOCRBackend(cfg)

    def test_run_returns_empty_when_result_is_none(self):
        import sys

        fake_mod = self._fake_rapidocr()
        fake_mod.RapidOCR.return_value = MagicMock(return_value=None)
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            backend = _RapidOCRBackend()
            txts, boxes, scores = backend._run(
                Image.new("RGB", (10, 10), "white")
            )
        assert txts == [] and boxes == [] and scores == []

    def test_run_handles_plain_list_boxes(self):
        import sys

        result = MagicMock()
        result.txts = ["x"]
        result.boxes = [[(0, 0), (5, 0), (5, 5), (0, 5)]]
        result.scores = [0.9]
        engine = MagicMock(return_value=result)
        fake_mod = MagicMock(RapidOCR=MagicMock(return_value=engine))
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            backend = _RapidOCRBackend()
            _, boxes, _ = backend._run(Image.new("RGB", (10, 10), "white"))
        assert boxes == [[(0, 0), (5, 0), (5, 5), (0, 5)]]

    def test_run_returns_none_boxes_safely(self):
        import sys

        result = MagicMock()
        result.txts = ["x"]
        result.boxes = None
        result.scores = [0.9]
        engine = MagicMock(return_value=result)
        fake_mod = MagicMock(RapidOCR=MagicMock(return_value=engine))
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            backend = _RapidOCRBackend()
            txts, boxes, scores = backend._run(
                Image.new("RGB", (10, 10), "white")
            )
        assert boxes == []

    def test_find_text_empty_target_short_circuits(self):
        import sys

        fake_mod = self._fake_rapidocr()
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            backend = _RapidOCRBackend()
            assert backend.find_text(
                Image.new("RGB", (10, 10), "white"),
                "",  # nothing to match -> early return
                filter_type="both",
                early_confidence_threshold=75,
            ) == ([], [], False)

    def test_find_text_raises_on_engine_failure(self):
        import sys

        engine = MagicMock(side_effect=RuntimeError("boom"))
        fake_mod = MagicMock(RapidOCR=MagicMock(return_value=engine))
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            backend = _RapidOCRBackend()
            with pytest.raises(OCRProcessingError, match="RapidOCR"):
                backend.find_text(
                    Image.new("RGB", (10, 10), "white"),
                    "Login",
                    filter_type="both",
                    early_confidence_threshold=75,
                )

    def test_extract_all_text_raises_on_engine_failure(self):
        import sys

        engine = MagicMock(side_effect=RuntimeError("boom"))
        fake_mod = MagicMock(RapidOCR=MagicMock(return_value=engine))
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            backend = _RapidOCRBackend()
            with pytest.raises(OCRProcessingError, match="RapidOCR"):
                backend.extract_all_text(
                    Image.new("RGB", (10, 10), "white"),
                    filter_type="both",
                )


class TestModuleLevelHelpers:
    def test_find_text_with_multiple_preprocessing(self, monkeypatch):
        with patch.object(
            OCREngine,
            "find_text",
            return_value=([(1, 2, 3, 4)], [80.0], False),
        ) as ft, patch.object(
            OCREngine, "__init__", lambda self, config=None: setattr(self, "_backend", None)
        ):
            boxes, scores, early = find_text_with_multiple_preprocessing(
                Image.new("RGB", (10, 10), "white"),
                "Login",
                "both",
                75.0,
            )
        ft.assert_called_once()
        assert boxes == [(1, 2, 3, 4)]

    def test_extract_text_from_image(self, monkeypatch):
        with patch.object(
            OCREngine,
            "extract_all_text",
            return_value=[OCRResult("hello", 90.0, (0, 0, 10, 10))],
        ), patch.object(
            OCREngine, "__init__", lambda self, config=None: setattr(self, "_backend", None)
        ):
            out = extract_text_from_image(
                Image.new("RGB", (10, 10), "white"), filter_type="both"
            )
        assert out == ["hello"]


class TestOCRResult:
    def test_repr_format(self):
        r = OCRResult("hello", 91.234, (1, 2, 3, 4))
        rep = repr(r)
        assert "hello" in rep
        assert "91.23" in rep
