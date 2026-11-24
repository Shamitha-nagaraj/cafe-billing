"""Small supervised model, chronological holdout, and an honest baseline."""
from datetime import date, timedelta
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error


def features(dates, origin):
    return [[(day-origin).days/30.0] + [int(day.weekday()==i) for i in range(7)] for day in dates]


def baseline(history, targets):
    # Only known history is used; no target-day sales enter the baseline.
    profile = {}
    for day, value in history:
        profile[day.weekday()] = value
    fallback = sum(value for _,value in history)/len(history)
    return [profile.get(day.weekday(),fallback) for day in targets]


def predict(series, today):
    completed = [row for row in series if date.fromisoformat(row['date']) < today]
    if len(completed) < 35:
        return {'ready':False,'days':len(completed),'required_days':35,
                'message':'Record at least 35 completed calendar days before forecasting. Try demo mode to explore a trained example.'}
    dates = [date.fromisoformat(row['date']) for row in completed]
    if any(dates[i]-dates[i-1] != timedelta(days=1) for i in range(1,len(dates))):
        raise ValueError('Forecast history must contain consecutive dates in ascending order.')
    sales = [row['net_minor']/100 for row in completed]
    split = len(dates)-7
    model = Ridge(alpha=1.0)
    model.fit(features(dates[:split],dates[0]),sales[:split])
    held_predictions = [max(0,float(x)) for x in model.predict(features(dates[split:],dates[0]))]
    held_baseline = baseline(list(zip(dates[:split],sales[:split])),dates[split:])
    model_mae = float(mean_absolute_error(sales[split:],held_predictions))
    base_mae = float(mean_absolute_error(sales[split:],held_baseline))
    selected = 'Ridge regression' if model_mae < base_mae else 'Same-weekday baseline'
    model.fit(features(dates,dates[0]),sales)
    future = [today+timedelta(days=i) for i in range(1,8)]
    forecasts = [max(0,float(x)) for x in model.predict(features(future,dates[0]))]
    base_future = baseline(list(zip(dates,sales)),future)
    selected_values = forecasts if selected == 'Ridge regression' else base_future
    return {'ready':True,'days':len(dates),'training_days':split,'holdout_days':7,
            'trained_through':dates[-1].isoformat(),'train_end':dates[split-1].isoformat(),
            'test_start':dates[split].isoformat(),'test_end':dates[-1].isoformat(),
            'model_mae_minor':round(model_mae*100),'baseline_mae_minor':round(base_mae*100),
            'selected_method':selected,'total_minor':round(sum(selected_values)*100),
            'future':[{'date':day.isoformat(),'ridge_minor':round(y*100),'baseline_minor':round(b*100),
                       'selected_minor':round(s*100)} for day,y,b,s in zip(future,forecasts,base_future,selected_values)],
            'holdout':[{'date':day.isoformat(),'actual_minor':round(y*100),'ridge_minor':round(p*100),
                        'baseline_minor':round(b*100)} for day,y,p,b in zip(dates[split:],sales[split:],held_predictions,held_baseline)],
            'note':'Net sales after discount, excluding tax. Today is excluded. Zero-bill dates count as zero sales; records must be complete. One holdout week is limited evidence, not a guarantee.'}
