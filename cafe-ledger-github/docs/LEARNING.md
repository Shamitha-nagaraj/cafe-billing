# Build Café Ledger from the basics

Start with the root README for installation. This document explains the ideas and the order in which to build a similar project yourself. You can use the supplied code as a reference while implementing each step.

## 1. What problem are we solving?

A café sells drinks and food. Staff need to record the correct quantities and prices, save a receipt, and understand which days and products sell well. A small model can estimate upcoming daily revenue from recorded history.

There are two related parts:

- **Billing is ordinary programming:** deterministic arithmetic, validation, and database transactions. It does not need machine learning.
- **Forecasting is basic supervised machine learning:** learn from daily sales and evaluate predictions against days the model has not seen during training.

Predicting revenue is different from predicting profit, stock requirements, or demand for each item. This project predicts total daily net sales only.

## 2. Applications and tools

| Tool | Why you need it | Required? |
|---|---|---|
| Python 3.11 or 3.12 | Runs the backend, tests, and model | Yes |
| A browser such as Chrome or Edge | Uses and tests the app | Yes |
| VS Code or another text editor | Reads and changes source files | Recommended |
| PowerShell / terminal | Runs installation and project commands | Yes |
| pip | Installs Python libraries; comes with Python | Yes |
| SQLite | Stores menu and bills; Python includes its driver | Automatic |
| GitHub account | Stores/shares source code and runs CI | For uploading |
| Git / GitHub Desktop | Tracks changes and simplifies later updates | Optional for browser upload |
| Railway, Render, or a server with a persistent disk | Runs an online version | Only for hosting |
| Docker | Builds a portable server image | Optional |

No MySQL installation, Excel, paid AI API, GPU, or separately trained neural network is needed.

## 3. Programming concepts to learn

### Python

Learn variables, strings, numbers, lists, dictionaries, functions, imports, exceptions, and file paths. For example, a cart item is a dictionary `{'id': 1, 'quantity': 2}` and a cart is a list of those dictionaries. Functions split the work into reusable steps.

`app.py` starts the local server. `cafe/__init__.py` creates the Flask app and connects web addresses to Python functions. `cafe/billing.py` contains order validation and calculations. Keeping these responsibilities separate makes fixes and tests easier.

### HTML, CSS, and JavaScript

HTML defines the page elements. CSS makes the page readable on a phone and styles printed receipts. JavaScript handles clicks, maintains a temporary cart, requests data from the backend, and updates the screen.

The browser uses `fetch('/api/menu')` to request a JSON menu. JSON is a structured text format shared by Python and JavaScript. A `POST /api/bills` request sends a new order. `GET /api/analytics` retrieves a report. HTTP status codes describe outcomes: 201 means created, 400 invalid input, 401 authentication needed, and 409 a conflicting request.

### SQL and databases

The four tables are:

| Table | Example fields | Purpose |
|---|---|---|
| menu | id, name, category, price_minor, active | Current products |
| bills | id, business_date, subtotal_minor, tax_minor, total_minor | One row per saved bill |
| bill_items | bill_id, menu_id, name, quantity, unit_price_minor | Products and historical prices on each bill |
| metadata | key, value | Currency, timezone, mode, demo initialization |

A primary key identifies one row. A foreign key connects a bill item to its bill. A transaction saves the bill and all its lines together: either all succeed or all are rolled back. SQL placeholders (`?`) keep values separate from SQL statements.

Try this read-only query with a SQLite viewer on a backup of the demo database:

```sql
SELECT business_date,
       SUM(subtotal_minor - discount_minor) / 100.0 AS net_sales
FROM bills
GROUP BY business_date
ORDER BY business_date;
```

## 4. Implement the billing flow

1. Define a menu and create the SQLite schema. Seed example products only when the menu is empty.
2. Build a page that reads `/api/menu` and displays product buttons.
3. Store selected product IDs and quantities in the browser cart.
4. Send IDs, quantities, discount, payment method, order type, and a unique request ID to the server.
5. Validate every value on the server. Read authoritative prices from the database instead of accepting browser prices.
6. Calculate subtotal, discount, tax, and total in integer minor units.
7. Save the bill and copied line-item names/prices in one transaction.
8. Return the saved receipt and render it in the browser. Print using the browser's print dialog.

Example with a **hypothetical configured tax**, not a tax recommendation:

```text
2 coffees at ₹150.00 = ₹300.00 subtotal
Discount             =  ₹20.00
Net sales            = ₹280.00
Configured 5% tax    =  ₹14.00
Collected total      = ₹294.00
```

Store ₹150.00 as `15000`. This avoids common floating-point money errors. Tax is rounded half-up to a minor unit. The sales forecast uses ₹280.00 from the example, while the average bill calculation uses ₹294.00.

Duplicate clicks and connection failures are common in billing software. Each order has a UUID. A retry with the same UUID and contents returns the existing receipt. The browser saves an unresolved request in session storage and locks its cart until the same request succeeds. Keep the tab open when resolving an uncertain save. Closing the browser can clear session storage; if that happens, check recent bills before recording the order again. This is not an offline POS.

## 5. Implement sales analysis before machine learning

First make reliable reports: sum daily net sales, count saved bills, calculate average collected amount, and group item quantities for best sellers. Check that daily totals match individual receipts.

Keep absent dates in the series. In this starter, no recorded bills means zero sales. This is appropriate only if records are complete. An unrecorded busy day and a genuinely closed day cannot be distinguished automatically. Correct your source data and record closure information before extending the model.

## 6. Understand the model

The target `y` is one day's net sales. Inputs `X` are:

- Time trend: number of days since the first training date divided by 30.
- Seven weekday flags: Monday through Sunday, each 0 or 1.

For example, a Tuesday 30 days after the origin has `[1.0, 0, 1, 0, 0, 0, 0, 0]`. Scaling the trend keeps it in a reasonable numerical range.

Ridge regression fits a weighted sum of features plus an intercept. It also penalizes large coefficients (`alpha=1.0`). It is a good small teaching model because its inputs and limitations are understandable.

```python
from sklearn.linear_model import Ridge

model = Ridge(alpha=1.0)
model.fit(X_train, y_train)
predicted_sales = model.predict(X_test)
```

Those three lines are only the fitting step. Preparing dates and evaluating honestly are equally necessary.

### Evaluate in time order

For 90 completed days, use the first 83 to train and the last 7 to test. Do not randomly split a time series, and do not include today's incomplete sales. The application limits history to the most recent 730 completed days for a small, predictable training workload.

MAE is the average absolute difference between prediction and actual sales. If errors are ₹100, ₹200, and ₹300, MAE is ₹200 per day. It is an amount, not an accuracy percentage.

Compare Ridge with a baseline that repeats the most recently observed sales for the same weekday. For the consecutive seven-day test window this is the preceding week's corresponding day. A sophisticated model must earn its place by improving on a simple estimate.

The app selects the lower-MAE method on this one holdout week, then refits Ridge on all completed history. It forecasts tomorrow through seven days after today. Both methods remain visible. Because this holdout is used for selection, its score is not an independent estimate of the chosen method's future performance. Use rolling historical test windows and a later untouched evaluation period before relying on it operationally.

### Try the model without the web app

```powershell
.\.venv\Scripts\python.exe train_sample.py
```

This reads `data/sample_daily_sales.csv`, prints test MAEs and seven forecast rows, and writes no database. The CSV is explicitly synthetic INR data dated January–March 2026. It is a separate teaching example; the interactive demo generates its own 90-day bill history relative to its first initialization date.

## 7. Test your work

Run `python -m unittest discover -s tests -v` from the project folder. The supplied tests cover the business rules rather than merely checking that a page opens. Particularly useful examples verify that invalid orders leave no partial records, retries create one bill, changed menu prices do not change old receipts, and changed test targets do not alter predictions produced without those targets.

Try these manual checks too:

1. Create a two-item demo bill with a discount and reopen its receipt.
2. Change a menu price, then verify the old receipt is unchanged.
3. Check that dashboard totals increase by the saved bill amount.
4. Download CSV and inspect dates, currency, and the demo label.
5. Resize the browser to a phone width and print a receipt to PDF.

## 8. GitHub and deployment are different

Git tracks source versions. GitHub hosts your repository. A Python hosting service runs your code, provides HTTPS, and exposes a website URL. The repository URL is not the running app's URL. GitHub Pages serves static files and cannot run this backend.

Read the root README for exact upload instructions, then `DEPLOYMENT.md` for hosting. Your SQLite sales database belongs in private persistent storage, not in your GitHub repository.

## 9. Sensible next extensions

After understanding the existing flow, add refunds with reversal records, staff accounts and roles, daily closure tracking, stock deduction, product-level demand, and rolling model evaluation. Each change needs corresponding validation and tests. Connect a payment gateway only after implementing verified server-side payment callbacks and reconciliation.

References: [Flask tutorial](https://flask.palletsprojects.com/en/stable/tutorial/), [Python tutorial](https://docs.python.org/3/tutorial/), [SQLite transactions](https://docs.python.org/3/library/sqlite3.html), [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), [time-series evaluation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
