import math
import unittest

from smart_bin.trajectory import Observation, TrajectoryPredictor


def ballistic_position(time_s):
    return 100.0 + 200.0 * time_s, 50.0 + 100.0 * time_s + 400.0 * time_s * time_s


class TrajectoryPredictorTest(unittest.TestCase):
    def test_predicts_downward_catch_line_crossing(self):
        predictor = TrajectoryPredictor(min_samples=6)
        for index in range(9):
            time_s = index * 0.05
            x_px, y_px = ballistic_position(time_s)
            predictor.add(Observation(time_s, x_px, y_px))

        prediction = predictor.predict(catch_y_px=300.0)

        self.assertIsNotNone(prediction)
        absolute_crossing_time = (-100.0 + math.sqrt(100.0 ** 2 + 4.0 * 400.0 * 250.0)) / 800.0
        self.assertAlmostEqual(prediction.seconds_remaining, absolute_crossing_time - 0.40, places=8)
        self.assertAlmostEqual(prediction.x_px, 100.0 + 200.0 * absolute_crossing_time, places=7)
        self.assertAlmostEqual(prediction.rmse_px, 0.0, places=7)

    def test_requires_enough_samples(self):
        predictor = TrajectoryPredictor(min_samples=6)
        for index in range(5):
            predictor.add(Observation(index * 0.05, 10.0 + index, 20.0 + index * index))

        self.assertIsNone(predictor.predict(300.0))

    def test_gap_starts_a_new_throw(self):
        predictor = TrajectoryPredictor(min_samples=3, reset_gap_s=0.25)
        predictor.add(Observation(0.00, 10.0, 20.0))
        predictor.add(Observation(0.05, 11.0, 21.0))
        predictor.add(Observation(0.50, 50.0, 60.0))

        self.assertEqual(len(predictor.observations), 1)
        self.assertEqual(predictor.observations[0].x_px, 50.0)

    def test_rejects_non_increasing_timestamps(self):
        predictor = TrajectoryPredictor()
        predictor.add(Observation(1.0, 10.0, 20.0))

        with self.assertRaisesRegex(ValueError, "timestamps must increase"):
            predictor.add(Observation(1.0, 11.0, 21.0))


if __name__ == "__main__":
    unittest.main()
