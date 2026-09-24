"""Session recording for reproducible Phase 1 experiments."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2

from smart_bin.detector import Detection
from smart_bin.evaluation import CrossingResult
from smart_bin.trajectory import Prediction


class SessionRecorder:
    def __init__(self, base_dir: Path, width: int, height: int, fps: float) -> None:
        session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.session_dir = base_dir / session_name
        self.session_dir.mkdir(parents=True, exist_ok=False)

        self._video = cv2.VideoWriter(
            str(self.session_dir / "annotated.mp4"),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not self._video.isOpened():
            raise RuntimeError("could not create the session video")

        self._telemetry_file = (self.session_dir / "telemetry.csv").open("w", newline="", encoding="utf-8")
        self._telemetry = csv.DictWriter(
            self._telemetry_file,
            fieldnames=[
                "timestamp_s",
                "throw_id",
                "detected",
                "x_px",
                "y_px",
                "radius_px",
                "area_px",
                "predicted_x_px",
                "predicted_y_px",
                "seconds_remaining",
                "fit_rmse_px",
                "confidence",
            ],
        )
        self._telemetry.writeheader()

        self._crossings_file = (self.session_dir / "crossings.csv").open("w", newline="", encoding="utf-8")
        self._crossings = csv.DictWriter(
            self._crossings_file,
            fieldnames=[
                "throw_id",
                "crossing_timestamp_s",
                "actual_x_px",
                "prediction_timestamp_s",
                "actual_lead_time_s",
                "predicted_x_px",
                "absolute_error_px",
                "predicted_crossing_timestamp_s",
                "arrival_time_error_s",
                "confidence",
                "fit_rmse_px",
            ],
        )
        self._crossings.writeheader()

    def record_frame(
        self,
        frame,
        timestamp_s: float,
        throw_id: int,
        detection: Optional[Detection],
        prediction: Optional[Prediction],
    ) -> None:
        self._video.write(frame)
        self._telemetry.writerow(
            {
                "timestamp_s": _number(timestamp_s),
                "throw_id": throw_id,
                "detected": detection is not None,
                "x_px": _number(detection.x_px) if detection else "",
                "y_px": _number(detection.y_px) if detection else "",
                "radius_px": _number(detection.radius_px) if detection else "",
                "area_px": _number(detection.area_px) if detection else "",
                "predicted_x_px": _number(prediction.x_px) if prediction else "",
                "predicted_y_px": _number(prediction.y_px) if prediction else "",
                "seconds_remaining": _number(prediction.seconds_remaining) if prediction else "",
                "fit_rmse_px": _number(prediction.rmse_px) if prediction else "",
                "confidence": _number(prediction.confidence) if prediction else "",
            }
        )

    def record_crossing(self, crossing: CrossingResult) -> None:
        if not crossing.errors:
            self._crossings.writerow(
                {
                    "throw_id": crossing.throw_id,
                    "crossing_timestamp_s": _number(crossing.timestamp_s),
                    "actual_x_px": _number(crossing.x_px),
                }
            )
        else:
            for error in crossing.errors:
                self._crossings.writerow(
                    {
                        "throw_id": crossing.throw_id,
                        "crossing_timestamp_s": _number(crossing.timestamp_s),
                        "actual_x_px": _number(crossing.x_px),
                        "prediction_timestamp_s": _number(error.prediction_timestamp_s),
                        "actual_lead_time_s": _number(error.lead_time_s),
                        "predicted_x_px": _number(error.predicted_x_px),
                        "absolute_error_px": _number(error.absolute_error_px),
                        "predicted_crossing_timestamp_s": _number(error.predicted_crossing_timestamp_s),
                        "arrival_time_error_s": _number(error.arrival_time_error_s),
                        "confidence": _number(error.confidence),
                        "fit_rmse_px": _number(error.rmse_px),
                    }
                )
        self._crossings_file.flush()

    def close(self) -> None:
        self._video.release()
        self._telemetry_file.close()
        self._crossings_file.close()


def _number(value: float) -> str:
    return "{:.6f}".format(value)
