from io import BytesIO

import numpy as np
import pandas as pd

from modules.analytics import (
    analyze_business_data,
    filter_data,
    filter_data_by_ranges,
)
from modules.charts import build_charts
from modules.data_loader import (
    apply_column_mappings,
    infer_column_mappings,
    infer_column_types,
    inspect_data_quality,
    load_sample_data,
)
from modules.insights import generate_insights
from modules.report_generator import export_csv, export_excel, export_pdf


def test_revenue_and_expense_totals():
    result = analyze_business_data(pd.DataFrame({"revenue": [100, 250], "expenses": [30, 70]}))
    assert result["total_revenue"] == 350
    assert result["total_expenses"] == 100


def test_profit_and_margin():
    result = analyze_business_data(pd.DataFrame({"revenue": [400], "expenses": [100]}))
    assert result["net_profit"] == 300
    assert result["profit_margin"] == 75


def test_revenue_growth_uses_latest_available_months():
    data = pd.DataFrame(
        {
            "date": ["2025-01-03", "2025-02-03"],
            "revenue": [100, 150],
            "expenses": [40, 50],
        }
    )
    assert analyze_business_data(data)["revenue_growth"] == 50


def test_zero_revenue_does_not_create_infinite_margin_or_growth():
    data = pd.DataFrame(
        {
            "date": ["2025-01-03", "2025-02-03"],
            "revenue": [0, 0],
            "expenses": [5, 20],
        }
    )
    result = analyze_business_data(data)
    assert result["net_profit"] == -25
    assert result["profit_margin"] is None
    assert result["revenue_growth"] is None


def test_growth_from_zero_comparison_period_is_unavailable():
    data = pd.DataFrame(
        {
            "date": ["2025-01-03", "2025-02-03"],
            "revenue": [0, 100],
            "expenses": [0, 20],
        }
    )
    result = analyze_business_data(data)
    assert result["revenue_growth"] is None
    assert result["profit_margin"] == 80


def test_missing_values_are_ignored_in_totals_and_reported():
    data = pd.DataFrame({"revenue": [100, np.nan], "expenses": [30, None]})
    result = analyze_business_data(data)
    quality = inspect_data_quality(data)
    assert result["total_revenue"] == 100
    assert result["total_expenses"] == 30
    assert result["net_profit"] == 70
    assert quality["missing_values"] == {"revenue": 1, "expenses": 1}


def test_empty_dataset_returns_unavailable_metrics():
    result = analyze_business_data(pd.DataFrame(columns=["revenue", "expenses"]))
    assert result["total_revenue"] is None
    assert result["total_expenses"] is None
    assert result["net_profit"] is None
    assert result["profit_margin"] is None


def test_missing_and_unrecognized_columns_are_not_assumed_to_be_financial():
    result = analyze_business_data(pd.DataFrame({"amount": [500], "cost": [200]}))
    assert result["total_revenue"] is None
    assert result["total_expenses"] is None
    assert result["net_profit"] is None
    assert result["best_product"] is None


def test_manual_mapping_preserves_original_headers_and_drives_metrics():
    original = pd.DataFrame({"Order value": [120, 80], "Operating cost": [40, 30]})
    assert infer_column_mappings(original)[0] == {}
    mapped = apply_column_mappings(
        original,
        {"revenue": "Order value", "expenses": "Operating cost"},
    )
    assert list(mapped.columns) == ["Order value", "Operating cost"]
    assert analyze_business_data(mapped)["net_profit"] == 130
    assert infer_column_types(mapped)["Order value"] == "numeric"


def test_csv_and_xlsx_uploads_load_in_memory():
    from modules.data_loader import load_uploaded_file

    csv_file = BytesIO(b"revenue,expenses\n120,50\n")
    csv_file.name = "business.csv"
    assert analyze_business_data(load_uploaded_file(csv_file))["net_profit"] == 70

    excel_file = BytesIO()
    pd.DataFrame({"revenue": [200], "expenses": [80]}).to_excel(excel_file, index=False)
    excel_file.seek(0)
    excel_file.name = "business.xlsx"
    assert analyze_business_data(load_uploaded_file(excel_file))["net_profit"] == 120


def test_corrupt_excel_upload_returns_a_clear_validation_error():
    import pytest

    from modules.data_loader import load_uploaded_file

    corrupt_file = BytesIO(b"not an Excel workbook")
    corrupt_file.name = "broken.xlsx"
    with pytest.raises(ValueError, match="Could not read broken.xlsx"):
        load_uploaded_file(corrupt_file)


def test_quality_detects_duplicate_rows_invalid_values_and_blank_cells():
    data = pd.DataFrame(
        {
            "date": ["2025-01-01", "bad-date", "bad-date", "2025-01-02"],
            "revenue": ["10", "not-a-number", "not-a-number", ""],
            "expenses": [5, 5, 5, 5],
        }
    )
    quality = inspect_data_quality(data)
    assert quality["duplicate_rows"] == 1
    assert quality["missing_values"]["revenue"] == 1
    assert quality["invalid_dates"] == {"date": 2}
    assert quality["invalid_numeric"] == {"revenue": 2}


def test_filters_apply_categories_search_dates_and_numeric_ranges():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]),
            "category": ["Services", "Retail", "Services"],
            "revenue": [10, 20, 30],
        }
    )
    filtered = filter_data(
        data,
        (pd.Timestamp("2025-01-01").date(), pd.Timestamp("2025-03-01").date()),
        {"category": {"contains": "serv"}},
    )
    filtered = filter_data_by_ranges(filtered, {"revenue": (15, 35)})
    assert filtered["revenue"].tolist() == [30]
    assert len(data) == 3


def test_sample_charts_and_insights_use_available_data():
    sample = load_sample_data("data/sample_business_data.csv")
    metrics = analyze_business_data(sample)
    quality = inspect_data_quality(sample)
    assert len(build_charts(sample)) == 5
    titles = {item["title"] for item in generate_insights(sample, metrics, quality)}
    assert "Revenue movement" in titles
    assert "Profit margin movement" in titles
    assert "Largest revenue category" in titles


def test_csv_excel_and_pdf_exports_are_readable():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "category": ["Retail", "Services"],
            "revenue": [100, 150],
            "expenses": [50, 60],
        }
    )
    metrics = analyze_business_data(data)
    quality = inspect_data_quality(data)
    insights = generate_insights(data, metrics, quality)

    csv_result = pd.read_csv(BytesIO(export_csv(data)))
    assert len(csv_result) == 2
    excel_result = pd.ExcelFile(BytesIO(export_excel(data, "Test business", metrics, insights, quality)))
    assert {"Records", "Summary", "Insights", "Data quality"}.issubset(excel_result.sheet_names)
    pdf_result = export_pdf(data, "Test business", metrics, insights, quality, "$", ["category_revenue"])
    assert pdf_result.startswith(b"%PDF")
    assert len(pdf_result) > 500
