import numpy as np
import pandas as pd

from modules.analytics import analyze_business_data, find_column, get_date_column


def _monthly_totals(data, column, date_column):
    if not column or not date_column:
        return pd.Series(dtype=float)
    values = pd.DataFrame(
        {
            "date": pd.to_datetime(data[date_column], errors="coerce"),
            "amount": pd.to_numeric(data[column], errors="coerce"),
        }
    ).dropna()
    if values.empty:
        return pd.Series(dtype=float)
    values["period"] = values["date"].dt.to_period("M")
    return values.groupby("period")["amount"].sum().sort_index()


def generate_insights(data, metrics=None, quality=None, currency_symbol="$"):
    """Create grounded, descriptive insights from available data only."""
    metrics = metrics or analyze_business_data(data)
    insights = []
    revenue_column = find_column(data, "revenue")
    expense_column = find_column(data, "expenses")
    date_column = get_date_column(data)

    growth = metrics.get("revenue_growth")
    if growth is not None:
        direction = "grew" if growth > 0 else "declined" if growth < 0 else "was unchanged"
        insights.append(
            {
                "type": "positive" if growth >= 0 else "warning",
                "title": "Revenue movement",
                "detail": (
                    f"Revenue {direction} by {abs(growth):.1f}% between the two most recent "
                    "available months in the selected data."
                ),
            }
        )
    elif revenue_column:
        insights.append(
            {
                "type": "neutral",
                "title": "Revenue comparison unavailable",
                "detail": metrics["availability"]["growth"],
            }
        )

    if expense_column and date_column:
        expenses = _monthly_totals(data, expense_column, date_column)
        if len(expenses) >= 2:
            previous, current = float(expenses.iloc[-2]), float(expenses.iloc[-1])
            if previous != 0:
                change = (current - previous) / abs(previous) * 100
                direction = "increased" if change > 0 else "decreased" if change < 0 else "were unchanged"
                insights.append(
                    {
                        "type": "warning" if change > 0 else "positive",
                        "title": "Expense movement",
                        "detail": (
                            f"Expenses {direction} by {abs(change):.1f}% from "
                            f"{expenses.index[-2]} to {expenses.index[-1]}."
                        ),
                    }
                )

    if revenue_column and expense_column and date_column:
        revenue_by_month = _monthly_totals(data, revenue_column, date_column)
        expenses_by_month = _monthly_totals(data, expense_column, date_column)
        common_periods = revenue_by_month.index.intersection(expenses_by_month.index).sort_values()
        if len(common_periods) >= 2:
            margins = []
            for period in common_periods[-2:]:
                revenue = float(revenue_by_month.loc[period])
                expenses = float(expenses_by_month.loc[period])
                margins.append((revenue - expenses) / revenue * 100 if revenue != 0 else None)
            if all(margin is not None for margin in margins):
                change = margins[-1] - margins[-2]
                direction = "increased" if change > 0 else "decreased" if change < 0 else "was unchanged"
                insights.append(
                    {
                        "type": "positive" if change >= 0 else "warning",
                        "title": "Profit margin movement",
                        "detail": (
                            f"Monthly profit margin {direction} by {abs(change):.1f} percentage "
                            f"points between the two latest comparable months "
                            f"({margins[-2]:.1f}% to {margins[-1]:.1f}%)."
                        ),
                    }
                )

    if expense_column:
        amounts = pd.to_numeric(data[expense_column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        if len(amounts) >= 4:
            lower_quartile, upper_quartile = amounts.quantile([0.25, 0.75])
            spread = upper_quartile - lower_quartile
            if spread > 0:
                upper_bound = upper_quartile + 1.5 * spread
                lower_bound = lower_quartile - 1.5 * spread
                unusual = amounts[(amounts > upper_bound) | (amounts < lower_bound)]
                if not unusual.empty:
                    insights.append(
                        {
                            "type": "warning",
                            "title": "Unusual expense values",
                            "detail": (
                                f"{len(unusual)} expense record(s) fall outside the 1.5×IQR "
                                f"range ({currency_symbol}{lower_bound:,.2f} to {currency_symbol}{upper_bound:,.2f}). "
                                "Review these records; this is a statistical flag, not proof of an error."
                            ),
                        }
                    )

    category_column = find_column(data, "category")
    if revenue_column and category_column:
        grouped = pd.DataFrame(
            {
                "category": data[category_column].astype("string"),
                "revenue": pd.to_numeric(data[revenue_column], errors="coerce"),
            }
        ).dropna().groupby("category")["revenue"].sum().sort_values(ascending=False)
        total = grouped.sum()
        if not grouped.empty and total > 0:
            category, value = grouped.index[0], float(grouped.iloc[0])
            share = value / total * 100
            insights.append(
                {
                    "type": "neutral",
                    "title": "Largest revenue category",
                    "detail": (
                        f"{category} contributed {currency_symbol}{value:,.2f}, or {share:.1f}% of "
                        "the summed revenue across categories in the selected data."
                    ),
                }
            )

    product_column = find_column(data, "product")
    if revenue_column and product_column:
        product = metrics.get("best_product")
        if product:
            insights.append(
                {
                    "type": "positive",
                    "title": "Leading product",
                    "detail": (
                        f"{product[0]} generated the most revenue "
                        f"({currency_symbol}{product[1]:,.2f}) in the selected data."
                    ),
                }
            )
            insights.append(
                {
                    "type": "neutral",
                    "title": "Action to consider",
                    "detail": (
                        f"Review pricing and customer demand for {product[0]} before making "
                        "product investment decisions; it is the current revenue leader."
                    ),
                }
            )

    if revenue_column and expense_column and category_column:
        category_totals = pd.DataFrame(
            {
                "category": data[category_column].astype("string"),
                "revenue": pd.to_numeric(data[revenue_column], errors="coerce"),
                "expenses": pd.to_numeric(data[expense_column], errors="coerce"),
            }
        ).dropna()
        if not category_totals.empty:
            category_totals = category_totals.groupby("category")[["revenue", "expenses"]].sum()
            loss_making = category_totals.loc[
                category_totals["expenses"] > category_totals["revenue"]
            ].sort_values("expenses", ascending=False)
            if not loss_making.empty:
                category = str(loss_making.index[0])
                revenue = float(loss_making.iloc[0]["revenue"])
                expenses = float(loss_making.iloc[0]["expenses"])
                insights.append(
                    {
                        "type": "warning",
                        "title": "Category needs attention",
                        "detail": (
                            f"{category} has {currency_symbol}{expenses:,.2f} in expenses "
                            f"against {currency_symbol}{revenue:,.2f} in revenue in the selected "
                            "records. Review its costs and pricing."
                        ),
                    }
                )

    quality = quality or {}
    issue_count = (
        sum(quality.get("missing_values", {}).values())
        + quality.get("duplicate_rows", 0)
        + sum(quality.get("invalid_dates", {}).values())
        + sum(quality.get("invalid_numeric", {}).values())
    )
    if issue_count:
        insights.append(
            {
                "type": "warning",
                "title": "Data quality may affect results",
                "detail": (
                    f"The quality check found {issue_count} issue(s), including missing, "
                    "duplicate, or invalid values. Review the data-quality panel before relying on totals."
                ),
            }
        )
    elif quality:
        insights.append(
            {
                "type": "positive",
                "title": "Data quality check",
                "detail": "No missing values, duplicate rows, invalid dates, or invalid numeric values were detected.",
            }
        )

    if not insights:
        insights.append(
            {
                "type": "neutral",
                "title": "More data needed",
                "detail": "Available columns and records do not support a reliable business comparison yet.",
            }
        )
    return insights
