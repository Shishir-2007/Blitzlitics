import pandas as pd
import plotly.express as px

from modules.analytics import find_column, get_date_column


COLORS = ["#5b67e8", "#13a88a", "#f0a64a", "#253451", "#8a96ad", "#53a4d5"]


def _numeric(data, column):
    return pd.to_numeric(data[column], errors="coerce").replace([float("inf"), float("-inf")], pd.NA)


def _monthly_data(data, date_column, columns):
    values = {"Period": pd.to_datetime(data[date_column], errors="coerce").dt.to_period("M").dt.to_timestamp()}
    values.update({label: _numeric(data, column) for label, column in columns.items()})
    monthly = pd.DataFrame(values).dropna(subset=["Period"])
    if monthly.empty:
        return monthly
    return (
        monthly.groupby("Period")[list(columns)]
        .sum(min_count=1)
        .reset_index()
        .sort_values("Period")
    )


def _category_chart(data, column, value_column, label, title, currency_symbol=None):
    values = pd.DataFrame(
        {"Name": data[column].astype("string"), "Value": _numeric(data, value_column)}
    ).dropna()
    if values.empty:
        return None
    values = (
        values.groupby("Name", as_index=False)["Value"]
        .sum()
        .sort_values("Value", ascending=False)
        .head(12)
        .sort_values("Value")
    )
    measure = f"{label} ({currency_symbol})" if currency_symbol is not None else label
    figure = px.bar(
        values,
        x="Value",
        y="Name",
        orientation="h",
        color_discrete_sequence=[COLORS[0]],
        labels={"Name": column, "Value": measure},
    )
    return title, figure


def build_charts(data, currency_symbol="$"):
    """Build only charts supported by recognized, available business columns."""
    charts = []
    revenue_column = find_column(data, "revenue")
    expense_column = find_column(data, "expenses")
    units_column = find_column(data, "units")
    date_column = get_date_column(data)
    category_column = find_column(data, "category")
    product_column = find_column(data, "product")

    if revenue_column and date_column:
        monthly = _monthly_data(data, date_column, {"Revenue": revenue_column})
        if not monthly.empty and monthly["Revenue"].notna().any():
            figure = px.line(
                monthly,
                x="Period",
                y="Revenue",
                markers=True,
                color_discrete_sequence=[COLORS[0]],
                labels={"Period": "Month", "Revenue": f"Revenue ({currency_symbol})"},
            )
            charts.append(("Revenue trend", figure))

    if revenue_column and expense_column:
        if date_column:
            monthly = _monthly_data(
                data, date_column, {"Revenue": revenue_column, "Expenses": expense_column}
            )
            comparison = monthly.melt(
                id_vars="Period", var_name="Measure", value_name="Amount"
            ).dropna()
            if not comparison.empty:
                figure = px.line(
                    comparison,
                    x="Period",
                    y="Amount",
                    color="Measure",
                    markers=True,
                    color_discrete_sequence=COLORS[:2],
                    labels={
                        "Period": "Month",
                        "Amount": f"Amount ({currency_symbol})",
                        "Measure": "Financial measure",
                    },
                )
                charts.append(("Revenue and expenses", figure))
            if not monthly.empty:
                monthly["Profit"] = monthly["Revenue"] - monthly["Expenses"]
                profit = monthly.dropna(subset=["Profit"])
                if not profit.empty:
                    figure = px.area(
                        profit,
                        x="Period",
                        y="Profit",
                        markers=True,
                        color_discrete_sequence=[COLORS[1]],
                        labels={"Period": "Month", "Profit": f"Net profit ({currency_symbol})"},
                    )
                    charts.append(("Profit trend", figure))
        else:
            totals = pd.DataFrame(
                {
                    "Measure": ["Revenue", "Expenses"],
                    "Amount": [
                        _numeric(data, revenue_column).sum(min_count=1),
                        _numeric(data, expense_column).sum(min_count=1),
                    ],
                }
            ).dropna()
            if not totals.empty:
                figure = px.bar(
                    totals,
                    x="Measure",
                    y="Amount",
                    color="Measure",
                    color_discrete_sequence=COLORS[:2],
                    labels={"Measure": "Financial measure", "Amount": f"Amount ({currency_symbol})"},
                )
                charts.append(("Revenue and expenses", figure))

    if revenue_column and category_column:
        chart = _category_chart(
            data, category_column, revenue_column, "Revenue", "Revenue by category", currency_symbol
        )
        if chart:
            charts.append(chart)
    if revenue_column and product_column:
        chart = _category_chart(
            data, product_column, revenue_column, "Revenue", "Revenue by product", currency_symbol
        )
        if chart:
            charts.append(chart)
    if expense_column and category_column:
        chart = _category_chart(
            data, category_column, expense_column, "Expenses", "Expenses by category", currency_symbol
        )
        if chart:
            charts.append(chart)

    if units_column and date_column:
        monthly = _monthly_data(data, date_column, {"Units sold": units_column})
        if not monthly.empty and monthly["Units sold"].notna().any():
            figure = px.bar(
                monthly,
                x="Period",
                y="Units sold",
                color_discrete_sequence=[COLORS[2]],
                labels={"Period": "Month", "Units sold": "Units sold"},
            )
            charts.append(("Units sold over time", figure))
    if units_column and product_column:
        chart = _category_chart(data, product_column, units_column, "Units sold", "Units sold by product")
        if chart:
            charts.append(chart)

    for _, figure in charts:
        figure.update_layout(
            template="plotly_white",
            font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", color="#45516a", size=11),
            margin=dict(l=18, r=18, t=18, b=18),
            legend_title_text="",
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            hoverlabel=dict(
                bgcolor="#172338",
                bordercolor="#172338",
                font=dict(color="#f7f8fc", size=12),
                namelength=-1,
            ),
            hovermode="x unified" if figure.data and figure.data[0].type in {"scatter", "bar"} else "closest",
            showlegend=len(figure.data) > 1,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        figure.update_xaxes(showgrid=False, zeroline=False, linecolor="#edf0f5", tickfont=dict(color="#8792a5", size=10))
        figure.update_yaxes(gridcolor="#edf0f5", zeroline=False, linecolor="#edf0f5", tickfont=dict(color="#8792a5", size=10))
    return charts
