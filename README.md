# cafe-billing

# Café Ledger — Café Billing and Sales Prediction System

Café Ledger is a web application that combines café billing, sales analysis, and basic machine learning. It helps staff create bills, review sales patterns, and estimate daily sales for the next seven days.

This project demonstrates how programming, databases, and machine learning can work together in a practical business application.

## Live Application

Website: https://cafe-billing-3.onrender.com

The application requires staff sign-in. Login credentials are configured privately through Render environment variables and are not included in this repository.

When demonstration mode is enabled, the application uses synthetic sales data. These records do not represent an actual café’s performance.

## What Has Been Built

## Billing and Menu Management

- Browse menu items by category or search by name.
- Add products to an order and adjust quantities.
- Apply a fixed discount and configurable tax.
- Record dine-in or takeaway orders.
- Record Cash, Card, or UPI as the payment method.
- Calculate and save bills.
- Display printable receipts.
- Add, edit, or deactivate menu items.
- Preserve original product names and prices on historical receipts.
- Prevent duplicate bills when the same checkout request is retried.

Payment methods are recorded for bookkeeping. The application does not collect or verify payments.

## Sales Analysis

- View daily net sales.
- Count completed bills.
- Calculate average bill value.
- Identify best-selling products by quantity.
- Filter reports by date.
- View recent bills and reopen receipts.
- Export daily sales reports as CSV files.

Net sales are calculated after discounts and before tax. Sales revenue is not the same as profit.

## Sales Prediction

- Prepare daily sales history from saved bills.
- Use time trend and weekday features.
- Train a Ridge regression model.
- Compare it with a simple same-weekday baseline.
- Evaluate predictions using Mean Absolute Error (MAE).
- Forecast daily net sales for the next seven days.
- Display both methods and highlight the method with lower error on the evaluation week.

## Technologies Used

| Technology | Purpose |
| Python | Backend logic, data processing, and machine learning |
| Flask | Web application framework and API routes |
| SQLite | Storage for menu items, bills, and bill items |
| HTML | Structure of the application screens |
| CSS | Responsive design and receipt print styling |
| JavaScript | Cart interactions, API requests, and charts |
| scikit-learn | Ridge regression and prediction evaluation |
| Waitress | Application server used for deployment |
| unittest | Automated testing |
| GitHub | Source-code hosting and version history |
| Render | Hosting the online application |
| Docker | Optional container-based deployment |

No external AI API key or GPU is required.

## How the Application Works

1. Staff select menu items and quantities in the browser.
2. JavaScript sends the order to the Flask backend.
3. The backend validates the order and reads current prices from SQLite.
4. Python calculates the subtotal, discount, tax, and total.
5. The bill and its items are saved in one database transaction.
6. The saved receipt is returned to the browser.
7. Sales reports aggregate the stored bills.
8. The forecasting module uses completed daily sales to estimate future sales.

The server calculates the authoritative bill amount rather than trusting prices submitted by the browser.

Money is stored in integer minor units. For example, ₹120.50 is stored as 12050 paise. This helps avoid floating-point rounding problems in billing.

## Machine Learning Approach

# Prediction Target

The model predicts daily net sales after discounts, excluding tax.

# Input Features

- A time trend representing the passage of days.
- Seven weekday indicators representing Monday through Sunday.

These features allow the model to learn simple sales trends and recurring weekly patterns.

# Model

The application uses Ridge regression, a form of linear regression that penalizes large coefficients.

It is suitable for this learning project because it is relatively simple to implement, evaluate, and explain.

# Training and Evaluation

1. Aggregate bills into a chronological daily sales series.
2. Fill dates without bills with zero sales.
3. Exclude the current day because its sales may be incomplete.
4. Require at least 35 completed calendar days of history.
5. Reserve the latest seven completed days for evaluation.
6. Train on the earlier dates.
7. Compare Ridge regression with a baseline using the most recently observed sales for the same weekday.
8. Calculate MAE for both methods.
9. Refit Ridge on all available completed history and forecast tomorrow through seven days after today.

The application uses at most the latest 730 completed days of history.

# What MAE Means

Mean Absolute Error measures the average absolute difference between predicted and actual sales.

For example, an MAE of ₹200 means predictions differed from actual sales by ₹200 per day on average during the evaluation period.

MAE is an amount, not an accuracy percentage.

# Forecast Limitations

- Forecasts are estimates, not guaranteed results.
- Missing sales records are treated as zero sales.
- The model assumes records are complete.
- Weather, festivals, promotions, stock shortages, and future closures are not included.
- One evaluation week is limited evidence of performance.
- Because that week is also used to select a method, it is not an independent final evaluation of the selected method.

Synthetic demonstration results do not establish accuracy for a real café.

## Deployment on Render

This project was deployed as a Python web service connected to GitHub.

Settings for this repository:

| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Branch | `main` |
| Root Directory | `cafe-ledger-github` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python serve.py` |
| Health Check Path | `/healthz` |

The `.python-version` file selects Python 3.12.

Configuration is supplied through Render environment variables, including:

- `CAFE_NAME`
- `CAFE_CURRENCY`
- `CAFE_TIMEZONE`
- `CAFE_TAX_PERCENT`
- `CAFE_DEMO`
- `CAFE_ADMIN_USER`
- `CAFE_ADMIN_PASSWORD`
- `PORT`

Public hosting requires a staff password of at least 16 characters. Store it in Render, not in GitHub.

The application can use Render’s automatically supplied public URL. Other hosting environments require the appropriate `APP_PUBLIC_URL` configuration.


## What Was Learned

Building this project provided practical experience with:

1. Breaking a business problem into billing, storage, reporting, and prediction features.
2. Writing Python functions, validation rules, and error handling.
3. Creating Flask routes and exchanging JSON between frontend and backend.
4. Building interactive interfaces with HTML, CSS, and JavaScript.
5. Designing relational tables and using SQL queries.
6. Using transactions to save related records together.
7. Handling money with integer units and explicit rounding.
8. Preventing duplicate records when requests are retried.
9. Aggregating transaction data into daily sales reports.
10. Preparing time-series data for machine learning.
11. Creating time and weekday features.
12. Training and evaluating a regression model.
13. Comparing machine learning with a simple baseline.
14. Avoiding future-data leakage during evaluation.
15. Writing automated tests for business rules.
16. Uploading source code to GitHub.
17. Configuring hosting, environment variables, and application start commands.
18. Troubleshooting deployment errors caused by incorrect root directories.
19. Understanding the difference between source-code visibility, website access, and staff authentication.
20. Recognizing the importance of persistent storage and backups.

## Current Scope and Future Improvements

This is an educational, single-café starter application.

Possible improvements include:

- Separate staff accounts and role-based permissions.
- Inventory and ingredient tracking.
- Refunds and bill corrections with audit records.
- Verified payment-gateway integration.
- Product-level demand forecasting.
- Holiday, promotion, and closure information.
- Evaluation across multiple historical periods.
- PostgreSQL support for larger deployments.
- Automated backup scheduling.

The application does not currently provide inventory management, payment processing, refunds, or certified tax invoicing.
