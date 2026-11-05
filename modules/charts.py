import pandas as pd
import plotly.express as px

from modules.analytics import find_column, get_date_column


COLORS = ["#5865f2", "#18243a", "#18a889", "#8b96aa", "#f0ad55", "#54a3d8"]


def _numeric(data, column):
    return pd.to_numeric(data[column], errors="coerce").replace([float("inf"), float("-inf")], pd.NA)


def build_charts(data, currency_symbol="$"):
    """Build only charts supported by recognized columns in the provided data."""
    charts = []
    revenue_column = find_column(data, "revenue")
    expense_column = find_column(data, "expenses")
    date_column = get_date_column(data)
    category_column = find_column(data, "category")
    product_column = find_column(data, "product")

    if revenue_column and date_column:
        trend = pd.DataFrame(
            {
                "Date": pd.to_datetime(data[date_column], errors="coerce"),
                "Revenue": _numeric(data, revenue_column),
            }
        ).dropna()
        if not trend.empty:
            trend = trend.groupby("Date", as_index=False)["Revenue"].sum().sort_values("Date")
            charts.append(
                (
                    "Revenue over time",
                    px.line(
                        trend,
                        x="Date",
                        y="Revenue",
                        markers=True,
                        color_discrete_sequence=[COLORS[0]],
                        labels={"Date": "Date", "Revenue": f"Revenue ({currency_symbol})"},
                    ),
                )
            )

    if revenue_column and expense_column:
        comparison_values = pd.DataFrame(
            {
                "Revenue": _numeric(data, revenue_column),
                "Expenses": _numeric(data, expense_column),
            }
        )
        if comparison_values.notna().any().any():
            comparison = comparison_values.sum().rename_axis("Metric").reset_index(name="Amount")
            figure = px.bar(
                comparison,
                x="Metric",
                y="Amount",
                color="Metric",
                color_discrete_sequence=COLORS[:2],
                labels={"Metric": "Financial measure", "Amount": f"Amount ({currency_symbol})"},
            )
            charts.append(("Revenue vs. expenses", figure))
        if date_column:
            trend = pd.DataFrame(
                {
                    "Date": pd.to_datetime(data[date_column], errors="coerce"),
                    "Revenue": _numeric(data, revenue_column),
                    "Expenses": _numeric(data, expense_column),
                }
            ).dropna()
            if not trend.empty:
                trend = trend.groupby("Date", as_index=False)[["Revenue", "Expenses"]].sum().sort_values("Date")
                trend["Profit"] = trend["Revenue"] - trend["Expenses"]
                charts.append(
                    (
                        "Profit over time",
                        px.line(
                            trend,
                            x="Date",
                            y="Profit",
                            markers=True,
                            color_discrete_sequence=[COLORS[1]],
                            labels={"Date": "Date", "Profit": f"Net profit ({currency_symbol})"},
                        ),
                    )
                )

    breakdown_column = category_column or product_column
    if revenue_column and breakdown_column:
        comparison = pd.DataFrame(
            {
                "Name": data[breakdown_column].astype("string"),
                "Revenue": _numeric(data, revenue_column),
            }
        ).dropna()
        if not comparison.empty:
            comparison = comparison.groupby("Name", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
            title = "Revenue by category" if category_column else "Revenue by product"
            charts.append(
                (
                    title,
                    px.bar(
                        comparison,
                        x="Name",
                        y="Revenue",
                        color="Revenue",
                        color_continuous_scale=["#e5e9ff", COLORS[0]],
                        labels={"Name": "Category or product", "Revenue": f"Revenue ({currency_symbol})"},
                    ),
                )
            )

    if expense_column and category_column:
        breakdown = pd.DataFrame(
            {
                "Category": data[category_column].astype("string"),
                "Expenses": _numeric(data, expense_column),
            }
        ).dropna()
        if not breakdown.empty:
            breakdown = breakdown.groupby("Category", as_index=False)["Expenses"].sum()
            charts.append(
                (
                    "Expense breakdown",
                    px.pie(
                        breakdown,
                        names="Category",
                        values="Expenses",
                        hole=0.45,
                        color_discrete_sequence=COLORS,
                        labels={"Category": "Category", "Expenses": f"Expenses ({currency_symbol})"},
                    ),
                )
            )

    for _, figure in charts:
        figure.update_layout(
            template="plotly_white",
            font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", color="#45516a", size=11),
            margin=dict(l=18, r=18, t=24, b=18),
            legend_title_text="",
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            hoverlabel=dict(
                bgcolor="#172338",
                bordercolor="#172338",
                font=dict(color="#f7f8fc", size=12),
                namelength=-1,
            ),
            hovermode="x unified",
            showlegend=len(figure.data) > 1,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10),
            ),
        )
        figure.update_xaxes(
            showgrid=False,
            zeroline=False,
            linecolor="#edf0f5",
            tickfont=dict(color="#8792a5", size=10),
        )
        figure.update_yaxes(
            gridcolor="#edf0f5",
            zeroline=False,
            linecolor="#edf0f5",
            tickfont=dict(color="#8792a5", size=10),
        )
        for trace in figure.data:
            if trace.type == "pie":
                trace.update(hovertemplate="<b>%{label}</b><br>%{value}<extra></extra>")
            else:
                trace.update(hovertemplate="%{x}<br><b>%{y}</b><extra></extra>")
    return charts
