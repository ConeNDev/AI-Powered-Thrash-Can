"""Live camera UI for the Phase 1 trajectory experiment."""

import argparse
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple

import cv2

from smart_bin.detector import ColorDetector
from smart_bin.evaluation import CrossingResult, LineCrossingEvaluator
from smart_bin.recording import SessionRecorder
from smart_bin.trajectory import Observation, Prediction, TrajectoryPredictor


def _hsv(value: str) -> Tuple[int, int, int]:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("HSV must look like 35,80,80") from exc
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("HSV must contain three comma-separated integers")
    return parts  # ColorDetector performs range validation.


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict where a coloured thrown object crosses a catch line")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--camera", type=int, default=0, help="camera index (default: 0)")
    source.add_argument("--video", type=Path, help="video file to process instead of a live camera")
    parser.add_argument("--lower-hsv", type=_hsv, default=(35, 80, 80), help="lower HSV threshold")
    parser.add_argument("--upper-hsv", type=_hsv, default=(85, 255, 255), help="upper HSV threshold")
    parser.add_argument("--min-area", type=float, default=120.0, help="minimum target contour area in pixels")
    parser.add_argument(
        "--catch-line-ratio",
        type=float,
        default=0.82,
        help="catch line y position as a fraction of frame height (default: 0.82)",
    )
    parser.add_argument("--mirror", action="store_true", help="mirror frames before processing")
    parser.add_argument("--show-mask", action="store_true", help="show the threshold mask in a second window")
    parser.add_argument(
        "--record-dir",
        type=Path,
        help="save annotated video and CSV measurements in a new session under this directory",
    )
    return parser


def _timestamp(capture, live: bool, live_start: float) -> float:
    if live:
        return time.perf_counter() - live_start
    position_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
    return position_ms / 1000.0


def _draw_prediction(frame, prediction: Prediction) -> None:
    point = (int(round(prediction.x_px)), int(round(prediction.y_px)))
    cv2.circle(frame, point, 13, (255, 0, 255), 3)
    cv2.putText(
        frame,
        "intercept {:.2f}s conf {:.0f}% err {:.1f}px".format(
            prediction.seconds_remaining,
            prediction.confidence * 100.0,
            prediction.rmse_px,
        ),
        (max(10, point[0] - 180), max(30, point[1] - 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 0, 255),
        2,
        cv2.LINE_AA,
    )


def _draw_crossing(frame, crossing: CrossingResult) -> None:
    point = (int(round(crossing.x_px)), int(round(crossing.y_px)))
    cv2.circle(frame, point, 16, (0, 165, 255), 3)
    selected = crossing.closest_to_lead(0.30)
    if selected is None:
        message = "throw {} crossed: no prior prediction".format(crossing.throw_id)
    else:
        message = "throw {}: {:.0f}ms prediction error {:.1f}px".format(
            crossing.throw_id,
            selected.lead_time_s * 1000.0,
            selected.absolute_error_px,
        )
    cv2.putText(
        frame,
        message,
        (10, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 165, 255),
        2,
        cv2.LINE_AA,
    )


def run(args: argparse.Namespace) -> int:
    if not 0.05 <= args.catch_line_ratio <= 0.98:
        raise ValueError("--catch-line-ratio must be between 0.05 and 0.98")

    live = args.video is None
    capture = cv2.VideoCapture(args.camera if live else str(args.video))
    if not capture.isOpened():
        source = "camera {}".format(args.camera) if live else str(args.video)
        raise RuntimeError("could not open {}".format(source))

    if live:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = ColorDetector(args.lower_hsv, args.upper_hsv, args.min_area)
    predictor = TrajectoryPredictor()
    live_start = time.perf_counter()
    last_timestamp: Optional[float] = None
    evaluator: Optional[LineCrossingEvaluator] = None
    recorder: Optional[SessionRecorder] = None
    last_crossing: Optional[CrossingResult] = None
    show_crossing_until = 0.0

    try:
        while capture.isOpened():
            ok, frame = capture.read()
            if not ok:
                break
            if args.mirror:
                frame = cv2.flip(frame, 1)

            timestamp = _timestamp(capture, live, live_start)
            if last_timestamp is not None and timestamp <= last_timestamp:
                timestamp = last_timestamp + 1.0 / max(capture.get(cv2.CAP_PROP_FPS), 30.0)
            last_timestamp = timestamp

            height, width = frame.shape[:2]
            catch_y = int(round(height * args.catch_line_ratio))
            if evaluator is None:
                evaluator = LineCrossingEvaluator(catch_y)
            if recorder is None and args.record_dir is not None:
                fps = capture.get(cv2.CAP_PROP_FPS)
                if fps <= 0.0 or fps > 240.0:
                    fps = 30.0
                recorder = SessionRecorder(args.record_dir, width, height, fps)
                print("Recording session to {}".format(recorder.session_dir))

            detection, mask = detector.detect(frame)
            prediction = None
            crossing = None

            if detection is not None:
                observation = Observation(timestamp, detection.x_px, detection.y_px)
                predictor.add(observation)
                prediction = predictor.predict(catch_y)
                crossing = evaluator.update(observation, prediction)
                if crossing is not None:
                    last_crossing = crossing
                    show_crossing_until = timestamp + 1.5
                    if recorder is not None:
                        recorder.record_crossing(crossing)
                cv2.circle(
                    frame,
                    (int(round(detection.x_px)), int(round(detection.y_px))),
                    max(4, int(round(detection.radius_px))),
                    (0, 255, 0),
                    2,
                )

            trail = [(int(round(item.x_px)), int(round(item.y_px))) for item in predictor.observations]
            for start, end in zip(trail, trail[1:]):
                cv2.line(frame, start, end, (255, 255, 0), 2)

            cv2.line(frame, (0, catch_y), (width - 1, catch_y), (0, 255, 255), 2)
            cv2.putText(frame, "catch line", (10, max(20, catch_y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            if prediction is not None and 0 <= prediction.x_px < width:
                _draw_prediction(frame, prediction)
            if last_crossing is not None and timestamp <= show_crossing_until:
                _draw_crossing(frame, last_crossing)

            cv2.putText(frame, "q quit | r reset", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            if recorder is not None:
                cv2.putText(frame, "REC", (width - 65, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                recorder.record_frame(frame, timestamp, evaluator.throw_id, detection, prediction)
            cv2.imshow("Smart Catcher Bin - Phase 1", frame)
            if args.show_mask:
                cv2.imshow("Detection mask", mask)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                predictor.clear()
                evaluator.reset()
                last_crossing = None
    finally:
        capture.release()
        if recorder is not None:
            recorder.close()
        cv2.destroyAllWindows()
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
