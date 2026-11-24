"""Run the teaching forecast on the included synthetic CSV, without changing bills."""
import csv
from datetime import date, timedelta
from pathlib import Path
from cafe.config import money
from cafe.forecast import predict


def main():
    path = Path(__file__).resolve().parent / 'data' / 'sample_daily_sales.csv'
    with path.open(encoding='utf-8', newline='') as file:
        rows = list(csv.DictReader(file))
    series = [{'date': row['date'], 'net_minor': money(row['net_sales'])} for row in rows]
    simulated_today = date.fromisoformat(series[-1]['date']) + timedelta(days=1)
    result = predict(series, simulated_today)
    print('SYNTHETIC TEACHING DATA — INR. These are not real cafe forecasts.')
    print(f'Simulated today: {simulated_today}. Today is excluded from forecasts.')
    print(f"Training days: {result['training_days']}; test: {result['test_start']} to {result['test_end']}")
    print(f"Ridge MAE: INR {result['model_mae_minor']/100:.2f}; baseline MAE: INR {result['baseline_mae_minor']/100:.2f}")
    print('Selected method:', result['selected_method'])
    print('Date          Ridge INR    Baseline INR    Selected INR')
    for row in result['future']:
        print(f"{row['date']}    {row['ridge_minor']/100:9.2f}    {row['baseline_minor']/100:12.2f}    {row['selected_minor']/100:12.2f}")


if __name__ == '__main__':
    main()
