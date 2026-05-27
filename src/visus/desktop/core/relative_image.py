"""
Visus Desktop - Relative Image Detection

This module implements relative image detection (anchor + target),
allowing a target image near an anchor image to be located.
"""

import logging
from typing import List, Optional, Tuple

import pyautogui

from ..exceptions import ImageNotFoundError

logger = logging.getLogger(__name__)


class RelativeImageDetector:
    """
    Relative image detector.

    Allows locating a target image near an anchor image,
    useful when there are multiple occurrences of the target image on the screen.
    """

    def __init__(self):
        """Initializes the relative image detector."""
        pass

    def locate_relative_image(
        self,
        anchor_image_path: str,
        target_image_path: str,
        confidence: float = 0.9,
        max_distance: int = 200,
        target_region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[Tuple]:
        """
        Locates a target image near an anchor image.

        Args:
            anchor_image_path: Path to the anchor image (unique on the screen)
            target_image_path: Path to the target image (may have multiple)
            confidence: Confidence level for detection (0.0-1.0)
            max_distance: Maximum distance in pixels from the anchor to the target
            target_region: Specific region to search for the target image (x, y, width, height)

        Returns:
            Location of the target image closest to the anchor, or None

        Raises:
            ImageNotFoundError: If the anchor image is not found
        """
        try:
            # First, locate the anchor image (always on the whole screen)
            logger.info(f"Searching for anchor image: {anchor_image_path}")
            anchor_location = pyautogui.locateOnScreen(
                anchor_image_path, confidence=confidence
            )

            if not anchor_location:
                raise ImageNotFoundError(f"Anchor image not found: {anchor_image_path}")

            logger.info(f"Anchor image found at: {anchor_location}")
            anchor_center = pyautogui.center(anchor_location)

            # Now search for all occurrences of the target image
            logger.info(f"Searching for target image: {target_image_path}")

            # If target_region was specified, search only in that region
            if target_region:
                logger.info(f"Searching for target in specific region: {target_region}")
                target_locations = list(
                    pyautogui.locateAllOnScreen(
                        target_image_path, region=target_region, confidence=confidence
                    )
                )
            else:
                # Search the whole screen
                target_locations = list(
                    pyautogui.locateAllOnScreen(
                        target_image_path, confidence=confidence
                    )
                )

            if not target_locations:
                region_info = (
                    f"in region {target_region}"
                    if target_region
                    else "on the whole screen"
                )
                logger.warning(
                    f"Target image not found {region_info}: {target_image_path}"
                )
                return None

            logger.info(
                f"Found {len(target_locations)} occurrences of the target image"
            )

            # Compute the distance from each target to the anchor and find the closest one
            closest_target = None
            min_distance = float("inf")

            for target_location in target_locations:
                target_center = pyautogui.center(target_location)

                # Compute Euclidean distance
                distance = (
                    (target_center.x - anchor_center.x) ** 2
                    + (target_center.y - anchor_center.y) ** 2
                ) ** 0.5

                logger.info(
                    f"Target at {target_location} is {distance:.1f}px from the anchor"
                )

                # Check whether it is within the maximum distance and is the closest
                if distance <= max_distance and distance < min_distance:
                    min_distance = distance
                    closest_target = target_location

            if closest_target:
                logger.info(
                    f"Closest target selected: {closest_target} "
                    f"(distance: {min_distance:.1f}px)"
                )
                return closest_target
            else:
                logger.warning(
                    f"No target image found within {max_distance}px of the anchor"
                )
                return None

        except Exception as e:
            logger.error(f"Error locating relative image: {e}")
            raise ImageNotFoundError(f"Error in relative image detection: {e}") from e

    def locate_image_with_retry(
        self,
        image_path: str,
        region: Optional[Tuple] = None,
        confidence: float = 0.9,
        max_attempts: int = 3,
        scales: Optional[List[float]] = None,
    ) -> Optional[Tuple]:
        """
        Attempts to locate an image with different scales and confidence levels.

        Args:
            image_path: Path to the image
            region: Region to search in (x, y, width, height)
            confidence: Initial confidence level
            max_attempts: Maximum number of attempts
            scales: List of scales to test (None to use the default)

        Returns:
            Location of the image, or None if not found
        """
        import os

        from PIL import Image

        if scales is None:
            scales = [1.0, 0.95, 1.05]  # Try with the original scale and ±5%

        for attempt in range(max_attempts):
            # Try to locate with different scales
            for scale in scales:
                try:
                    if scale != 1.0:
                        # Load and resize the reference image
                        ref_img = Image.open(image_path)
                        new_width = int(ref_img.width * scale)
                        new_height = int(ref_img.height * scale)
                        scaled_img = ref_img.resize((new_width, new_height))

                        # Save temporarily to use with pyautogui
                        temp_path = f"temp_scaled_{scale}.png"
                        scaled_img.save(temp_path)

                        if region:
                            location = pyautogui.locateOnScreen(
                                temp_path, region=region, confidence=confidence
                            )
                        else:
                            location = pyautogui.locateOnScreen(
                                temp_path, confidence=confidence
                            )

                        os.remove(temp_path)  # Clean up the temporary file
                    else:
                        if region:
                            location = pyautogui.locateOnScreen(
                                image_path, region=region, confidence=confidence
                            )
                        else:
                            location = pyautogui.locateOnScreen(
                                image_path, confidence=confidence
                            )

                    if location:
                        return location
                except Exception as e:
                    logger.debug(f"Error searching for image with scale {scale}: {e}")
                    continue

            # If the scale did not work, try reducing the confidence
            adjusted_confidence = max(0.7, confidence - 0.05 * (attempt + 1))
            logger.debug(f"Adjusting confidence to {adjusted_confidence}")

            try:
                if region:
                    location = pyautogui.locateOnScreen(
                        image_path, region=region, confidence=adjusted_confidence
                    )
                else:
                    location = pyautogui.locateOnScreen(
                        image_path, confidence=adjusted_confidence
                    )

                if location:
                    return location
            except Exception as e:
                logger.debug(f"Error searching for image with adjusted confidence: {e}")

            # Small pause between attempts
            import time

            time.sleep(0.5)

        return None
