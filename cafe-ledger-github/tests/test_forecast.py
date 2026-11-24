import unittest
from datetime import date, timedelta
from cafe.forecast import predict


class ForecastTests(unittest.TestCase):
    today = date(2026, 11, 24)

    def series(self, n=70, constant=False):
        return [{'date': (self.today - timedelta(days=n-i)).isoformat(),
                 'net_minor': 100000 if constant else 100000 + i * 2000 + (i % 7) * 13000} for i in range(n)]

    def test_requires_enough_history(self):
        self.assertFalse(predict(self.series(34), self.today)['ready'])
        self.assertTrue(predict(self.series(35), self.today)['ready'])

    def test_dates_and_seven_day_holdout(self):
        result = predict(self.series(), self.today)
        self.assertEqual(result['training_days'], 63)
        self.assertLess(result['train_end'], result['test_start'])
        self.assertEqual(result['test_end'], '2026-11-23')
        self.assertEqual([row['date'] for row in result['future']], [(self.today + timedelta(days=i)).isoformat() for i in range(1, 8)])
        self.assertEqual(len(result['holdout']), 7)

    def test_today_and_future_sales_never_enter_training(self):
        rows = self.series()
        expected = predict(rows, self.today)
        rows += [{'date': (self.today + timedelta(days=i)).isoformat(), 'net_minor': 999999999} for i in range(3)]
        self.assertEqual(predict(rows, self.today), expected)

    def test_holdout_targets_do_not_leak_into_holdout_predictions(self):
        rows = self.series()
        before = predict(rows, self.today)
        for row in rows[-7:]:
            row['net_minor'] *= 10
        after = predict(rows, self.today)
        for first, second in zip(before['holdout'], after['holdout']):
            self.assertEqual(first['ridge_minor'], second['ridge_minor'])
            self.assertEqual(first['baseline_minor'], second['baseline_minor'])
        self.assertNotEqual(before['model_mae_minor'], after['model_mae_minor'])

    def test_constant_sales_have_zero_error(self):
        result = predict(self.series(constant=True), self.today)
        self.assertEqual(result['baseline_mae_minor'], 0)
        self.assertEqual(result['model_mae_minor'], 0)
        self.assertEqual(result['total_minor'], 700000)

    def test_mae_matches_reported_holdout(self):
        result = predict(self.series(), self.today)
        expected = sum(abs(row['actual_minor'] - row['ridge_minor']) for row in result['holdout']) / 7
        self.assertAlmostEqual(expected, result['model_mae_minor'], delta=1)

    def test_gap_and_unsorted_history_rejected(self):
        rows = self.series()
        del rows[4]
        with self.assertRaises(ValueError):
            predict(rows, self.today)
        with self.assertRaises(ValueError):
            predict(list(reversed(self.series())), self.today)

    def test_predictions_never_negative(self):
        rows = self.series()
        for index, row in enumerate(rows):
            row['net_minor'] = max(0, 200000 - index * 5000)
        result = predict(rows, self.today)
        self.assertTrue(all(row['ridge_minor'] >= 0 for row in result['future']))


if __name__ == '__main__':
    unittest.main()
