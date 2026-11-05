# Bizlytics

Bizlytics is a Streamlit dashboard for exploring business performance using Pandas, NumPy, and Plotly. It includes a fictional sample business dataset, CSV/Excel upload, data-quality checks, editable column mapping, interactive filtering, rule-based insights, and CSV, Excel, and PDF reports.

## Requirements

- Python 3.11 or newer
- pip

Pandas and NumPy are pinned to compatible official wheels tested with Python 3.12.10. For repeatable cloud deployments, select Python 3.12 in the Streamlit Community Cloud app settings.

## Install

In PowerShell, from the project directory:

```powershell
python -m venv .venv-compatible
.\.venv-compatible\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents environment activation, use the environment's Python directly:

```powershell
.\.venv-compatible\Scripts\python.exe -m pip install -r requirements.txt
```

## Run Bizlytics

With the environment activated:

```powershell
streamlit run app.py
```

Or without activation:

```powershell
.\.venv-compatible\Scripts\python.exe -m streamlit run app.py
```

The app loads fictional sample data by default. Choose **Upload a file** in the sidebar for a CSV or XLSX workbook. The currency selector controls display formatting only; it does not convert values.

## Explore and validate data

- Confirm automatically suggested date, revenue, expenses, product, and category fields or map them to other source columns. Original headers and values are retained.
- Review detected column types, missing values (including blank cells), duplicate rows, invalid dates, and invalid numeric values.
- Filter dashboard metrics and charts by date, categorical values, text search for high-cardinality fields, and numeric ranges.
- Inspect, sort, choose columns, and download the filtered table as CSV.
- Read rule-based comparisons for revenue, monthly profit margins, expenses, leading revenue categories, and data-quality warnings. Insights describe available data and do not forecast.

## Reports and exports

The **Insights & reports** page offers:

- UTF-8 CSV export of filtered records.
- An Excel workbook with records, summary metrics, insights, and a data-quality sheet.
- An in-memory PDF report with dataset name, reporting period, available metrics, insights, quality warnings, and an optional category-revenue chart.

## Run tests

```powershell
.\.venv-compatible\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv-compatible\Scripts\python.exe -m pytest -q
```

## Deploy to Streamlit Community Cloud

1. Push the project to a GitHub repository you control.
2. In Streamlit Community Cloud, create an app from that repository.
3. Set the app's main file to `app.py` and select Python 3.12.
4. Keep `requirements.txt` at the repository root. Community Cloud installs the application dependencies from this file.

Commit `app.py`, `requirements.txt`, `README.md`, `modules/`, and `data/sample_business_data.csv`. The sample CSV is required for the default dashboard. The `tests/` folder is useful for maintenance but isn't needed to run the deployed app. Do not commit virtual environments, caches, uploaded customer data, `.env` files, or Streamlit secrets.

## Phase 2 scope

This version includes the original Phase 1 dashboard and sample data, plus upload validation and mapping, advanced exploration, rule-based insights, and CSV/Excel/PDF reports. Authentication, databases, external company APIs, forecasting, and automated predictive insights remain out of scope.
