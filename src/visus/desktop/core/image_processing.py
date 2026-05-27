"""
Visus Desktop - Image Processing

This module contains all the image preprocessing techniques
optimized to improve OCR accuracy.
"""

import logging
from typing import List, Union

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Class responsible for image processing for OCR.

    Implements multiple preprocessing techniques optimized
    based on performance tests for different types of text and backgrounds.
    """

    def __init__(self, methods: Union[str, List[str]] = "all"):
        """
        Initializes the image processor.

        Args:
            methods (str or list): Methods to be applied.
                                 "all" for all of them, or a specific list
        """
        self.methods = methods
        self.available_methods = [
            "hsv_enhancement",  # Method 28 - 62% confidence
            "threshold_variants",  # Threshold variations
            "dark_background",  # Method 2 - 59% confidence
            "channel_processing",  # Method 22 - 57% confidence
            "contrast_sharpening",  # Methods 13 and 27 - 41% confidence
            "adaptive_threshold",  # Adaptive threshold
            "color_masking",  # HSV color masks
            "lab_enhancement",  # LAB processing
            "combinations",  # Optimized combinations
        ]

    def preprocess_for_ocr(self, img: Image.Image) -> List[Image.Image]:
        """
        Applies optimized preprocessing techniques based on execution results.
        Focuses on the methods that best detected numbers and removes ineffective methods.

        This function is an EXACT copy of the preprocess_image_for_ocr function from the original bot_vision.py.
        """
        # List to store all processed versions
        processed_images = []

        # Convert to numpy array for manipulation
        img_np = np.array(img)

        logger.debug(
            f"🔬 Starting image processing {img.size} with 19 optimized techniques"
        )

        # METHOD 1 (62% confidence) - Highest priority
        # -----------------------------------------------------------------------------------
        # Version with best detection of numbers in colored boxes
        # HSV processing with specific adjustments
        img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

        # Increase saturation to highlight colors
        img_hsv[:, :, 1] = np.clip(img_hsv[:, :, 1] * 1.4, 0, 255).astype(np.uint8)
        img_enhanced = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        processed_images.append(Image.fromarray(img_enhanced))
        logger.debug(
            "✓ Method 1/19: HSV Enhancement (increased saturation) - PRIORITY (62% effectiveness)"
        )

        # Version with specific threshold - variation of method 28
        img_gray = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(img_gray, 150, 255, cv2.THRESH_BINARY)
        processed_images.append(Image.fromarray(thresh))
        logger.debug("✓ Method 2/19: HSV Enhancement + specific threshold")

        # METHOD 3 (59% confidence) - Second priority
        # -----------------------------------------------------------------------------------
        # Inversion for light text on dark background
        _, dark_bg_thresh = cv2.threshold(
            np.array(img.convert("L")), 160, 255, cv2.THRESH_BINARY_INV
        )
        processed_images.append(Image.fromarray(dark_bg_thresh))
        logger.debug(
            "✓ Method 3/19: Light text / dark background inversion (59% effectiveness)"
        )

        # Variation of method 2 with different thresholds
        dark_thresholds = [140, 160, 180]
        for i, thresh_val in enumerate(dark_thresholds):
            _, dark_var = cv2.threshold(
                np.array(img.convert("L")), thresh_val, 255, cv2.THRESH_BINARY_INV
            )
            processed_images.append(Image.fromarray(dark_var))
            logger.debug(f"✓ Method {4 + i}/19: Inversion with threshold {thresh_val}")

        # METHOD 7 (57% confidence) - Third priority
        # -----------------------------------------------------------------------------------
        # Color channel processing and specific detection
        r_channel = img_np[:, :, 0]
        b_channel = img_np[:, :, 2]

        # Channel manipulation variations
        # Channel detection based on differences between R, G, B
        channel_diff = np.absolute(
            r_channel.astype(np.int16) - b_channel.astype(np.int16)
        )
        channel_diff = np.clip(channel_diff * 2, 0, 255).astype(np.uint8)
        _, channel_thresh = cv2.threshold(channel_diff, 30, 255, cv2.THRESH_BINARY)
        processed_images.append(Image.fromarray(channel_thresh))
        logger.debug(
            "✓ Method 7/19: RGB channel processing (R-B difference) (57% effectiveness)"
        )

        # METHOD 8 (41% confidence) and METHOD 9 (41% confidence)
        # -----------------------------------------------------------------------------------
        # Versions with high sharpness and contrast
        gray = img.convert("L")

        # High contrast + sharpness (optimized)
        contrast_sharp = (
            ImageEnhance.Contrast(gray).enhance(2.5).filter(ImageFilter.SHARPEN)
        )
        processed_images.append(contrast_sharp)
        logger.debug("✓ Method 8/19: High contrast + sharpness (41% effectiveness)")

        # Additional sharpness to improve edges
        extra_sharp = contrast_sharp.filter(ImageFilter.SHARPEN).filter(
            ImageFilter.SHARPEN
        )
        processed_images.append(extra_sharp)
        logger.debug("✓ Method 9/19: Extra sharpness (double application)")

        # TECHNIQUES FOR LIGHT TEXT ON DARK BACKGROUND (gray, black)
        # -----------------------------------------------------------------------------------
        # Simple inversion (useful for white text on dark background)
        inverted = Image.fromarray(255 - img_np)
        processed_images.append(inverted)
        logger.debug("✓ Method 10/19: Full image inversion")

        # Adaptive thresholding for text on dark background
        cv_gray = np.array(gray)

        # Adaptive with different windows - better for small numbers on varied backgrounds
        adaptive_thresh1 = cv2.adaptiveThreshold(
            cv_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, 2
        )
        processed_images.append(Image.fromarray(adaptive_thresh1))
        logger.debug("✓ Method 11/19: Gaussian adaptive threshold")

        adaptive_thresh2 = cv2.adaptiveThreshold(
            cv_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 3
        )
        processed_images.append(Image.fromarray(adaptive_thresh2))
        logger.debug("✓ Method 12/19: Mean adaptive threshold")

        # COLOR MANIPULATION FOR COLORED BACKGROUNDS (pink, gray)
        # -----------------------------------------------------------------------------------
        # Light pink/purple in HSV with more precise ranges
        lower_pink = np.array([140, 50, 150])
        upper_pink = np.array([170, 255, 255])
        pink_mask_hsv = cv2.inRange(img_hsv, lower_pink, upper_pink)
        pink_mask_inv = cv2.bitwise_not(pink_mask_hsv)
        processed_images.append(Image.fromarray(pink_mask_inv))
        logger.debug("✓ Method 13/19: HSV mask for pink/purple backgrounds")

        # Light gray in HSV
        lower_gray = np.array([0, 0, 180])
        upper_gray = np.array([180, 30, 255])
        gray_mask_hsv = cv2.inRange(img_hsv, lower_gray, upper_gray)
        gray_mask_inv = cv2.bitwise_not(gray_mask_hsv)
        processed_images.append(Image.fromarray(gray_mask_inv))
        logger.debug("✓ Method 14/19: HSV mask for light gray backgrounds")

        # Dark gray/black
        lower_dark_gray = np.array([0, 0, 0])
        upper_dark_gray = np.array([180, 30, 80])
        dark_gray_mask = cv2.inRange(img_hsv, lower_dark_gray, upper_dark_gray)
        dark_gray_mask_inv = cv2.bitwise_not(dark_gray_mask)
        processed_images.append(Image.fromarray(dark_gray_mask_inv))
        logger.debug("✓ Method 15/19: HSV mask for dark gray/black backgrounds")

        # LUMINOSITY EQUALIZATION AND ENHANCEMENT
        # -----------------------------------------------------------------------------------
        # Lab color space processing - good for numbers on various colored backgrounds
        lab_img = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab_img)

        # Equalize the L channel (luminosity) - a technique that was successful
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)

        # Recombine the channels
        updated_lab_img = cv2.merge((cl, a_channel, b_channel))

        # Convert back to RGB and then to grayscale
        enhanced_img = cv2.cvtColor(updated_lab_img, cv2.COLOR_LAB2RGB)
        enhanced_gray = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2GRAY)

        # Apply thresholding to the enhanced image
        _, binary_enhanced = cv2.threshold(enhanced_gray, 127, 255, cv2.THRESH_BINARY)
        processed_images.append(Image.fromarray(binary_enhanced))
        logger.debug("✓ Method 16/19: Lab color space + CLAHE")

        # Inverted version for light text on dark background
        _, binary_enhanced_inv = cv2.threshold(
            enhanced_gray, 127, 255, cv2.THRESH_BINARY_INV
        )
        processed_images.append(Image.fromarray(binary_enhanced_inv))
        logger.debug("✓ Method 17/19: Lab color space + CLAHE inverted")

        # OPTIMIZED COMBINATIONS - merges successful techniques
        # -----------------------------------------------------------------------------------

        # Combination: high sharpness + high contrast
        contrast_highest = ImageEnhance.Contrast(gray).enhance(3.0)
        sharpened_strong = contrast_highest.filter(ImageFilter.SHARPEN).filter(
            ImageFilter.SHARPEN
        )
        processed_images.append(sharpened_strong)
        logger.debug("✓ Method 18/19: Maximum contrast + double sharpness")

        # Merge lab and hsv to capture the best of both worlds
        merged_img = cv2.addWeighted(enhanced_gray, 0.5, img_gray, 0.5, 0)
        _, merged_thresh = cv2.threshold(merged_img, 140, 255, cv2.THRESH_BINARY)
        processed_images.append(Image.fromarray(merged_thresh))
        logger.debug("✓ Method 19/19: Optimized Lab + HSV combination")

        # Filter valid images
        valid_images = []
        for img_proc in processed_images:
            try:
                if img_proc.mode in ["RGB", "L", "1"]:
                    valid_images.append(img_proc)
            except Exception as e:
                logger.debug(f"Error processing one of the images: {e}")

        logger.info(f"🔬 Processing complete: {len(valid_images)} variations generated")
        print(
            f"Generating {len(valid_images)} optimized preprocessing variations for OCR"
        )

        return valid_images


# Standalone function for full compatibility with the original code
def preprocess_image_for_ocr(img: Image.Image) -> List[Image.Image]:
    """
    Standalone function that exactly replicates the original function from bot_vision.py.

    Args:
        img (Image.Image): Image to be processed

    Returns:
        List[Image.Image]: List of processed images
    """
    processor = ImageProcessor()
    return processor.preprocess_for_ocr(img)


def get_available_methods() -> List[str]:
    """
    Returns the list of available processing methods.

    Returns:
        list: List of available methods
    """
    processor = ImageProcessor()
    return processor.available_methods
