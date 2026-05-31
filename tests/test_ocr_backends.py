"""Tests for the pluggable OCR backend dispatch (Phase 3 / E5).

``OCREngine`` is now a thin facade that picks a backend based on
``config['ocr_backend']``:

  * ``'tesseract'`` (default) → existing Tesseract pipeline.
  * ``'rapidocr'``           → RapidOCR via ONNX Runtime, lazy-imported.

The contract (``find_text`` / ``extract_all_text`` signatures and return
shapes) is unchanged so callers don't notice.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from visus.desktop.core.ocr_engine import OCREngine, OCRResult
from visus.desktop.exceptions import ConfigurationError


class TestBackendDispatch:
    """``OCREngine`` picks the right backend based on config."""

    def test_default_backend_is_rapidocr(self):
        from visus.desktop.utils import config as _config

        defaults = _config.BotVisionConfig._load_default_config(
            _config.BotVisionConfig.__new__(_config.BotVisionConfig)
        )
        assert defaults["ocr_backend"] == "rapidocr"

    def test_explicit_tesseract_backend_uses_tesseract_backend(self):
        from visus.desktop.core.ocr_engine import _TesseractBackend

        with patch.object(_TesseractBackend, "_setup", lambda self: None):
            engine = OCREngine(_make_config({"ocr_backend": "tesseract"}))
        assert isinstance(engine._backend, _TesseractBackend)

    def test_rapidocr_backend_selects_rapid_backend(self):
        from visus.desktop.core.ocr_engine import _RapidOCRBackend

        # The RapidOCR import is lazy; stub it so the test does not require
        # the optional dependency to be installed.
        fake_engine = MagicMock()
        fake_rapidocr_mod = MagicMock(RapidOCR=MagicMock(return_value=fake_engine))
        with patch.dict(sys.modules, {"rapidocr": fake_rapidocr_mod}):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
        assert isinstance(engine._backend, _RapidOCRBackend)

    def test_unknown_backend_raises_configuration_error(self):
        with pytest.raises(ConfigurationError, match="ocr_backend"):
            OCREngine(_make_config({"ocr_backend": "magic"}))

    def test_missing_rapidocr_dependency_falls_back_to_tesseract(self):
        # rapidocr is the default but an optional extra. If it isn't installed,
        # the engine must fall back to Tesseract (with a warning) rather than
        # raise, so a core install still does OCR.
        from visus.desktop.core.ocr_engine import _TesseractBackend

        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "rapidocr":
                raise ImportError("No module named 'rapidocr'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import), patch.object(
            _TesseractBackend, "_setup", lambda self: None
        ):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
        assert isinstance(engine._backend, _TesseractBackend)
        assert engine.config.get("ocr_backend") == "tesseract"


class TestTesseractBackendPreserved:
    """The Tesseract path is unchanged behind the facade."""

    def test_find_text_signature_preserved(self):
        from visus.desktop.core.ocr_engine import _TesseractBackend

        with patch.object(_TesseractBackend, "_setup", lambda self: None):
            engine = OCREngine(_make_config({"ocr_backend": "tesseract"}))
        assert hasattr(engine, "find_text")
        assert hasattr(engine, "extract_all_text")

    def test_existing_ocr_configs_still_present(self):
        from visus.desktop.core.ocr_engine import _TesseractBackend

        with patch.object(_TesseractBackend, "_setup", lambda self: None):
            engine = OCREngine(_make_config({"ocr_backend": "tesseract"}))
        # Sanity: a Tesseract backend still owns the PSM config list.
        assert engine._backend.ocr_configs
        assert any("psm" in cfg for cfg in engine._backend.ocr_configs)


class TestRapidOCRBackendShape:
    """``_RapidOCRBackend`` returns the same shape Tesseract does."""

    def _fake_rapidocr(self, txts=("Login",), boxes=(((10, 20), (60, 20), (60, 40), (10, 40)),), scores=(0.95,)):
        result = MagicMock()
        result.txts = txts
        result.boxes = np.array(boxes)
        result.scores = scores
        engine = MagicMock(return_value=result)
        fake_mod = MagicMock(RapidOCR=MagicMock(return_value=engine))
        return fake_mod

    def test_find_text_returns_three_tuple(self):
        fake_mod = self._fake_rapidocr()
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
            boxes, scores, early = engine.find_text(
                Image.new("RGB", (200, 100), color="white"),
                "Login",
                filter_type="both",
                early_confidence_threshold=75.0,
            )
        assert isinstance(boxes, list)
        assert isinstance(scores, list)
        assert isinstance(early, bool)
        assert len(boxes) == len(scores)

    def test_find_text_matches_target_text(self):
        fake_mod = self._fake_rapidocr(
            txts=("Login", "Submit"),
            boxes=(
                ((10, 20), (60, 20), (60, 40), (10, 40)),
                ((100, 20), (160, 20), (160, 40), (100, 40)),
            ),
            scores=(0.7, 0.95),
        )
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
            boxes, scores, early = engine.find_text(
                Image.new("RGB", (200, 100)),
                "Submit",
                filter_type="both",
                early_confidence_threshold=50.0,
            )
        # Submit is present with score 0.95 -> 95 scaled, well above 50.
        assert early is True
        assert len(boxes) == 1
        # The box returned is Submit's, not Login's.
        assert boxes[0][0] == 100

    def test_find_text_no_match_returns_empty(self):
        fake_mod = self._fake_rapidocr(txts=("Cancel",))
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
            boxes, scores, early = engine.find_text(
                Image.new("RGB", (200, 100)),
                "Login",
                filter_type="both",
                early_confidence_threshold=75.0,
            )
        assert boxes == []
        assert scores == []
        assert early is False

    def test_extract_all_text_returns_ocrresult_list(self):
        fake_mod = self._fake_rapidocr(
            txts=("Hello", "World"),
            boxes=(
                ((0, 0), (50, 0), (50, 20), (0, 20)),
                ((60, 0), (110, 0), (110, 20), (60, 20)),
            ),
            scores=(0.9, 0.8),
        )
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
            results = engine.extract_all_text(Image.new("RGB", (200, 100)))
        assert len(results) == 2
        assert all(isinstance(r, OCRResult) for r in results)
        assert {r.text for r in results} == {"Hello", "World"}

    def test_rapidocr_scores_are_scaled_to_zero_hundred(self):
        """PP-OCR scores come in 0-1; Tesseract historic range is 0-100."""
        fake_mod = self._fake_rapidocr(scores=(0.8,))
        with patch.dict(sys.modules, {"rapidocr": fake_mod}):
            engine = OCREngine(_make_config({"ocr_backend": "rapidocr"}))
            _, scores, _ = engine.find_text(
                Image.new("RGB", (200, 100)),
                "Login",
                filter_type="both",
                early_confidence_threshold=50.0,
            )
        assert scores == [80.0]


def _make_config(overrides):
    """Build a BotVisionConfig that skips Tesseract auto-detection."""
    from visus.desktop.utils import config as _config

    cfg = _config.BotVisionConfig.__new__(_config.BotVisionConfig)
    cfg.config = _config.BotVisionConfig._load_default_config(cfg)
    cfg.config.update(overrides)
    return cfg
