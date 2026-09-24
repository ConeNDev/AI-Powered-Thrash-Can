"""Evaluate image-space intercept predictions against an observed line crossing."""

from dataclasses import dataclass
from statistics import median
from typing import List, Optional, Tuple

from smart_bin.trajectory import Observation, Prediction


@dataclass(frozen=True)
class PredictionSample:
    timestamp_s: float
    predicted_x_px: float
    predicted_crossing_timestamp_s: float
    confidence: float
    rmse_px: float


@dataclass(frozen=True)
class PredictionError:
    prediction_timestamp_s: float
    lead_time_s: float
    predicted_x_px: float
    absolute_error_px: float
    predicted_crossing_timestamp_s: float
    arrival_time_error_s: float
    confidence: float
    rmse_px: float


@dataclass(frozen=True)
class CrossingResult:
    throw_id: int
    timestamp_s: float
    x_px: float
    y_px: float
    errors: Tuple[PredictionError, ...]

    @property
    def median_error_px(self) -> Optional[float]:
        if not self.errors:
            return None
        return float(median(item.absolute_error_px for item in self.errors))

    def closest_to_lead(self, target_lead_s: float) -> Optional[PredictionError]:
        if not self.errors:
            return None
        return min(self.errors, key=lambda item: abs(item.lead_time_s - target_lead_s))


class LineCrossingEvaluator:
    """Track one throw and score every prediction when it crosses a horizontal line."""

    def __init__(self, catch_y_px: float, reset_gap_s: float = 0.40) -> None:
        self.catch_y_px = catch_y_px
        self.reset_gap_s = reset_gap_s
        self.throw_id = 1
        self._previous: Optional[Observation] = None
        self._prediction_samples: List[PredictionSample] = []
        self._crossed = False

    def reset(self) -> None:
        if self._previous is not None or self._prediction_samples or self._crossed:
            self.throw_id += 1
        self._previous = None
        self._prediction_samples.clear()
        self._crossed = False

    def update(
        self,
        observation: Observation,
        prediction: Optional[Prediction],
    ) -> Optional[CrossingResult]:
        if self._previous is not None:
            gap = observation.timestamp_s - self._previous.timestamp_s
            if gap > self.reset_gap_s:
                self.reset()

        result = self._detect_crossing(observation)
        if result is None and not self._crossed and prediction is not None:
            self._prediction_samples.append(
                PredictionSample(
                    timestamp_s=observation.timestamp_s,
                    predicted_x_px=prediction.x_px,
                    predicted_crossing_timestamp_s=observation.timestamp_s + prediction.seconds_remaining,
                    confidence=prediction.confidence,
                    rmse_px=prediction.rmse_px,
                )
            )

        self._previous = observation
        return result

    def _detect_crossing(self, current: Observation) -> Optional[CrossingResult]:
        previous = self._previous
        if self._crossed or previous is None:
            return None

        vertical_change = current.y_px - previous.y_px
        crossed_downward = previous.y_px < self.catch_y_px <= current.y_px and vertical_change > 0.0
        if not crossed_downward:
            return None

        fraction = (self.catch_y_px - previous.y_px) / vertical_change
        crossing_timestamp = previous.timestamp_s + fraction * (current.timestamp_s - previous.timestamp_s)
        crossing_x = previous.x_px + fraction * (current.x_px - previous.x_px)

        errors = tuple(
            PredictionError(
                prediction_timestamp_s=sample.timestamp_s,
                lead_time_s=crossing_timestamp - sample.timestamp_s,
                predicted_x_px=sample.predicted_x_px,
                absolute_error_px=abs(sample.predicted_x_px - crossing_x),
                predicted_crossing_timestamp_s=sample.predicted_crossing_timestamp_s,
                arrival_time_error_s=abs(sample.predicted_crossing_timestamp_s - crossing_timestamp),
                confidence=sample.confidence,
                rmse_px=sample.rmse_px,
            )
            for sample in self._prediction_samples
            if sample.timestamp_s < crossing_timestamp
        )
        self._crossed = True
        return CrossingResult(
            throw_id=self.throw_id,
            timestamp_s=crossing_timestamp,
            x_px=crossing_x,
            y_px=self.catch_y_px,
            errors=errors,
        )
