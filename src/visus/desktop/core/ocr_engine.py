"""
Visus Desktop - OCR Engine

This module manages optical character recognition (OCR) using Tesseract
with multiple configurations and techniques optimized for different types of text.
"""

import logging
from typing import Dict, List, Optional, Tuple

from PIL import Image

from ..exceptions import OCRProcessingError, TesseractNotFoundError
from ..utils.config import BotVisionConfig
from ..utils.text_filters import limpar_texto, matches_filter
from .image_processing import ImageProcessor

logger = logging.getLogger(__name__)


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
    """
    OCR engine with multiple configurations and optimized processing.

    Uses different Tesseract configurations and preprocessing techniques
    to maximize accuracy in text detection.
    """

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

        self._setup_tesseract()

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

    def _setup_tesseract(self) -> None:
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
