from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from modules.analytics import find_column, get_date_column


def export_csv(data):
    """Return a UTF-8 CSV download for the supplied (typically filtered) records."""
    return data.to_csv(index=False).encode("utf-8-sig")


def export_excel(data, dataset_name, metrics, insights, quality):
    """Build an in-memory workbook containing records and a concise report."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Records", index=False)
        summary = [
            {"Item": "Dataset", "Value": dataset_name},
            {"Item": "Rows", "Value": len(data)},
            {"Item": "Revenue", "Value": metrics.get("total_revenue")},
            {"Item": "Expenses", "Value": metrics.get("total_expenses")},
            {"Item": "Net profit", "Value": metrics.get("net_profit")},
            {"Item": "Profit margin (%)", "Value": metrics.get("profit_margin")},
            {"Item": "Revenue growth (%)", "Value": metrics.get("revenue_growth")},
        ]
        pd.DataFrame(summary).to_excel(writer, sheet_name="Summary", index=False)
        insight_rows = [
            {"Type": insight["type"], "Insight": insight["title"], "Detail": insight["detail"]}
            for insight in insights
        ]
        pd.DataFrame(insight_rows, columns=["Type", "Insight", "Detail"]).to_excel(
            writer, sheet_name="Insights", index=False
        )
        quality_rows = [
            {"Issue": "Missing values", "Details": str(quality.get("missing_values", {}))},
            {"Issue": "Duplicate rows", "Details": quality.get("duplicate_rows", 0)},
            {"Issue": "Invalid dates", "Details": str(quality.get("invalid_dates", {}))},
            {"Issue": "Invalid numeric values", "Details": str(quality.get("invalid_numeric", {}))},
        ]
        pd.DataFrame(quality_rows).to_excel(writer, sheet_name="Data quality", index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column_cells in sheet.columns:
                width = min(
                    max(len(str(cell.value or "")) for cell in column_cells) + 2,
                    55,
                )
                sheet.column_dimensions[column_cells[0].column_letter].width = max(width, 12)
    return buffer.getvalue()


class _ChartFlowable(Flowable):
    def __init__(self, chart):
        super().__init__()
        self.chart = chart
        self.width = chart.width
        self.height = chart.height

    def draw(self):
        renderPDF.draw(self.chart, self.canv, 0, 0)


def _category_chart(data, currency_symbol):
    category = find_column(data, "category")
    revenue = find_column(data, "revenue")
    if not category or not revenue:
        return None
    values = pd.DataFrame(
        {
            "category": data[category].astype("string"),
            "revenue": pd.to_numeric(data[revenue], errors="coerce"),
        }
    ).dropna().groupby("category")["revenue"].sum().sort_values().tail(8)
    if values.empty:
        return None
    chart = HorizontalBarChart()
    chart.x = 115
    chart.y = 25
    chart.width = 350
    chart.height = max(120, 26 * len(values))
    chart.data = [values.tolist()]
    chart.categoryAxis.categoryNames = [str(name) for name in values.index]
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labelTextFormat = f"{currency_symbol}%.0f"
    chart.valueAxis.labels.fontSize = 8
    chart.bars[0].fillColor = colors.HexColor("#0f9d91")
    drawing = Drawing(480, chart.height + 45)
    drawing.add(chart)
    return drawing


def _quality_messages(quality):
    messages = []
    if quality.get("missing_values"):
        messages.append(f"Missing values by column: {quality['missing_values']}")
    if quality.get("duplicate_rows"):
        messages.append(f"Duplicate rows: {quality['duplicate_rows']}")
    if quality.get("invalid_dates"):
        messages.append(f"Invalid dates by column: {quality['invalid_dates']}")
    if quality.get("invalid_numeric"):
        messages.append(f"Invalid numeric values by column: {quality['invalid_numeric']}")
    return messages or ["No missing values, duplicate rows, invalid dates, or invalid numeric values detected."]


def export_pdf(data, dataset_name, metrics, insights, quality, currency_symbol="$", selected_charts=None):
    """Create a downloadable PDF with summary, grounded insights, quality, and optional chart."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"Bizlytics report - {dataset_name}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], textColor=colors.HexColor("#102a43")))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], textColor=colors.HexColor("#0f766e"), spaceBefore=12))
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=8, leading=11, alignment=TA_LEFT))

    elements = [
        Paragraph("Bizlytics", styles["BrandTitle"]),
        Paragraph(f"Business performance report: {escape(str(dataset_name))}", styles["Heading2"]),
        Paragraph(f"Records included: {len(data):,}", styles["BodyText"]),
    ]
    date_column = get_date_column(data)
    if date_column:
        dates = pd.to_datetime(data[date_column], errors="coerce").dropna()
        if not dates.empty:
            elements.append(
                Paragraph(
                    f"Reporting period: {dates.min().date()} to {dates.max().date()}",
                    styles["BodyText"],
                )
            )

    def currency(value):
        return "Unavailable" if value is None or pd.isna(value) else f"{currency_symbol}{value:,.2f}"

    elements.extend(
        [
            Spacer(1, 10),
            Paragraph("Key metrics", styles["SectionTitle"]),
        ]
    )
    metric_rows = [
        ["Metric", "Value"],
        ["Revenue", currency(metrics.get("total_revenue"))],
        ["Expenses", currency(metrics.get("total_expenses"))],
        ["Net profit", currency(metrics.get("net_profit"))],
        ["Profit margin", f"{metrics['profit_margin']:.1f}%" if metrics.get("profit_margin") is not None else "Unavailable"],
        ["Revenue growth", f"{metrics['revenue_growth']:+.1f}%" if metrics.get("revenue_growth") is not None else "Unavailable"],
    ]
    metric_table = Table(metric_rows, colWidths=[2.5 * inch, 3.9 * inch], repeatRows=1)
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102a43")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f9")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9e2ec")),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elements.append(metric_table)
    elements.append(Paragraph("Automated insights", styles["SectionTitle"]))
    for insight in insights:
        elements.append(
            Paragraph(
                f"<b>{escape(str(insight['title']))}:</b> {escape(str(insight['detail']))}",
                styles["SmallBody"],
            )
        )
        elements.append(Spacer(1, 4))

    elements.append(Paragraph("Data quality", styles["SectionTitle"]))
    for message in _quality_messages(quality):
        elements.append(Paragraph(escape(message), styles["SmallBody"]))
        elements.append(Spacer(1, 3))

    selected_charts = set(selected_charts or [])
    if "category_revenue" in selected_charts:
        chart = _category_chart(data, currency_symbol)
        if chart is not None:
            elements.append(Paragraph("Revenue by category", styles["SectionTitle"]))
            elements.append(_ChartFlowable(chart))

    document.build(elements)
    return buffer.getvalue()
