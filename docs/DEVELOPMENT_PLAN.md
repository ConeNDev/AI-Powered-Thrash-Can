# Development plan

## Product statement

Build a mobile catcher that observes a lightweight thrown object, estimates a
safe reachable intercept on the floor, plans a collision-free route, and moves
the bin under that intercept. The project is a robotics system, not just an AI
model: perception, estimation, planning, controls, mechanics, power, safety,
testing, and telemetry all have to agree on coordinates and deadlines.

## System boundaries and safety rules

- Start with foam balls or loosely crumpled paper only—never glass, metal,
  liquids, batteries, sharp objects, or throws toward people or animals.
- The robot must stop on stale commands, lost localization, obstacle proximity,
  controller disconnect, over-current, low battery, or emergency-stop input.
- Cap speed and acceleration during every indoor test; raise them only after
  logged stopping-distance tests.
- Do not put a rechargeable battery inside a dirty/wet waste compartment.
  Electronics and the removable catch basket need separate enclosures.
- The final demo should be supervised in a marked test area.

## Architecture

```text
camera(s) -> detection -> 3D observations -> trajectory filter -> intercept candidates
                                                                  |
wheel encoders + IMU -> localization -> reachability + route planner -> motion command
depth/LiDAR/bumpers -> obstacle map -------------------------------^          |
                                                                              v
                                                    ESP32 safety + PID -> motor driver
```

The Raspberry Pi is the high-level computer. It performs vision, state
estimation, planning, logging, and networking. The ESP32 owns deterministic
wheel-speed control, encoder sampling, watchdogs, bumpers, and the physical
emergency stop. A serial protocol connects them. The ESP32 stops the motors if
valid commands stop arriving; Linux is never the only safety layer.

## Milestones and acceptance gates

### Phase 0 — requirements and experiment design (now)

- Write measurable constraints: test-area size, basket diameter and mass,
  maximum object mass, throw distance, desired success rate, maximum robot
  speed, floor type, and budget.
- Record every experiment and store configuration with results.

Gate: one-page specification with numeric targets and a safe test protocol.

### Phase 1 — laptop-camera 2D trajectory proof (current repository)

- Fixed camera, side view, plain background, brightly coloured soft object.
- HSV detector supplies timestamped image coordinates.
- Fit horizontal position linearly and vertical position quadratically.
- Predict the next downward crossing of a visible catch line.
- Save short videos for repeatable offline tests before testing live.

Gate: at least 50 recorded throws; median intercept error <= 8 cm after a
pixel-to-centimetre scale is added; useful prediction >= 300 ms before crossing;
no more than 10% false predictions. These are initial targets, not promises.

### Phase 2 — calibrated 3D landing estimator

- Calibrate camera intrinsics and lens distortion with a ChArUco/chessboard.
- Define `camera`, `world`, `robot`, and `basket` coordinate frames explicitly.
- First use two fixed views or a depth camera. Compare against single-camera
  estimates so the observability limitation is visible in the portfolio.
- Replace ordinary least squares with a Kalman/extended Kalman filter and attach
  uncertainty to each candidate landing point.
- Reject objects whose class, estimated mass, trajectory, or confidence is unsafe.

Gate: 90th-percentile landing error is smaller than half the basket's usable
radius on an unseen test set, with prediction latency and uncertainty logged.

### Phase 3 — inexpensive learning rover

- Assemble a small two-wheel differential-drive chassis with encoders, caster,
  ESP32, dual motor driver, bumper switches, and low-voltage bench battery pack.
- Implement wheel-speed PID, odometry, command timeout, E-stop, and serial
  heartbeat before autonomous navigation.
- Drive commanded distances/turns and measure error on the actual floor.

Gate: repeatable stop, straight-line, rotation, and watchdog tests; <5% distance
error over 2 m after calibration; safe stop from the configured maximum speed.

### Phase 4 — navigation and collision avoidance

- Simulate a differential-drive robot first (ROS 2 + Gazebo).
- Build an occupancy/cost map from depth camera or 2D LiDAR; keep bumpers as a
  final independent layer.
- Use a global shortest-path planner plus a local controller that respects the
  robot footprint, acceleration, and dynamic obstacles.
- Convert a predicted intercept into a time-constrained reachable goal. If no
  safe route can arrive before the object, stop instead of chasing it.

Gate: 100 autonomous goals in a bounded course with zero collisions, >=95%
arrival rate, and all unsafe/unreachable targets rejected.

### Phase 5 — catcher-sized mechanical prototype

- Measure payload, centre of gravity, wheel traction, required acceleration,
  torque, stall current, stopping distance, and tip margin before selecting the
  final motors, driver, battery, or chassis.
- Use a wide, shallow, lightweight catch basket before a tall household bin.
- Add compliant bumpers, wheel guards, fuses, master switch, E-stop, battery
  state monitoring, and separated power rails for compute and motors.

Gate: remote-control tests under full payload and fault-injection tests pass
before the autonomous catcher is enabled.

### Phase 6 — integrated intercept and portfolio finish

- Fuse target uncertainty, robot travel time, path risk, and basket geometry.
- Benchmark stationary catch, unobstructed moving catch, then obstacle detour.
- Publish architecture decisions, wiring diagram, CAD, test data, failure cases,
  demo video, build instructions, cost, and honest limitations.

Gate: pre-registered test protocol and reproducible results; a missed or unsafe
throw causes a controlled stop.

## Software ownership by language

- **Python:** experiments, OpenCV/detector inference, trajectory estimation,
  notebooks, data analysis, and early ROS 2 nodes.
- **C++:** ESP-IDF firmware and only later latency-critical ROS 2 nodes.
- **Java:** optional Spring Boot telemetry/configuration service and web API. It
  is useful for demonstrating your existing strength, but should not sit in the
  millisecond motor-safety path.

## First experiment checklist

1. Put the laptop 2–4 m from a clear side-on throwing plane and keep it still.
2. Use a soft green ball or green crumpled paper and a contrasting background.
3. Keep people, pets, breakables, and liquids out of the marked test zone.
4. Run the app, check the mask, and tune HSV thresholds before throwing.
5. Make gentle arcs parallel to the camera plane; confirm the cyan trail follows
   the object and the magenta point settles on the yellow line.
6. Record false detections, time remaining, pixel error, lighting, and throw type.

## Decisions deliberately postponed

- final motor, wheel, driver, and battery sizing (requires measured mass/speed);
- monocular versus stereo/depth camera (requires Phase 1 error data and layout);
- 2D LiDAR versus depth-camera navigation (depends on budget and floor hazards);
- full ROS 2 adoption on the Pi (learn it in simulation before integration);
- ML detector model (collect representative video before choosing/training one).

