"""Simple HSV colour detector used to isolate trajectory work from ML work."""

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import cv2


@dataclass(frozen=True)
class Detection:
    x_px: float
    y_px: float
    radius_px: float
    area_px: float


class ColorDetector:
    def __init__(
        self,
        lower_hsv: Sequence[int],
        upper_hsv: Sequence[int],
        min_area_px: float = 120.0,
    ) -> None:
        self.lower_hsv = _validate_hsv(lower_hsv)
        self.upper_hsv = _validate_hsv(upper_hsv)
        self.min_area_px = min_area_px

    def detect(self, frame) -> Tuple[Optional[Detection], object]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, mask

        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))
        if area < self.min_area_px:
            return None, mask

        (x, y), radius = cv2.minEnclosingCircle(contour)
        return Detection(float(x), float(y), float(radius), area), mask


def _validate_hsv(value: Sequence[int]) -> Tuple[int, int, int]:
    if len(value) != 3:
        raise ValueError("HSV values must contain exactly three integers")
    hue, saturation, brightness = (int(item) for item in value)
    if not 0 <= hue <= 179 or not 0 <= saturation <= 255 or not 0 <= brightness <= 255:
        raise ValueError("HSV values must be within H=0..179, S/V=0..255")
    return hue, saturation, brightness

