# Smart Catcher Bin

An incremental robotics project whose final goal is a mobile bin that predicts
where a lightweight thrown object will land, drives to the intercept point, and
avoids floor obstacles.

The repository currently contains **Phase 1: laptop-camera trajectory proof**.
It tracks a brightly coloured object, fits its image-space flight path, and
draws the predicted crossing point on a configurable horizontal catch line.

## What this prototype proves

- frames can be captured and timestamped in real time;
- a target can be detected without an ML model;
- a noisy sequence of target centres can be fitted to a ballistic curve;
- an intercept and time-to-intercept can be updated on every frame.

It does **not** yet estimate a true 3D landing point or move hardware. A single
uncalibrated camera cannot reliably recover arbitrary 3D motion. Phase 2 adds
calibration and repeatable measurements; robot motion comes after that.

## Quick start

Use Python 3.9 or newer. On macOS, allow your terminal application to use the
camera when prompted.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
smart-bin-camera
```

Hold a bright green ball or crumpled paper in view. The default detector looks
for green. Press `r` to clear the current trajectory and `q` to quit.

Useful options:

```bash
# Inspect all options
smart-bin-camera --help

# Tune the detector for an orange object
smart-bin-camera --lower-hsv 5,100,100 --upper-hsv 25,255,255

# Process a recording instead of the webcam
smart-bin-camera --video captures/throw.mp4

# Record an annotated video and CSV measurements
smart-bin-camera --show-mask --record-dir captures
```

Recording creates a timestamped directory containing:

- `annotated.mp4` — the camera view with detection and prediction overlays;
- `telemetry.csv` — every frame's detection, prediction, fit error, and confidence;
- `crossings.csv` — actual downward crossings plus position and arrival-time
  error for every earlier prediction.

When a detected object crosses the yellow line downward, an orange marker shows
the measured crossing. The status text reports the prediction made closest to
300 ms before that crossing. Press `r` between attempts if the object remains
visible; a detection gap longer than 0.4 seconds starts a new throw automatically.

For the first experiment, place the laptop sideways to the throw, keep it
fixed, use a plain background, and throw only a soft lightweight object into an
empty area. Move the yellow catch line with `--catch-line-ratio`.

## Repository map

- `src/smart_bin/detector.py` — HSV colour target detector
- `src/smart_bin/trajectory.py` — dependency-free least-squares flight model
- `src/smart_bin/app.py` — live/video OpenCV application
- `tests/` — deterministic physics tests
- `docs/DEVELOPMENT_PLAN.md` — staged engineering roadmap and acceptance gates
- `docs/HARDWARE_PLAN.md` — purchase strategy and eventual system architecture
