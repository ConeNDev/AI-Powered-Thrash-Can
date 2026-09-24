import unittest

from smart_bin.evaluation import LineCrossingEvaluator
from smart_bin.trajectory import Observation, Prediction


def prediction(x_px, seconds_remaining=0.5):
    return Prediction(
        x_px=x_px,
        y_px=300.0,
        seconds_remaining=seconds_remaining,
        rmse_px=2.0,
        sample_count=8,
        confidence=0.8,
    )


class LineCrossingEvaluatorTest(unittest.TestCase):
    def test_interpolates_downward_crossing_and_scores_predictions(self):
        evaluator = LineCrossingEvaluator(catch_y_px=300.0)
        self.assertIsNone(evaluator.update(Observation(0.0, 100.0, 200.0), prediction(140.0)))
        self.assertIsNone(evaluator.update(Observation(0.2, 120.0, 280.0), prediction(136.0, 0.15)))

        result = evaluator.update(Observation(0.4, 140.0, 320.0), None)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.timestamp_s, 0.3)
        self.assertAlmostEqual(result.x_px, 130.0)
        self.assertEqual(len(result.errors), 2)
        self.assertAlmostEqual(result.errors[0].lead_time_s, 0.3)
        self.assertAlmostEqual(result.errors[0].absolute_error_px, 10.0)
        self.assertAlmostEqual(result.errors[0].predicted_crossing_timestamp_s, 0.5)
        self.assertAlmostEqual(result.errors[0].arrival_time_error_s, 0.2)
        self.assertAlmostEqual(result.closest_to_lead(0.3).absolute_error_px, 10.0)

    def test_does_not_count_upward_crossing(self):
        evaluator = LineCrossingEvaluator(catch_y_px=300.0)
        evaluator.update(Observation(0.0, 100.0, 320.0), None)

        result = evaluator.update(Observation(0.1, 110.0, 280.0), None)

        self.assertIsNone(result)

    def test_gap_starts_next_throw(self):
        evaluator = LineCrossingEvaluator(catch_y_px=300.0, reset_gap_s=0.4)
        evaluator.update(Observation(0.0, 100.0, 200.0), None)
        evaluator.update(Observation(0.5, 200.0, 200.0), None)

        self.assertEqual(evaluator.throw_id, 2)


if __name__ == "__main__":
    unittest.main()
