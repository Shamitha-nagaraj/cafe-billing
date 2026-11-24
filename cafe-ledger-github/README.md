# Café Ledger — billing and sales forecasting

A beginner-friendly Python project that turns a café order into a saved, printable bill and uses past daily sales to predict the next seven days. Built with Flask, SQLite, HTML, CSS, JavaScript, and scikit-learn. No OpenAI account or API key is required.

## What you will build

- A responsive point-of-sale screen with a menu, search, categories, quantities, discounts, configurable tax, and recorded payment method.
- Bills calculated on the server using integer minor units (paise for INR), saved transactionally in SQLite, with printable receipts and duplicate-submission protection.
- A sales dashboard with daily net sales, completed bills, average bill value, best-selling items, and CSV export.
- A seven-day sales forecast using Ridge regression, with a chronological holdout evaluation and a same-weekday baseline.
- A separate, clearly labeled demonstration mode with synthetic history. Demo and real databases never mix.

This is a learning/single-café starter. Recording Cash/Card/UPI does **not** collect or verify a payment. A printed bill is not automatically a legally compliant tax invoice. Tax defaults to 0%; configure it with your accountant. Forecasts are estimates, not guaranteed sales or profit predictions.

## 1. Install and run locally

Install Python 3.11 or 3.12 (the versions used in CI). In PowerShell, open this project's folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:8080**. The real register starts with an example menu and no sales. The SQLite database is created automatically in `instance/cafe.sqlite3`.

For macOS/Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

To try a complete dashboard immediately, stop the server with Ctrl+C and run:

```powershell
.\.venv\Scripts\python.exe app.py --demo
```

Demo mode uses `instance/demo.sqlite3`, with 90 days of reproducible synthetic sales. A visible banner identifies demo mode. Every bill created there is also a demo bill. Restart without `--demo` to return to the real register. The CSV in `data/sample_daily_sales.csv` is a teaching dataset, not your café's sales.

## 2. Make your first bill

1. Open Register. Search or select a category and click menu items.
2. Adjust quantities in the cart. Choose dine-in/takeaway and a payment method.
3. Enter an optional fixed discount. Preview the subtotal, discount, tax, and total.
4. Click **Complete bill** only after collecting payment outside this application.
5. The backend recalculates and saves the bill. Print its receipt or start another bill.
6. Open Sales & forecast to see the updated totals. Reopen receipts from recent bills.

Use **Manage menu** to add items, update names/prices, or deactivate items. Historical receipts keep their original names and prices. New bills use current menu prices.

## 3. Understand the programming

| Layer | Technology | Responsibility |
|---|---|---|
| Page structure | HTML | Forms, navigation, cart, receipt, dashboard |
| Design | CSS | Mobile layout, typography, print layout |
| Browser behavior | JavaScript | Cart, API calls, charts, validation feedback |
| Backend | Python + Flask | Routes, authoritative billing, authentication, exports |
| Storage | SQLite / SQL | Menu, bills, bill items, settings |
| Machine learning | scikit-learn Ridge regression | Predict next week's daily net sales |
| Hosting server | Waitress | Serve the Flask application outside development |
| Version control | Git / GitHub | Track source changes and share the project |

Flow: browser cart → POST `/api/bills` → server validates menu and amounts → one SQLite transaction saves bill and items → receipt JSON → browser prints. The browser never decides the authoritative price or total.

Money is stored as integers: ₹120.50 becomes 12050 paise. Discount is subtracted before tax. Tax is rounded half-up to the nearest minor unit. Sales/forecasting uses **net sales after discount, excluding tax**, not profit. Average bill value uses the paid total including tax.

## 4. Understand the basic machine learning

**Supervised learning** learns a relationship between input features X and known targets y. Here X contains a time trend and weekday indicators; y is daily net sales. Ridge is linear regression with a penalty that reduces extreme coefficients. The penalty is fixed at 1.0; the app does not tune hyperparameters against its test set.

1. Aggregate saved bills into a chronological daily series, using at most the latest 730 completed days.
2. Fill dates with no bills with zero. This assumes recording is complete; missing records are not automatically known to be closures. Closed days are treated as zero sales, not removed.
3. Exclude the current, incomplete day from training.
4. Require at least 35 completed calendar days of history.
5. Reserve the latest 7 completed days as a test set. Train only on earlier days.
6. Compare predictions with actual sales using **MAE** (mean absolute error), expressed in your currency.
7. Compare the model with a simple baseline: each day repeats sales from the same weekday one week earlier.
8. Refit on all completed history and forecast the next 7 days after today. Both Ridge and baseline forecasts remain visible; the holdout winner is highlighted as the suggested starter forecast.

No future sales enter training features. A small MAE is better, but one week's test is limited evidence, and using it to choose a method means it is not an independent final evaluation. There is no invented accuracy percentage or confidence interval. The model does not know weather, promotions, festivals, stockouts, holidays, or future closures. Negative predictions are clipped to zero. Re-evaluate over multiple periods before operational use.

Read `cafe/forecast.py` and `docs/LEARNING.md` for the implementation. Training runs locally/on your server; no sales are sent to an AI provider.

## 5. Configuration

Copy `.env.example` to `.env` and edit it. Environment variables override `.env`. Restart after configuration changes.

| Variable | Default | Purpose |
|---|---|---|
| `CAFE_NAME` | Café Ledger | Name printed on receipts |
| `CAFE_CURRENCY` | INR | Three-letter currency code; use a currency with 2 decimal places |
| `CAFE_TIMEZONE` | Asia/Kolkata | Business day used for sales and training |
| `CAFE_TAX_PERCENT` | 0 | Percentage added after discount; no tax-law assumption |
| `CAFE_DATA_DIR` | instance | Persistent SQLite directory |
| `CAFE_DEMO` | 0 | 1 chooses a separate demonstration database |
| `CAFE_ADMIN_USER` | admin | Username for optional local / required public Basic authentication |
| `CAFE_ADMIN_PASSWORD` | empty | Password; public hosting requires at least 16 characters |
| `APP_PUBLIC_URL` | empty | Exact public HTTPS origin; Render URL is a fallback |
| `PORT` | 8080 | Hosted listening port; locally use `app.py --port 8081` to change it |

Currency is fixed for an existing database. Changing its code does not convert historical money; create a separate database for a different currency. Tax changes affect new bills only. Never commit `.env`, live databases, or private exports to GitHub. The supplied package excludes them.

## 6. Upload to GitHub without the earlier folder problem

1. Generate a clean package with `python package_project.py`, then extract `dist/cafe-ledger-github.zip`.
2. Sign in at https://github.com/new. Create a repository named `cafe-billing-forecast`; Private is a good starting choice. Leave README, .gitignore, and license initialization off because files are already supplied.
3. On the empty repository page choose **uploading an existing file**, or **Add file → Upload files**.
4. Open the extracted folder. Select its **contents**, including the `cafe`, `static`, `templates`, `tests`, `docs`, and `data` folders. Drag them into GitHub. Do not upload the ZIP or an extra outer folder.
5. Enter `Initial cafe billing and forecast project` and commit to `main`.
6. Confirm that `app.py`, `requirements.txt`, `README.md`, and `serve.py` appear immediately on the repository's Code page. Open `cafe` and confirm its Python modules are inside.
7. The GitHub repository is the source-code location. GitHub Pages cannot run this Flask/SQLite backend.

## 7. Deploy, only if you want an online staff app

Follow `docs/DEPLOYMENT.md`. This app stores bills, so it needs **persistent storage**, HTTPS, and staff authentication. A host's temporary filesystem is not safe for real sales. Start with a local demonstration if you do not want a paid persistent-storage plan.

For a Python host: build `pip install -r requirements.txt`, start `python serve.py`, health path `/healthz`. Keep Root Directory blank when the upload layout matches step 6. The included Dockerfile is an alternative. Do not run the Flask development server publicly.

The online app is for authorized staff, not an anonymous public billing dashboard. Basic authentication is a starter control; add proper user accounts/roles and audit logs for a real team. A consistent database backup utility is included; see the deployment guide before recording real sales.

## 8. Tests and project map

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use temporary databases. They cover money rounding, invalid orders, transactions, duplicate submissions, historical prices, reporting, authorization, and chronological forecasts. GitHub Actions runs them on pushes and pull requests. Software tests do not establish forecast accuracy on your real café.

```text
README.md                    Start here
app.py                       Local launcher
serve.py                     Public Waitress launcher
requirements.txt             Runtime dependencies
cafe/__init__.py             Flask app and routes
cafe/config.py               Environment parsing
cafe/database.py             SQLite schema and demo data
cafe/billing.py              Authoritative invoice calculations
cafe/analytics.py            Sales reports and aggregates
cafe/forecast.py             Ridge model and chronological evaluation
templates/index.html         App shell
static/app.js                Browser behavior
static/styles.css            Responsive and print styles
data/sample_daily_sales.csv  Clearly synthetic learning data
tests/                       Automated tests
docs/LEARNING.md              Beginner explanation
docs/DEPLOYMENT.md            Hosting and persistent-storage guide
package_project.py           Clean, allowlisted GitHub ZIP
train_sample.py              Train/evaluate the standalone teaching CSV
backup_database.py           Consistent private SQLite backup
Dockerfile                   Optional container deployment
.github/workflows/tests.yml   Continuous integration
```

## 9. Suggested learning sequence

Learn Python functions and dictionaries → HTML/CSS forms → JavaScript events and fetch → Flask routes and HTTP → SQL tables/transactions → integer-money calculations → chronological data analysis → regression and MAE → tests → Git/GitHub → hosting and backups. First change a menu item, create a bill, inspect the saved rows, and trace the forecast feature construction.

Not included yet: inventory deduction, supplier management, payment gateway, refunds/voids, multiple outlets, customer accounts, certified invoicing, or trained product-level demand predictions. Add those as separate features with tests; never silently delete paid bills to correct mistakes.

Sources: [Flask](https://flask.palletsprojects.com/en/stable/), [SQLite integration](https://flask.palletsprojects.com/en/stable/tutorial/database/), [Ridge regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), [chronological evaluation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), [GitHub uploads](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).
