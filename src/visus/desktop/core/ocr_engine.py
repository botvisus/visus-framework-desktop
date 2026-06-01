"""
Visus Desktop - OCR Engine

Pluggable OCR engine (Phase 3 / E5). ``OCREngine`` is a thin facade that
selects a backend at construction time based on
``config['ocr_backend']``:

  * ``'tesseract'`` (default) -- multi-PSM pipeline over 19 preprocessing
    variants. Best for Portuguese, character whitelisting, RPA UI text.
  * ``'rapidocr'``           -- PP-OCR models via ONNX Runtime. No
    external binary; install with ``pip install
    'visus-desktop[rapidocr]'``.

Both backends honour the same contract (``find_text`` /
``extract_all_text``) so callers don't need to care which one is active.
"""

import logging
from typing import Dict, List, Optional, Tuple

from PIL import Image

from ..exceptions import ConfigurationError, OCRProcessingError, TesseractNotFoundError
from ..utils.config import BotVisionConfig
from ..utils.text_filters import limpar_texto, matches_filter
from .image_processing import ImageProcessor

logger = logging.getLogger(__name__)


def _iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    """Intersection-over-union of two ``(x, y, w, h)`` boxes."""
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    inter_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    inter_h = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


# Relative glyph widths for proportional fonts. A flat "every char is 1/N of
# the line" model drifts badly on text full of narrow glyphs (URLs: '/', '.',
# 'i', 'l'); weighting each character by its typical advance width keeps the
# interpolated slice aligned much further into the string.
_GLYPH_WIDE = set("mwMW@%—")
_GLYPH_NARROW = set("iIl|.,:;'`!ij ")
_GLYPH_SEMI_NARROW = set("ftr()[]{}/\\-")


def _glyph_width(c: str) -> float:
    if c in _GLYPH_WIDE:
        return 1.0
    if c in _GLYPH_NARROW:
        return 0.34
    if c in _GLYPH_SEMI_NARROW:
        return 0.5
    if c.isupper() or c.isdigit():
        return 0.72
    return 0.58


def _narrow_box_to_word(
    raw_text: str, target: str, box: Tuple[int, int, int, int]
) -> Tuple[int, int, int, int]:
    """Approximate the sub-box of ``target`` inside a line ``box``.

    OCR line detections span the whole text run, so a substring match (e.g.
    "visus" inside a long URL) returns the entire line's box. When the caller
    wants just the searched word, interpolate its horizontal slice from the
    character offset, weighting each glyph by its typical width so proportional
    fonts stay aligned. The vertical extent (``y``, ``h``) is kept. Falls back
    to the full ``box`` when the target is not found verbatim in ``raw_text``
    (e.g. OCR cleaning shifted it). Still an estimate -- exact per-word boxes
    need a word-level OCR pass (Tesseract ``image_to_data``).
    """
    if not raw_text:
        return box
    i = raw_text.lower().find(target.lower())
    if i < 0:
        return box
    x, y, w, h = box
    widths = [_glyph_width(c) for c in raw_text]
    total = sum(widths) or 1.0
    pre = sum(widths[:i])
    word = sum(widths[i:i + len(target)])
    word_x = int(round(x + w * pre / total))
    word_w = max(1, int(round(w * word / total)))
    word_w = min(word_w, x + w - word_x)  # clamp inside the original box
    return (word_x, y, word_w, h)


def _dedupe_in_reading_order(
    candidates: List[Tuple[float, Tuple[int, int, int, int]]],
    iou_threshold: float = 0.4,
) -> List[Tuple[float, Tuple[int, int, int, int]]]:
    """Collapse overlapping ``(confidence, box)`` candidates.

    Keeps the highest-confidence representative for each spatial cluster
    (IoU > ``iou_threshold`` counts as the same occurrence), then sorts
    survivors top-to-bottom, left-to-right so the caller can number them
    in natural reading order.
    """
    by_conf = sorted(candidates, key=lambda c: c[0], reverse=True)
    kept: List[Tuple[float, Tuple[int, int, int, int]]] = []
    for conf, box in by_conf:
        if any(_iou(box, k_box) > iou_threshold for _, k_box in kept):
            continue
        kept.append((conf, box))
    return sorted(kept, key=lambda c: (c[1][1], c[1][0]))


class OCRResult:
    """
    Class to store OCR results.
    """

    def __init__(
        self,
        text: str,
        confidence: float,
        box: Tuple[int, int, int, int],
        method_index: int = 0,
        config_index: int = 0,
    ):
        self.text = text
        self.confidence = confidence
        self.box = box  # (x, y, width, height)
        self.method_index = method_index
        self.config_index = config_index

    def __repr__(self):
        return f"OCRResult(text='{self.text}', confidence={self.confidence:.2f})"


class OCREngine:
    """Facade selecting the active OCR backend based on config.

    The class keeps the historical ``OCREngine(config)`` constructor so
    existing call sites do not change. The actual work is delegated to a
    backend instance stored on ``self._backend``; both Tesseract and
    RapidOCR backends implement the same two methods (``find_text``,
    ``extract_all_text``) and the facade just forwards.
    """

    def __init__(self, config: Optional[BotVisionConfig] = None):
        self.config = config or BotVisionConfig()
        backend_name = self.config.get("ocr_backend", "rapidocr")
        if backend_name == "tesseract":
            self._backend = _TesseractBackend(self.config)
        elif backend_name == "rapidocr":
            try:
                self._backend = _RapidOCRBackend(self.config)
            except ConfigurationError as exc:
                # rapidocr is the preferred default but an OPTIONAL extra.
                # If it isn't installed, fall back to Tesseract so a core
                # install still does OCR. (Install with
                # ``pip install 'visus-desktop[rapidocr]'`` to use it.)
                logger.warning(
                    "ocr_backend='rapidocr' unavailable (%s); "
                    "falling back to 'tesseract'.",
                    exc,
                )
                self.config.config["ocr_backend"] = "tesseract"
                if hasattr(self.config, "_detect_tesseract"):
                    try:
                        self.config._detect_tesseract()
                    except Exception:  # pragma: no cover - best effort
                        pass
                self._backend = _TesseractBackend(self.config)
        else:
            raise ConfigurationError(
                f"Unknown ocr_backend {backend_name!r}; "
                "expected 'tesseract' or 'rapidocr'."
            )
        # Expose a few attributes the legacy tests/users inspect directly
        # so the facade stays a drop-in replacement for the old class.
        self.image_processor = getattr(self._backend, "image_processor", None)

    # ------------------------------------------------------------------
    # Public OCR contract -- both backends implement these.
    # ------------------------------------------------------------------

    def find_text(self, *args, **kwargs):
        return self._backend.find_text(*args, **kwargs)

    def find_all_text(self, *args, **kwargs):
        """Return every distinct occurrence of ``target_text``.

        Unlike :meth:`find_text` (which short-circuits on the first
        high-confidence detection), this enumerates ALL matches across
        every preprocessing pass and dedupes overlapping boxes (keeping
        the best confidence per spatial region). Results are sorted in
        reading order (top-to-bottom, left-to-right).
        """
        return self._backend.find_all_text(*args, **kwargs)

    def extract_all_text(self, *args, **kwargs):
        return self._backend.extract_all_text(*args, **kwargs)

    def __getattr__(self, item):
        """Proxy legacy attribute reads (``ocr_configs``, ``config_names``, …)
        through to the active backend so existing callers keep working."""
        # ``__getattr__`` only fires for names not already on the instance,
        # so this is purely a compat shim for backend-specific attributes.
        backend = self.__dict__.get("_backend")
        if backend is None or item.startswith("_"):
            raise AttributeError(item)
        return getattr(backend, item)


class _TesseractBackend:
    """Tesseract-backed OCR pipeline (the historical implementation)."""

    def __init__(self, config: Optional[BotVisionConfig] = None):
        """
        Initializes the OCR engine.

        Args:
            config (BotVisionConfig, optional): Library configuration
        """
        self.config = config or BotVisionConfig()
        self.image_processor = ImageProcessor()

        # Optimized OCR configurations
        self.ocr_configs = [
            r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789",  # Numbers, single line
            r"--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789",  # Numbers, single word
            r"--oem 3 --psm 6",  # Common page layout
            r"--oem 3 --psm 11",  # Sparse text
            r"--oem 3 --psm 7",  # Single line
            r"--oem 3 --psm 8",  # Single word
            r"--oem 3 --psm 13",  # Raw line. Treat the image as a single text line
        ]

        # Descriptive names of the processing methods
        self.method_names = [
            "HSV Enhancement (increased saturation) - PRIORITY",  # Method 1 - 62% effectiveness
            "HSV Enhancement + specific threshold",  # Method 2 - variation of 1
            "Light text / dark background inversion",  # Method 3 - 59% effectiveness
            "Inversion with threshold 140",  # Method 4 - variation of 3
            "Inversion with threshold 160",  # Method 5 - variation of 3
            "Inversion with threshold 180",  # Method 6 - variation of 3
            "RGB channel processing (R-B difference)",  # Method 7 - 57% effectiveness
            "High contrast + sharpness",  # Method 8 - 41% effectiveness
            "Extra sharpness (double application)",  # Method 9 - variation of 8
            "Full image inversion",  # Method 10
            "Gaussian adaptive threshold",  # Method 11
            "Mean adaptive threshold",  # Method 12
            "HSV mask for pink/purple backgrounds",  # Method 13
            "HSV mask for light gray backgrounds",  # Method 14
            "HSV mask for dark gray/black backgrounds",  # Method 15
            "Lab color space + CLAHE",  # Method 16
            "Lab color space + CLAHE inverted",  # Method 17
            "Maximum contrast + double sharpness",  # Method 18
            "Optimized Lab + HSV combination",  # Method 19
        ]

        # Names of the OCR configurations
        self.config_names = [
            "numbers_line_psm7",  # Configuration 0
            "numbers_word_psm8",  # Configuration 1
            "page_layout_psm6",  # Configuration 2
            "sparse_text_psm11",  # Configuration 3
            "single_line_psm7",  # Configuration 4
            "single_word_psm8",  # Configuration 5
            "raw_line_psm13",  # Configuration 6
        ]

        # Confidence bonuses per configuration and filter type
        self.confidence_bonuses = {
            "numbers": {
                0: 8,
                1: 5,
                2: 2,
                3: 1,
            },  # PSM 7 and 8 with whitelist for numbers
            "letters": {2: 3, 3: 2, 4: 4, 5: 3},  # PSM 6 and 11 for letters
            "both": {2: 2, 3: 1, 4: 2, 5: 1},  # General configurations
        }

        self._setup()

    def _get_method_name(self, index: int) -> str:
        """
        Returns the descriptive name of the processing method.

        Args:
            index (int): Method index

        Returns:
            str: Descriptive name of the method
        """
        if index < len(self.method_names):
            return self.method_names[index]
        else:
            return f"Custom method #{index + 1}"

    def _get_config_name(self, index: int) -> str:
        """
        Returns the descriptive name of the OCR configuration.

        Args:
            index (int): Configuration index

        Returns:
            str: Descriptive name of the configuration
        """
        if index < len(self.config_names):
            return self.config_names[index]
        else:
            return f"Custom config #{index + 1}"

    def _setup(self) -> None:
        """Configures Tesseract with the current settings."""
        try:
            self.config.setup_tesseract()
        except Exception as e:
            logger.error(f"Error configuring Tesseract: {e}")
            raise TesseractNotFoundError("Could not configure Tesseract OCR") from e

    def find_text(
        self,
        region_img: Image.Image,
        target_text: str,
        filter_type: str = "both",
        early_confidence_threshold: float = 75.0,
    ) -> Tuple[List[Tuple], List[float], bool]:
        """
        Finds text using multiple preprocessed versions of the image.

        Args:
            region_img (PIL.Image): Image of the region to search in
            target_text (str): Text to be found
            filter_type (str): Filter type ("numbers", "letters", "both")
            early_confidence_threshold (float): Threshold for early return

        Returns:
            tuple: (found_boxes, confidence_scores, found_early)

        Raises:
            OCRProcessingError: If there is an error during OCR processing
        """
        try:
            # Preprocess the image
            processed_images = self.image_processor.preprocess_for_ocr(region_img)

            all_found_boxes = []
            all_confidence_scores = []
            best_result = None
            best_img_index = 0
            best_config_index = 0
            best_confidence = 0.0

            logger.info(
                f"Searching for text '{target_text}' with threshold of {early_confidence_threshold}%"
            )

            # Bonus for priority methods (the first methods are optimized)
            high_confidence_bonus = 8.0

            # Process each preprocessed image
            for img_index, img in enumerate(processed_images):
                for config_index, config in enumerate(self.ocr_configs):
                    results = self._process_single_image(
                        img,
                        target_text,
                        filter_type,
                        config_index,
                        config,
                        img_index,
                        len(processed_images),
                        high_confidence_bonus,
                    )

                    for result in results:
                        # Check whether it was found with high confidence
                        if result.confidence >= early_confidence_threshold:
                            method_name = self._get_method_name(img_index)
                            config_name = self._get_config_name(config_index)
                            logger.info(
                                f">>> High-confidence detection ({result.confidence:.2f}%) found!"
                            )
                            logger.info(
                                f"🎯 CHOSEN METHOD: {method_name} (#{img_index + 1}/{len(processed_images)})"
                            )
                            logger.info(
                                f"⚙️  CONFIGURATION: {config_name} (#{config_index + 1}/{len(self.ocr_configs)})"
                            )
                            logger.info(
                                f"📊 Detected text: '{result.text}' at position {result.box}"
                            )
                            return [result.box], [result.confidence], True

                        # Track the best result
                        if result.confidence > best_confidence:
                            best_result = result
                            best_img_index = img_index
                            best_config_index = config_index
                            best_confidence = result.confidence

                        # Add to the overall results
                        all_found_boxes.append(result.box)
                        all_confidence_scores.append(result.confidence)

            # If it got here, it did not find with high confidence, but may have found something
            if best_result and best_confidence > 0:
                best_method_name = self._get_method_name(best_img_index)
                best_config_name = self._get_config_name(best_config_index)
                logger.info(
                    f"🎯 BEST RESULT: {best_method_name} (#{best_img_index + 1}/{len(processed_images)})"
                )
                logger.info(
                    f"⚙️  CONFIGURATION: {best_config_name} (#{best_config_index + 1}/{len(self.ocr_configs)})"
                )
                logger.info(
                    f"📊 Confidence: {best_confidence:.2f}% - Text: '{best_result.text}'"
                )

            return all_found_boxes, all_confidence_scores, False

        except Exception as e:
            logger.error(f"Error during OCR processing: {e}")
            raise OCRProcessingError(f"Text search failed: {e}") from e

    def find_all_text(
        self,
        region_img: Image.Image,
        target_text: str,
        filter_type: str = "both",
        min_confidence: float = 0.0,
        word_box: bool = False,
    ) -> List[Tuple[float, Tuple[int, int, int, int]]]:
        """Return every distinct ``target_text`` match in ``region_img``.

        Iterates every preprocessing / config combination without the
        early-exit optimisation that :meth:`find_text` uses, so multiple
        on-screen instances of the same string can all be reported. The
        result is a deduplicated list of ``(confidence, (x, y, w, h))``
        in reading order (top-to-bottom, left-to-right).

        ``word_box`` is accepted for API parity with the RapidOCR backend;
        Tesseract matches whole word tokens, so its boxes are already
        word-level and the flag has no additional effect here.
        """
        try:
            processed_images = self.image_processor.preprocess_for_ocr(region_img)
            candidates: List[Tuple[float, Tuple[int, int, int, int]]] = []
            high_confidence_bonus = 8.0
            for img_index, img in enumerate(processed_images):
                for config_index, config in enumerate(self.ocr_configs):
                    results = self._process_single_image(
                        img,
                        target_text,
                        filter_type,
                        config_index,
                        config,
                        img_index,
                        len(processed_images),
                        high_confidence_bonus,
                    )
                    for result in results:
                        if result.confidence >= min_confidence:
                            candidates.append((result.confidence, result.box))
            return _dedupe_in_reading_order(candidates)
        except Exception as exc:
            logger.error(f"find_all_text failed: {exc}")
            raise OCRProcessingError(f"find_all_text failed: {exc}") from exc

    def _process_single_image(
        self,
        img: Image.Image,
        target_text: str,
        filter_type: str,
        config_index: int,
        config: str,
        img_index: int,
        total_images: int,
        high_confidence_bonus: float,
    ) -> List[OCRResult]:
        """
        Processes a single image with a specific OCR configuration.

        Args:
            img (PIL.Image): Image to be processed
            target_text (str): Target text
            filter_type (str): Filter type
            config_index (int): Configuration index
            config (str): Tesseract configuration string
            img_index (int): Index of the processed image
            total_images (int): Total number of images
            high_confidence_bonus (float): Confidence bonus

        Returns:
            list: List of OCRResult found
        """
        try:
            import pytesseract

            # Run OCR
            data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT, config=config
            )

            # Filter recognized words
            recognized_words = [
                limpar_texto(w, filter_type) for w in data["text"] if w.strip()
            ]
            recognized_words = [
                w for w in recognized_words if matches_filter(w, filter_type)
            ]

            # Debug log
            if filter_type == "numbers" and recognized_words:
                logger.debug(
                    f"OCR Numbers (method {img_index + 1}/{total_images}): {recognized_words}"
                )
            elif filter_type == "both":
                numeric_words = [w for w in recognized_words if w.isdigit()]
                if numeric_words:
                    logger.debug(
                        f"OCR Numbers (method {img_index + 1}/{total_images}): {numeric_words}"
                    )

            # Process the target text
            target_words = [
                limpar_texto(word, filter_type) for word in target_text.split()
            ]
            target_words = [w for w in target_words if matches_filter(w, filter_type)]
            n_words = len(target_words)

            results = []

            # Search for word combinations
            for idx in range(len(data["text"]) - n_words + 1):
                candidate = [
                    limpar_texto(data["text"][j], filter_type)
                    for j in range(idx, idx + n_words)
                ]

                if not all(candidate) or not all(
                    matches_filter(word, filter_type) for word in candidate
                ):
                    continue

                # Check for a match
                if all(
                    candidate[k].lower() == target_words[k].lower()
                    for k in range(n_words)
                ):
                    result = self._create_ocr_result(
                        data,
                        idx,
                        n_words,
                        candidate,
                        config_index,
                        filter_type,
                        img_index,
                        high_confidence_bonus,
                    )

                    if result:
                        results.append(result)
                        logger.debug(
                            f"Found '{' '.join(candidate)}' with confidence: {result.confidence:.2f}%"
                        )

            return results

        except ImportError as e:
            raise OCRProcessingError("pytesseract is not installed") from e
        except Exception as e:
            logger.debug(f"Error in OCR with configuration {config}: {e}")
            return []

    def _create_ocr_result(
        self,
        data: Dict,
        idx: int,
        n_words: int,
        candidate: List[str],
        config_index: int,
        filter_type: str,
        img_index: int,
        high_confidence_bonus: float,
    ) -> Optional[OCRResult]:
        """
        Creates an OCRResult from the Tesseract data.

        Args:
            data (dict): Data returned by Tesseract
            idx (int): Starting index of the word
            n_words (int): Number of words
            candidate (list): Candidate words
            config_index (int): Configuration index
            filter_type (str): Filter type
            img_index (int): Image index
            high_confidence_bonus (float): Confidence bonus

        Returns:
            OCRResult or None: OCR result or None if invalid
        """
        try:
            # Compute average confidence
            confidence_values = [
                float(data["conf"][j])
                for j in range(idx, idx + n_words)
                if float(data["conf"][j]) > 0
            ]

            if confidence_values:
                avg_confidence = sum(confidence_values) / len(confidence_values)
            else:
                avg_confidence = 0

            # Compute bounding box
            lefts = [data["left"][j] for j in range(idx, idx + n_words)]
            tops = [data["top"][j] for j in range(idx, idx + n_words)]
            rights = [
                data["left"][j] + data["width"][j] for j in range(idx, idx + n_words)
            ]
            bottoms = [
                data["top"][j] + data["height"][j] for j in range(idx, idx + n_words)
            ]

            box = (
                min(lefts),
                min(tops),
                max(rights) - min(lefts),
                max(bottoms) - min(tops),
            )

            # Compute confidence bonus
            config_bonus = self.confidence_bonuses.get(filter_type, {}).get(
                config_index, 0
            )

            # Bonus for high-priority methods
            method_bonus = 0
            if img_index < 10:
                method_bonus = high_confidence_bonus * (1.0 - (img_index / 10.0))

            final_confidence = avg_confidence + config_bonus + method_bonus

            return OCRResult(
                text=" ".join(candidate),
                confidence=final_confidence,
                box=box,
                method_index=img_index,
                config_index=config_index,
            )

        except Exception as e:
            logger.debug(f"Error creating OCRResult: {e}")
            return None

    def extract_all_text(
        self, img: Image.Image, filter_type: str = "both"
    ) -> List[OCRResult]:
        """
        Extracts all the text found in the image.

        Args:
            img (PIL.Image): Image to be processed
            filter_type (str): Filter type

        Returns:
            list: List of OCRResult with all the text found
        """
        try:
            import pytesseract

            # Use default configuration for full extraction
            config = r"--oem 3 --psm 6"
            data = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT, config=config
            )

            results = []

            for i, text in enumerate(data["text"]):
                if text.strip():
                    cleaned_text = limpar_texto(text, filter_type)
                    if cleaned_text and matches_filter(cleaned_text, filter_type):
                        confidence = float(data["conf"][i])
                        box = (
                            data["left"][i],
                            data["top"][i],
                            data["width"][i],
                            data["height"][i],
                        )

                        results.append(
                            OCRResult(text=cleaned_text, confidence=confidence, box=box)
                        )

            return results

        except Exception as e:
            logger.error(f"Error during full text extraction: {e}")
            raise OCRProcessingError(f"Extraction failed: {e}") from e


class _RapidOCRBackend:
    """RapidOCR-backed OCR pipeline (PP-OCR via ONNX Runtime).

    Lazy-imports ``rapidocr`` so the package is only required when this
    backend is actually selected. Maps RapidOCR's output (lists of text /
    polygons / 0-1 scores) into the shape historically produced by
    Tesseract (axis-aligned ``(x, y, w, h)`` boxes and 0-100 scores).
    """

    def __init__(self, config: Optional[BotVisionConfig] = None):
        self.config = config or BotVisionConfig()
        try:
            import rapidocr  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ConfigurationError(
                "ocr_backend='rapidocr' requires the optional dependency. "
                "Install with: pip install 'visus-desktop[rapidocr]'"
            ) from exc
        self._engine = rapidocr.RapidOCR()

    def _run(self, image: Image.Image):
        """Invoke RapidOCR and return ``(txts, boxes, scores)`` triples."""
        import numpy as np

        arr = np.array(image)
        result = self._engine(arr)
        if result is None:
            return [], [], []
        txts = list(getattr(result, "txts", []) or [])
        boxes_raw = getattr(result, "boxes", None)
        scores = list(getattr(result, "scores", []) or [])
        if boxes_raw is None:
            return txts, [], scores
        # Accept either a numpy array of polygons or a plain list.
        try:
            boxes_iter = boxes_raw.tolist()  # type: ignore[union-attr]
        except AttributeError:
            boxes_iter = list(boxes_raw)
        return txts, boxes_iter, scores

    @staticmethod
    def _poly_to_xywh(polygon) -> Tuple[int, int, int, int]:
        """Convert a 4-vertex polygon to an axis-aligned (x, y, w, h)."""
        xs = [int(p[0]) for p in polygon]
        ys = [int(p[1]) for p in polygon]
        x, y = min(xs), min(ys)
        return (x, y, max(xs) - x, max(ys) - y)

    def _run_word_boxes(self, image: Image.Image):
        """Single OCR pass with per-word boxes; return ``(words, lines)``.

        Uses RapidOCR's native ``return_word_box=True`` so the recognizer
        emits a box per WORD (via its internal CTC alignment) instead of one
        box for the whole line -- this is what makes locating a word inside a
        long run (e.g. a URL) precise. ``words`` is
        ``[(text, score, (x, y, w, h)), ...]``; ``lines`` is the line-level
        ``[(text, polygon, score), ...]`` from the SAME pass (so the caller can
        fall back without a second OCR run).
        """
        import numpy as np

        result = self._engine(np.array(image), return_word_box=True)
        if result is None:
            return [], []

        txts = list(getattr(result, "txts", []) or [])
        boxes_raw = getattr(result, "boxes", None)
        scores = list(getattr(result, "scores", []) or [])
        if boxes_raw is None:
            lines = []
        else:
            try:
                boxes_iter = boxes_raw.tolist()  # type: ignore[union-attr]
            except AttributeError:
                boxes_iter = list(boxes_raw)
            lines = list(zip(txts, boxes_iter, scores))

        words: List[Tuple[str, float, Tuple[int, int, int, int]]] = []
        for entry in getattr(result, "word_results", None) or []:
            if not entry:
                continue
            # An entry is a tuple of (text, score, polygon) word-tuples; some
            # versions hand back a single word-tuple unwrapped.
            word_tuples = [entry] if isinstance(entry[0], str) else entry
            for word in word_tuples:
                try:
                    text, score, poly = word[0], word[1], word[2]
                except (IndexError, TypeError):
                    continue
                if not poly:
                    continue
                words.append((str(text), float(score), self._poly_to_xywh(poly)))
        return words, lines

    def find_text(
        self,
        region_img: Image.Image,
        target_text: str,
        filter_type: str = "both",
        early_confidence_threshold: float = 75.0,
    ) -> Tuple[List[Tuple], List[float], bool]:
        try:
            txts, boxes, scores = self._run(region_img)
        except Exception as exc:
            raise OCRProcessingError(f"RapidOCR call failed: {exc}") from exc

        target_clean = limpar_texto(target_text, filter_type).lower()
        if not target_clean:
            return [], [], False

        matched_boxes: List[Tuple] = []
        matched_scores: List[float] = []
        early_match = False
        for txt, polygon, raw_score in zip(txts, boxes, scores):
            candidate = limpar_texto(str(txt), filter_type)
            if not matches_filter(candidate, filter_type):
                continue
            if target_clean not in candidate.lower():
                continue
            box = self._poly_to_xywh(polygon)
            score_pct = float(raw_score) * 100.0
            matched_boxes.append(box)
            matched_scores.append(score_pct)
            if score_pct >= early_confidence_threshold:
                early_match = True
                return [box], [score_pct], True
        return matched_boxes, matched_scores, early_match

    def find_all_text(
        self,
        region_img: Image.Image,
        target_text: str,
        filter_type: str = "both",
        min_confidence: float = 0.0,
        word_box: bool = False,
    ) -> List[Tuple[float, Tuple[int, int, int, int]]]:
        """RapidOCR equivalent of :meth:`_TesseractBackend.find_all_text`.

        Lists every RapidOCR detection whose cleaned text contains
        ``target_text``, scored on RapidOCR's own 0--100 confidence,
        deduplicated by spatial overlap and sorted in reading order.

        When ``word_box`` is True, boxes are tightened from the whole text line
        to the matched word: RapidOCR's native per-word boxes
        (``return_word_box``) are used when available, falling back to a
        character-offset interpolation (:func:`_narrow_box_to_word`) otherwise.
        Useful to locate a word inside a long run such as a URL.
        """
        target_clean = limpar_texto(target_text, filter_type).lower()
        if not target_clean:
            return []

        # Gather line-level detections (and, for word_box, per-word boxes from
        # the same pass so there is no second OCR run in the common case).
        words: List[Tuple[str, float, Tuple[int, int, int, int]]] = []
        lines = None
        if word_box:
            try:
                words, lines = self._run_word_boxes(region_img)
            except Exception as exc:
                logger.debug("return_word_box pass failed (%s); using lines", exc)
        if lines is None:
            try:
                txts, polygons, scores = self._run(region_img)
            except Exception as exc:
                raise OCRProcessingError(f"RapidOCR call failed: {exc}") from exc
            lines = list(zip(txts, polygons, scores))

        # Precise path: match against native per-word boxes.
        if word_box and words:
            candidates: List[Tuple[float, Tuple[int, int, int, int]]] = []
            for raw_text, score, wbox in words:
                cleaned = limpar_texto(raw_text, filter_type)
                if not matches_filter(cleaned, filter_type):
                    continue
                if target_clean not in cleaned.lower():
                    continue
                score_pct = score * 100.0
                if score_pct < min_confidence:
                    continue
                # Exact when the word IS the target; otherwise the target is a
                # substring of a bigger token (e.g. "visus" in "visus-desktop")
                # -- interpolate inside that small token box, not the line.
                box = (
                    wbox
                    if len(raw_text) <= len(target_text)
                    else _narrow_box_to_word(raw_text, target_text, wbox)
                )
                candidates.append((score_pct, box))
            if candidates:
                return _dedupe_in_reading_order(candidates)

        # Fallback: line-level match (with interpolation when word_box).
        candidates = []
        for txt, polygon, raw_score in lines:
            candidate = limpar_texto(str(txt), filter_type)
            if not matches_filter(candidate, filter_type):
                continue
            if target_clean not in candidate.lower():
                continue
            score_pct = float(raw_score) * 100.0
            if score_pct < min_confidence:
                continue
            box = self._poly_to_xywh(polygon)
            if word_box:
                box = _narrow_box_to_word(str(txt), target_text, box)
            candidates.append((score_pct, box))
        return _dedupe_in_reading_order(candidates)

    def extract_all_text(
        self, img: Image.Image, filter_type: str = "both"
    ) -> List[OCRResult]:
        try:
            txts, boxes, scores = self._run(img)
        except Exception as exc:
            raise OCRProcessingError(f"RapidOCR call failed: {exc}") from exc

        results: List[OCRResult] = []
        for txt, polygon, raw_score in zip(txts, boxes, scores):
            cleaned = limpar_texto(str(txt), filter_type)
            if not cleaned or not matches_filter(cleaned, filter_type):
                continue
            results.append(
                OCRResult(
                    text=cleaned,
                    confidence=float(raw_score) * 100.0,
                    box=self._poly_to_xywh(polygon),
                )
            )
        return results


# Convenience functions
def find_text_with_multiple_preprocessing(
    region_img: Image.Image,
    target_text: str,
    filter_type: str = "both",
    early_confidence_threshold: float = 75.0,
) -> Tuple[List[Tuple], List[float], bool]:
    """
    Convenience function to find text with multiple preprocessing.

    Args:
        region_img (PIL.Image): Image of the region
        target_text (str): Text to search for
        filter_type (str): Filter type
        early_confidence_threshold (float): Confidence threshold

    Returns:
        tuple: (boxes, confidences, early_match)
    """
    engine = OCREngine()
    return engine.find_text(
        region_img, target_text, filter_type, early_confidence_threshold
    )


def extract_text_from_image(img: Image.Image, filter_type: str = "both") -> List[str]:
    """
    Convenience function to extract text from an image.

    Args:
        img (PIL.Image): Image to be processed
        filter_type (str): Filter type

    Returns:
        list: List of texts found
    """
    engine = OCREngine()
    results = engine.extract_all_text(img, filter_type)
    return [result.text for result in results]
