import re

import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "revenue": {"revenue", "sales", "total_revenue", "total_sales"},
    "expenses": {"expense", "expenses", "total_expense", "total_expenses"},
    "units": {"units", "unit", "units_sold", "quantity", "qty"},
    "date": {"date", "datetime", "timestamp", "transaction_date", "sale_date"},
    "product": {"product", "product_name", "item"},
    "category": {"category", "product_category"},
    "profit": {"profit", "net_profit"},
}


def _normalize_column(column):
    return re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_")


def find_column(data, field):
    """Return a recognized column for a known field, or None."""
    mapped_fields = data.attrs.get("bizlytics_column_mapping", {})
    if field in mapped_fields:
        mapped = mapped_fields[field]
        return mapped if mapped in data.columns else None
    aliases = COLUMN_ALIASES.get(field, {field})
    for column in data.columns:
        if _normalize_column(column) in aliases:
            return column
    return None


def get_date_column(data):
    return find_column(data, "date")


def _numeric_series(data, column):
    return pd.to_numeric(data[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _sum_column(data, column):
    values = _numeric_series(data, column).dropna()
    return float(values.sum()) if not values.empty else None


def _best_performer(data, field, revenue_column):
    column = find_column(data, field)
    if column is None or revenue_column is None:
        return None
    work = pd.DataFrame(
        {
            "name": data[column].astype("string"),
            "revenue": _numeric_series(data, revenue_column),
        }
    ).dropna()
    if work.empty:
        return None
    totals = work.groupby("name", dropna=True)["revenue"].sum()
    if totals.empty:
        return None
    name = str(totals.idxmax())
    return name, float(totals.max())


def _revenue_growth(data, revenue_column, date_column):
    if revenue_column is None or date_column is None:
        return None
    work = pd.DataFrame(
        {
            "date": pd.to_datetime(data[date_column], errors="coerce"),
            "revenue": _numeric_series(data, revenue_column),
        }
    ).dropna()
    if work.empty:
        return None
    work["period"] = work["date"].dt.to_period("M")
    totals = work.groupby("period")["revenue"].sum().sort_index()
    if len(totals) < 2:
        return None
    previous, current = totals.iloc[-2], totals.iloc[-1]
    if previous == 0:
        return None
    return float((current - previous) / abs(previous) * 100)


def _period_comparisons(data, revenue_column, expense_column, units_column, date_column):
    if date_column is None:
        return {}
    dates = pd.to_datetime(data[date_column], errors="coerce")
    if dates.notna().sum() < 2:
        return {}

    def values_for(column):
        if column:
            return _numeric_series(data, column)
        return pd.Series(np.nan, index=data.index)

    monthly_data = pd.DataFrame(
        {
            "period": dates.dt.to_period("M"),
            "revenue": values_for(revenue_column),
            "expenses": values_for(expense_column),
            "units": values_for(units_column),
        }
    ).dropna(subset=["period"])
    if monthly_data.empty:
        return {}
    monthly = monthly_data.groupby("period").agg(
        revenue=("revenue", lambda values: values.sum(min_count=1)),
        expenses=("expenses", lambda values: values.sum(min_count=1)),
        units=("units", lambda values: values.sum(min_count=1)),
        revenue_records=("revenue", "count"),
    ).sort_index()
    comparisons = {}

    def percentage_change(series):
        series = series.dropna()
        if len(series) < 2 or series.iloc[-2] == 0:
            return None
        return float((series.iloc[-1] - series.iloc[-2]) / abs(series.iloc[-2]) * 100)

    for metric in ("revenue", "expenses", "units"):
        if monthly[metric].notna().sum() >= 2:
            comparisons[metric] = percentage_change(monthly[metric])

    if revenue_column and expense_column:
        monthly["profit"] = monthly["revenue"] - monthly["expenses"]
        monthly["margin"] = (
            monthly["profit"] / monthly["revenue"] * 100
        ).where(monthly["revenue"] != 0)
        if monthly["profit"].notna().sum() >= 2:
            comparisons["profit"] = percentage_change(monthly["profit"])
        margins = monthly["margin"].dropna()
        if len(margins) >= 2:
            comparisons["margin"] = float(margins.iloc[-1] - margins.iloc[-2])

    if revenue_column:
        monthly["average_revenue"] = monthly["revenue"] / monthly["revenue_records"]
        if monthly["average_revenue"].notna().sum() >= 2:
            comparisons["average_revenue"] = percentage_change(monthly["average_revenue"])
    return comparisons


def analyze_business_data(data):
    """Calculate financial metrics only from recognized, numeric data columns."""
    revenue_column = find_column(data, "revenue")
    expense_column = find_column(data, "expenses")
    units_column = find_column(data, "units")
    date_column = get_date_column(data)

    revenue = _sum_column(data, revenue_column) if revenue_column else None
    expenses = _sum_column(data, expense_column) if expense_column else None
    units_sold = _sum_column(data, units_column) if units_column else None
    revenue_values = (
        _numeric_series(data, revenue_column).dropna()
        if revenue_column
        else pd.Series(dtype=float)
    )
    average_revenue = float(revenue_values.mean()) if not revenue_values.empty else None
    if revenue is None:
        profit = None
        margin = None
    elif expenses is None:
        profit = None
        margin = None
    else:
        profit = revenue - expenses
        margin = float(profit / revenue * 100) if revenue != 0 else None

    availability = {
        "revenue": "Calculated from the recognized revenue column." if revenue is not None else "Unavailable: add a recognized revenue or sales column with numeric values.",
        "expenses": "Calculated from the recognized expense column." if expenses is not None else "Unavailable: add a recognized expenses column with numeric values.",
        "profit": "Revenue minus expenses." if profit is not None else "Unavailable: both recognized revenue and expenses columns are required.",
        "margin": "Net profit divided by revenue." if margin is not None else "Unavailable: profit requires revenue and expenses, and revenue must be non-zero.",
        "units": "Calculated from the recognized units-sold or quantity column." if units_sold is not None else "Unavailable: add a recognized units-sold or quantity column with numeric values.",
        "average_revenue": "Average revenue per record with a numeric revenue value." if average_revenue is not None else "Unavailable: add a recognized revenue or sales column with numeric values.",
        "growth": "Unavailable: two dated monthly periods with revenue are required, and the previous period must be non-zero.",
    }
    growth = _revenue_growth(data, revenue_column, date_column)
    if growth is not None:
        availability["growth"] = "Compared the most recent available month with the previous available month."

    return {
        "total_revenue": revenue,
        "total_expenses": expenses,
        "total_units_sold": units_sold,
        "average_revenue": average_revenue,
        "net_profit": profit,
        "profit_margin": margin,
        "revenue_growth": growth,
        "period_comparisons": _period_comparisons(
            data, revenue_column, expense_column, units_column, date_column
        ),
        "best_product": _best_performer(data, "product", revenue_column),
        "best_category": _best_performer(data, "category", revenue_column),
        "availability": availability,
    }


def filter_data(data, date_range=None, selections=None):
    """Apply optional date, categorical, and numeric range filters."""
    filtered = data.copy()
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        date_column = get_date_column(filtered)
        if date_column:
            dates = pd.to_datetime(filtered[date_column], errors="coerce")
            start = pd.Timestamp(date_range[0])
            end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
            filtered = filtered.loc[dates.between(start, end, inclusive="both")]

    selections = selections or {}
    for field, selected in selections.items():
        column = field if field in filtered.columns else find_column(filtered, field)
        if column and selected is not None:
            if isinstance(selected, dict) and "contains" in selected:
                filtered = filtered.loc[
                    filtered[column].astype(str).str.contains(
                        str(selected["contains"]), case=False, na=False, regex=False
                    )
                ]
                continue
            selected_values = {str(value) for value in selected}
            filtered = filtered.loc[filtered[column].astype(str).isin(selected_values)]
    return filtered.copy()


def filter_data_by_ranges(data, ranges=None):
    """Filter numeric columns to inclusive bounds without modifying source data."""
    filtered = data.copy()
    for column, bounds in (ranges or {}).items():
        if column in filtered.columns and bounds and len(bounds) == 2:
            values = _numeric_series(filtered, column)
            filtered = filtered.loc[values.between(bounds[0], bounds[1], inclusive="both")]
    return filtered.copy()
