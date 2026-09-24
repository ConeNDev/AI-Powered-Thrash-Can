# Hardware purchase plan

Do not buy the final full-size drive hardware yet. Motor torque, current, battery
capacity, wheel diameter, and stability cannot be selected responsibly until the
payload, required travel distance, available intercept time, and floor are
measured. Buying a cheap learning rover first is less expensive than replacing
an under-sized full-bin drivetrain.

## Buy by milestone

### Now — Phase 1

Required purchase: **none** if the laptop webcam works.

Helpful only if already convenient:

- bright foam ball or coloured paper;
- tape measure and painter's tape for ground truth;
- tripod/stand for repeatable camera placement;
- printed ChArUco/chessboard later for calibration.

### Phase 3 — learning rover (rough target: US$45–90, local tax/shipping excluded)

- ESP32-S3 development board with native USB;
- two-wheel acrylic or metal educational chassis kit with two low-voltage geared
  motors, **quadrature encoders**, wheels, and caster;
- TB6612FNG dual motor-driver breakout for small TT/N20 learning motors;
- two lever microswitches for bumpers;
- inline fuse, latching master switch, and large normally-closed E-stop;
- AA NiMH holder/cells or a protected, reputable low-voltage pack and its correct
  charger; use a bench supply for early stationary tests if available.

Avoid L298N boards: they are common and cheap but inefficient. Do not use a
solderless breadboard for motor current, do not drive motors from ESP32 pins, and
do not buy unprotected loose lithium cells for a first hardware build.

### Phase 4 — onboard compute and perception (rough target: US$180–350)

- Raspberry Pi 5, **4 GB is enough for the planned headless robot**;
- official active cooler;
- official 27 W USB-C supply for bench development;
- 32–64 GB high-endurance microSD card;
- Raspberry Pi Camera Module 3 Wide for a robot-mounted view, or preferably a
  supported stereo/depth camera when Phase 2 proves it is required;
- 2D LiDAR only if the depth approach cannot provide reliable floor obstacles;
- logic-level USB/UART link to the ESP32.

The robot battery will eventually need a dedicated regulated 5 V rail for the
Pi. Motor power and compute power should branch from the fused battery path and
share a deliberate ground; motor noise must not brown out the Pi.

### Phase 5 — final platform (price only after engineering measurements)

- rigid low-centre-of-gravity base and removable lightweight basket;
- two encoder-equipped metal DC gearmotors sized from torque and speed tests;
- motor driver selected above measured stall current with margin;
- rubber drive wheels and stable casters/omni supports;
- protected battery pack from a reputable supplier, matching charger, BMS,
  main fuse, current/voltage monitor, master disconnect, and enclosure;
- wheel guards, compliant perimeter bumper, physical E-stop, wiring harness,
  strain relief, connectors, and spare fuses.

## Recommended versus cheapest

| Part | Cheapest sensible learning choice | Recommended final direction |
|---|---|---|
| High-level computer | keep using laptop | Raspberry Pi 5 4 GB + active cooler |
| Real-time controller | ESP32 dev board | ESP32-S3 dev board with USB and documented pinout |
| First camera | laptop webcam | two calibrated views or supported depth/stereo camera |
| Pi camera | skip initially | Camera Module 3 Wide for navigation/recording |
| Learning motors | encoded TT/N20 gearmotors | metal gearmotors with quadrature encoders, sized later |
| Small motor driver | TB6612FNG | final driver sized from worst-case current |
| Obstacle sensing | bump switches + simulation | depth/2D LiDAR + bumpers + wheel odometry/IMU |
| Battery | bench supply or NiMH learning pack | protected pack + BMS/fuse/charger, sized later |
| Chassis | 2WD kit | custom wide, low base after mass/acceleration tests |

## Why Raspberry Pi plus ESP32

Linux on the Pi is excellent for cameras, models, planning, networking, and
logs, but it is not a hard real-time motor safety controller. The ESP32 supplies
predictable PWM/encoder timing and can stop independently when its heartbeat
expires. This split is common, understandable to interviewers, and lets the
project demonstrate distributed-system design as well as robotics.

## Sizing data to collect before the final order

- total mass and centre-of-gravity height;
- basket opening and usable catch radius;
- maximum required distance and minimum available time;
- target top speed and acceleration;
- wheel diameter and floor coefficient of friction;
- slope/threshold height, desired runtime, and available charging time;
- motor free current, typical current, stall current, encoder resolution;
- measured Pi/peripheral peak power and motor electrical noise;
- braking distance under full payload.

