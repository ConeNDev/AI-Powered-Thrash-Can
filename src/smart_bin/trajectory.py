"""Small, deterministic image-space ballistic trajectory estimator.

Image coordinates have their origin in the top-left, so a falling object has a
positive y velocity. We fit x(t) linearly and y(t) quadratically, then solve for
the next downward crossing of the configured catch line.
"""

from collections import deque
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Deque, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Observation:
    timestamp_s: float
    x_px: float
    y_px: float


@dataclass(frozen=True)
class Prediction:
    x_px: float
    y_px: float
    seconds_remaining: float
    rmse_px: float
    sample_count: int
    confidence: float


def _solve_linear_system(matrix: Sequence[Sequence[float]], values: Sequence[float]) -> List[float]:
    """Solve a small dense linear system with partial-pivot Gaussian elimination."""
    size = len(values)
    augmented = [list(matrix[row]) + [float(values[row])] for row in range(size)]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("trajectory samples do not contain enough independent motion")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]

        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[column])
            ]

    return [augmented[row][-1] for row in range(size)]


def _least_squares_polynomial(times: Sequence[float], values: Sequence[float], degree: int) -> List[float]:
    """Return ascending polynomial coefficients using the normal equations."""
    columns = degree + 1
    sums = [sum(t ** power for t in times) for power in range(2 * degree + 1)]
    matrix = [[sums[row + column] for column in range(columns)] for row in range(columns)]
    vector = [sum(value * (t ** power) for t, value in zip(times, values)) for power in range(columns)]
    return _solve_linear_system(matrix, vector)


def _evaluate(coefficients: Sequence[float], time_s: float) -> float:
    result = 0.0
    for coefficient in reversed(coefficients):
        result = result * time_s + coefficient
    return result


class TrajectoryPredictor:
    def __init__(
        self,
        min_samples: int = 6,
        window_size: int = 18,
        min_span_s: float = 0.10,
        reset_gap_s: float = 0.40,
        max_prediction_horizon_s: float = 1.50,
        min_downward_velocity_px_s: float = 20.0,
    ) -> None:
        if min_samples < 3 or window_size < min_samples:
            raise ValueError("window_size must be >= min_samples >= 3")
        self._observations: Deque[Observation] = deque(maxlen=window_size)
        self.min_samples = min_samples
        self.min_span_s = min_span_s
        self.reset_gap_s = reset_gap_s
        self.max_prediction_horizon_s = max_prediction_horizon_s
        self.min_downward_velocity_px_s = min_downward_velocity_px_s

    @property
    def observations(self) -> Tuple[Observation, ...]:
        return tuple(self._observations)

    def clear(self) -> None:
        self._observations.clear()

    def add(self, observation: Observation) -> None:
        if not all(isfinite(value) for value in (observation.timestamp_s, observation.x_px, observation.y_px)):
            raise ValueError("observation values must be finite")

        if self._observations:
            gap = observation.timestamp_s - self._observations[-1].timestamp_s
            if gap <= 0:
                raise ValueError("observation timestamps must increase")
            if gap > self.reset_gap_s:
                self.clear()
        self._observations.append(observation)

    def predict(self, catch_y_px: float) -> Optional[Prediction]:
        if len(self._observations) < self.min_samples:
            return None

        latest_time = self._observations[-1].timestamp_s
        relative_times = [item.timestamp_s - latest_time for item in self._observations]
        if relative_times[-1] - relative_times[0] < self.min_span_s:
            return None

        xs = [item.x_px for item in self._observations]
        ys = [item.y_px for item in self._observations]
        try:
            x_coefficients = _least_squares_polynomial(relative_times, xs, degree=1)
            y_coefficients = _least_squares_polynomial(relative_times, ys, degree=2)
        except ValueError:
            return None

        a = y_coefficients[2]
        b = y_coefficients[1]
        c = y_coefficients[0] - catch_y_px
        if abs(a) < 1e-9:
            if abs(b) < 1e-9:
                return None
            roots = [-c / b]
        else:
            discriminant = b * b - 4.0 * a * c
            if discriminant < 0:
                return None
            root_offset = sqrt(discriminant)
            roots = [(-b - root_offset) / (2.0 * a), (-b + root_offset) / (2.0 * a)]

        candidates = []
        for root in roots:
            vertical_velocity = b + 2.0 * a * root
            if (
                root > 0.0
                and root <= self.max_prediction_horizon_s
                and vertical_velocity >= self.min_downward_velocity_px_s
            ):
                candidates.append(root)
        if not candidates:
            return None

        seconds_remaining = min(candidates)
        predicted_x = _evaluate(x_coefficients, seconds_remaining)

        squared_errors = []
        for time_s, actual_x, actual_y in zip(relative_times, xs, ys):
            dx = _evaluate(x_coefficients, time_s) - actual_x
            dy = _evaluate(y_coefficients, time_s) - actual_y
            squared_errors.append(dx * dx + dy * dy)
        rmse = sqrt(sum(squared_errors) / len(squared_errors))

        sample_score = min(1.0, len(self._observations) / 12.0)
        residual_score = max(0.0, 1.0 - rmse / 35.0)
        horizon_score = max(0.0, 1.0 - seconds_remaining / self.max_prediction_horizon_s)
        confidence = sample_score * residual_score * horizon_score

        return Prediction(
            x_px=predicted_x,
            y_px=catch_y_px,
            seconds_remaining=seconds_remaining,
            rmse_px=rmse,
            sample_count=len(self._observations),
            confidence=confidence,
        )

