from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import streamlit as st

from modules.analytics import (
    analyze_business_data,
    filter_data,
    filter_data_by_ranges,
    get_date_column,
)
from modules.charts import build_charts
from modules.data_loader import (
    FIELD_LABELS,
    apply_column_mappings,
    infer_column_mappings,
    infer_column_types,
    inspect_data_quality,
    load_sample_data,
    load_uploaded_file,
)
from modules.insights import generate_insights
from modules.report_generator import export_csv, export_excel, export_pdf


st.set_page_config(
    page_title="Blitzlitics | Business intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #17233b;
        --navy-soft: #202e49;
        --accent: #5b67e8;
        --accent-soft: #eef0ff;
        --ink: #1d293b;
        --muted: #738096;
        --canvas: #f5f7fb;
        --border: #e7ebf2;
        --success: #16856f;
        --shadow-card: 0 5px 18px rgba(27, 39, 67, .045), 0 1px 3px rgba(27, 39, 67, .04);
    }
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
    }
    .stApp, [data-testid="stAppViewContainer"] > .main { background: var(--canvas); }
    [data-testid="stMainBlockContainer"] {
        max-width: 1540px;
        padding: 2rem clamp(1.15rem, 3vw, 3.1rem) 3rem;
    }
    [data-testid="stHeader"] { background: rgba(245, 247, 251, .9); }
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
        background: var(--navy);
        border-right: 1px solid rgba(255,255,255,.07);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #b7c1d1 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #edf1f8;
        font-size: .72rem;
        letter-spacing: .12em;
        margin: 1.15rem 0 .45rem;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.1); }
    .brand-lockup { align-items: center; display: flex; gap: .75rem; margin: .25rem 0 .2rem; }
    .brand-mark {
        align-items: center;
        background: linear-gradient(145deg, #818bff, #5260eb);
        border: 1px solid rgba(255,255,255,.2);
        border-radius: 12px;
        box-shadow: 0 5px 18px rgba(78, 93, 240, .28);
        color: #fff;
        display: flex;
        font-size: 1.08rem;
        font-weight: 800;
        height: 38px;
        justify-content: center;
        width: 38px;
    }
    .brand-name { color: #f7f8fc; font-size: 1.27rem; font-weight: 740; letter-spacing: -.045em; margin: 0; }
    .tagline { color: #91a0b7; font-size: .75rem; line-height: 1.55; margin: .45rem 0 1rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: .18rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 9px;
        color: #bdc7d7 !important;
        padding: .43rem .62rem;
        transition: background .16s ease, border-color .16s ease, color .16s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(255,255,255,.055);
        color: #fff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: rgba(101, 113, 246, .17);
        border-color: rgba(138, 146, 255, .2);
        color: #fff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        color: #fff !important;
        font-weight: 650;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        background: rgba(255,255,255,.075);
        border-color: rgba(255,255,255,.13);
        border-radius: 9px;
        color: #f4f6fb;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] svg { fill: #b6c1d2; }
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: rgba(108, 121, 244, .24);
        border: 1px solid rgba(150, 158, 255, .2);
        border-radius: 6px;
    }
    .eyebrow {
        color: var(--accent);
        font-size: .68rem;
        font-weight: 750;
        letter-spacing: .13em;
        margin: 0 0 .45rem;
        text-transform: uppercase;
    }
    .page-title {
        color: var(--ink);
        font-size: clamp(1.65rem, 3vw, 2.2rem);
        font-weight: 740;
        letter-spacing: -.05em;
        line-height: 1.17;
        margin: 0;
    }
    .page-subtitle { color: var(--muted); font-size: .92rem; line-height: 1.6; margin: .5rem 0 1.25rem; }
    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid var(--border);
        border-radius: 14px;
        min-height: 113px;
        padding: 1rem 1.05rem .85rem;
        box-shadow: var(--shadow-card);
        transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #d7dcf4;
        box-shadow: 0 9px 24px rgba(27, 39, 67, .075);
        transform: translateY(-2px);
    }
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] p {
        color: #68758c !important;
        font-size: .76rem;
        font-weight: 630;
    }
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div {
        color: var(--ink) !important;
        font-size: clamp(1.05rem, 1.55vw, 1.6rem) !important;
        font-weight: 730;
        letter-spacing: -.04em;
        line-height: 1.2;
        white-space: nowrap;
    }
    div[data-testid="stMetricDelta"] { font-size: .72rem; font-weight: 620; }
    h2, h3 { color: var(--ink); letter-spacing: -.025em; }
    h3 { font-size: 1rem; font-weight: 680; margin: 1.15rem 0 .55rem; }
    [data-testid="stPlotlyChart"] {
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(27, 39, 67, .035);
        overflow: hidden;
    }
    [data-testid="stExpander"], [data-testid="stAlert"] {
        border-radius: 11px;
    }
    .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
        border-radius: 9px;
        font-size: .84rem;
        font-weight: 640;
        min-height: 2.55rem;
        transition: background .16s ease, border-color .16s ease, box-shadow .16s ease, transform .16s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        box-shadow: 0 4px 12px rgba(67, 82, 205, .1);
        transform: translateY(-1px);
    }
    [data-testid="stFileUploader"] section {
        background: #fbfcff;
        border: 1px dashed #cbd2e2;
        border-radius: 12px;
        transition: background .18s ease, border-color .18s ease;
    }
    [data-testid="stFileUploader"] section:hover {
        background: #f5f6ff;
        border-color: #8992ff;
    }
    @media (max-width: 800px) {
        [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem 2rem; }
        div[data-testid="stMetric"] { min-height: 103px; padding: .8rem; }
        .page-title { font-size: 1.7rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_PATH = Path(__file__).parent / "data" / "sample_business_data.csv"
CURRENCY_OPTIONS = {
    "USD ($)": "$",
    "EUR (€)": "€",
    "GBP (£)": "£",
    "INR (₹)": "₹",
    "No currency symbol": "",
}
PAGES = [
    "Overview",
    "Sales Analytics",
    "Product Performance",
    "Financial Analytics",
    "Data Explorer",
    "Business Insights",
    "Reports",
]
PAGE_ICONS = {
    "Overview": "space_dashboard",
    "Sales Analytics": "query_stats",
    "Product Performance": "inventory_2",
    "Financial Analytics": "account_balance",
    "Data Explorer": "table_view",
    "Business Insights": "lightbulb",
    "Reports": "summarize",
}


def format_currency(value, symbol):
    if value is None or pd.isna(value):
        return "Unavailable"
    if float(value).is_integer():
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"


def format_number(value):
    if value is None or pd.isna(value):
        return "Unavailable"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def _remember_upload():
    uploaded_file = st.session_state.get("data_explorer_upload")
    if uploaded_file is not None:
        st.session_state["uploaded_dataset"] = {
            "name": uploaded_file.name,
            "content": uploaded_file.getvalue(),
        }
        st.session_state["active_source"] = "Uploaded data"
        st.session_state["dataset_name"] = Path(uploaded_file.name).stem


def _save_mapping(mapping_key, field, widget_key):
    mappings = dict(st.session_state[mapping_key])
    selected = st.session_state[widget_key]
    mappings[field] = None if selected == "Not mapped" else selected
    st.session_state[mapping_key] = mappings


def render_quality(quality):
    issue_count = (
        sum(quality["missing_values"].values())
        + quality["duplicate_rows"]
        + sum(quality["invalid_dates"].values())
        + sum(quality["invalid_numeric"].values())
    )
    if issue_count:
        st.warning(
            f"Found {issue_count} data-quality issue(s). Review the details before relying on these results."
        )
        details = {
            "Missing values by column": quality["missing_values"],
            "Duplicate rows": quality["duplicate_rows"],
            "Invalid dates by column": quality["invalid_dates"],
            "Invalid numeric values by column": quality["invalid_numeric"],
        }
        for label, value in details.items():
            if value:
                st.write(f"**{label}:** {value}")
    else:
        st.success("No missing values, duplicate rows, invalid dates, or invalid numeric values detected.")


def render_filters(data, key_prefix):
    date_range = None
    selections = {}
    numeric_ranges = {}
    date_column = get_date_column(data)

    if date_column:
        parsed_dates = pd.to_datetime(data[date_column], errors="coerce").dropna()
        if not parsed_dates.empty:
            date_range = st.date_input(
                "Reporting date range",
                value=(parsed_dates.min().date(), parsed_dates.max().date()),
                min_value=parsed_dates.min().date(),
                max_value=parsed_dates.max().date(),
                key=f"{key_prefix}_date",
            )

    types = infer_column_types(data)
    with st.expander("Dimensions", expanded=False):
        for column in data.columns:
            if column == date_column or types[column] not in {"text", "boolean"}:
                continue
            options = sorted(data[column].dropna().astype(str).unique().tolist())
            if len(options) < 2:
                continue
            if len(options) <= 50:
                selections[column] = st.multiselect(
                    str(column),
                    options,
                    default=options,
                    key=f"{key_prefix}_category_{column}",
                )
            else:
                query = st.text_input(
                    f"Search {column}",
                    key=f"{key_prefix}_search_{column}",
                    placeholder="Type to filter matching values",
                )
                if query.strip():
                    selections[column] = {"contains": query.strip()}

    with st.expander("Numeric ranges", expanded=False):
        for column in data.columns:
            if not types[column].startswith("numeric"):
                continue
            values = pd.to_numeric(data[column], errors="coerce").dropna()
            if values.empty:
                continue
            minimum, maximum = float(values.min()), float(values.max())
            if minimum < maximum:
                numeric_ranges[column] = st.slider(
                    f"{column} range",
                    min_value=minimum,
                    max_value=maximum,
                    value=(minimum, maximum),
                    key=f"{key_prefix}_range_{column}",
                )
    return date_range, selections, numeric_ranges


def show_page_header(eyebrow, title, subtitle):
    st.markdown(f'<p class="eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-title">{title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-subtitle">{subtitle}</p>', unsafe_allow_html=True)


def reporting_period(data):
    date_column = get_date_column(data)
    if date_column is None:
        return "No date column mapped"
    dates = pd.to_datetime(data[date_column], errors="coerce").dropna()
    if dates.empty:
        return "No valid dates in the selected records"
    return f"{dates.min():%b %d, %Y} – {dates.max():%b %d, %Y}"


def render_chart_cards(charts, selected_titles, columns=2):
    selected = [(title, figure) for title, figure in charts if title in selected_titles]
    if not selected:
        st.info("These charts are unavailable because the selected data does not contain the required mapped columns.")
        return
    for index in range(0, len(selected), columns):
        row_size = min(columns, len(selected) - index)
        chart_columns = st.columns(row_size)
        for offset, (title, figure) in enumerate(selected[index:index + row_size]):
            with chart_columns[offset]:
                with st.container(border=True):
                    st.subheader(title)
                    st.plotly_chart(
                        figure,
                        width="stretch",
                        config={"displaylogo": False, "responsive": True},
                    )


def render_kpi(label, value, explanation, comparison=None, suffix="%"):
    delta = None
    delta_description = None
    if comparison is not None:
        display_comparison = f"{comparison:+.1f}{suffix}"
        delta = display_comparison
        delta_description = "vs previous available month"
    with st.container(border=True):
        st.metric(
            label,
            value,
            delta=delta,
            delta_description=delta_description,
            help=explanation,
        )
        st.caption(explanation)


st.session_state.setdefault("active_page", "Overview")
st.session_state.setdefault("active_source", "Sample data")

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-mark">B</div><p class="brand-name">Blitzlitics</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<p class="tagline">Clarity for every business decision.</p>', unsafe_allow_html=True)
    page = st.radio(
        "Workspace",
        PAGES,
        key="active_page",
        format_func=lambda item: f":material/{PAGE_ICONS[item]}:  {item}",
        label_visibility="collapsed",
    )
    st.divider()
    st.subheader("Data")
    source = st.radio(
        "Dataset",
        ["Sample data", "Uploaded data"],
        key="active_source",
        horizontal=True,
    )
    currency_label = st.selectbox(
        "Currency display",
        list(CURRENCY_OPTIONS),
        index=0 if source == "Sample data" else 4,
        key=f"currency_{source.replace(' ', '_').lower()}",
        help="Changes the displayed currency symbol only; it does not convert values.",
    )
    currency_symbol = CURRENCY_OPTIONS[currency_label]

uploaded_dataset = st.session_state.get("uploaded_dataset")
if source == "Sample data":
    try:
        with st.spinner("Loading the sample business dataset…"):
            raw_data = load_sample_data(DATA_PATH)
    except (ValueError, OSError, pd.errors.ParserError) as error:
        st.error(f"Could not load the sample dataset: {error}")
        st.stop()
    dataset_name = "Blitzlitics sample business"
    dataset_id = "sample"
elif uploaded_dataset is not None:
    try:
        upload_buffer = BytesIO(uploaded_dataset["content"])
        upload_buffer.name = uploaded_dataset["name"]
        raw_data = load_uploaded_file(upload_buffer)
    except (ValueError, OSError, pd.errors.ParserError, ImportError) as error:
        st.error(f"Could not load the selected dataset: {error}")
        st.stop()
    dataset_name = Path(uploaded_dataset["name"]).stem
    dataset_id = sha256(uploaded_dataset["content"]).hexdigest()[:16]
else:
    raw_data = None
    dataset_name = "Business report"
    dataset_id = "pending-upload"

if raw_data is None and page != "Data Explorer":
    show_page_header(
        "Business intelligence",
        "Add a dataset to get started",
        "Upload a CSV or Excel workbook from Data Explorer to explore your business performance.",
    )
    st.info("Choose **Data Explorer** in the sidebar to upload a dataset, or switch to the sample data.")
    st.stop()

if "dataset_name" not in st.session_state:
    st.session_state["dataset_name"] = dataset_name
with st.sidebar:
    dataset_name = st.text_input(
        "Report name",
        key="dataset_name",
        help="Used as the name in Excel and PDF reports.",
    )

if raw_data is None:
    raw_data = pd.DataFrame()

auto_mappings, mapping_candidates = infer_column_mappings(raw_data)
mapping_key = f"bizlytics_mappings_{dataset_id}"
if mapping_key not in st.session_state:
    st.session_state[mapping_key] = {
        field: auto_mappings.get(field) for field in FIELD_LABELS
    }
mapping_values = dict(st.session_state[mapping_key])

if page == "Data Explorer":
    show_page_header(
        "Your data workspace",
        "Data Explorer",
        "Upload, validate, map, filter, and inspect the records behind your analysis.",
    )
    with st.container(border=True):
        st.subheader("Bring your data")
        st.caption("Upload a CSV or Excel workbook (.xlsx). Your file stays in this app session and is not sent to an external service.")
        st.file_uploader(
            "Choose a CSV or XLSX file",
            type=["csv", "xlsx"],
            key="data_explorer_upload",
            on_change=_remember_upload,
            help="Use a header row. You can map date, revenue, expenses, units, product, and category columns.",
        )
        if uploaded_dataset is not None:
            st.caption(f"Loaded: {uploaded_dataset['name']} · {len(raw_data):,} records")

    with st.expander("Confirm or map columns", expanded=not bool(auto_mappings)):
        st.caption(
            "Suggested matches come from column headers. Map fields used by analytics; "
            "source headers and cell values remain unchanged."
        )
        mapping_columns = st.columns(2)
        options = ["Not mapped"] + list(raw_data.columns)
        for index, (field, label) in enumerate(FIELD_LABELS.items()):
            candidates = mapping_candidates[field]
            if len(candidates) > 1:
                st.warning(
                    f"Several columns could represent {label.lower()}: "
                    f"{', '.join(map(str, candidates))}. Choose the correct column."
                )
            widget_key = f"mapping_{dataset_id}_{field}"
            if widget_key not in st.session_state:
                st.session_state[widget_key] = mapping_values.get(field) or "Not mapped"
            with mapping_columns[index % 2]:
                st.selectbox(
                    f"{label} column",
                    options,
                    key=widget_key,
                    on_change=_save_mapping,
                    args=(mapping_key, field, widget_key),
                )
            selected = st.session_state[widget_key]
            mapping_values[field] = None if selected == "Not mapped" else selected

try:
    data = apply_column_mappings(raw_data, mapping_values)
except ValueError as error:
    st.error(f"Column mapping is invalid: {error}")
    data = apply_column_mappings(raw_data, auto_mappings)

quality = inspect_data_quality(data)
schema = pd.DataFrame(
    [
        {
            "Column": str(column),
            "Detected type": kind,
            "Non-empty values": int(data[column].notna().sum()),
            "Missing values": int(data[column].isna().sum()),
        }
        for column, kind in infer_column_types(data).items()
    ]
)

with st.sidebar:
    st.subheader("Filters")
    date_range, selections, numeric_ranges = render_filters(data, f"global_{dataset_id}")

filtered_data = filter_data(data, date_range, selections)
filtered_data = filter_data_by_ranges(filtered_data, numeric_ranges)
metrics = analyze_business_data(filtered_data)
filtered_quality = inspect_data_quality(filtered_data)
insights = generate_insights(filtered_data, metrics, filtered_quality, currency_symbol)
charts = build_charts(filtered_data, currency_symbol)
comparisons = metrics.get("period_comparisons", {})

if source == "Sample data":
    st.caption("Sample dataset · fictional demonstration data")
if raw_data.empty:
    st.warning("This dataset has no business records yet. Upload a file or review its schema.")

if page == "Overview":
    show_page_header(
        "Business performance",
        "Welcome to Blitzlitics",
        "Your business at a glance. Every number reflects the selected dataset and filters.",
    )
    status_columns = st.columns([1.5, 1])
    with status_columns[0]:
        st.caption(f"Reporting period · {reporting_period(filtered_data)}")
    with status_columns[1]:
        st.badge(
            f"{len(filtered_data):,} records · {'quality checked' if not any(filtered_quality[key] for key in ('missing_values', 'duplicate_rows', 'invalid_dates', 'invalid_numeric')) else 'quality issues found'}",
            icon=":material/check_circle:",
            color="green" if not any(filtered_quality[key] for key in ("missing_values", "duplicate_rows", "invalid_dates", "invalid_numeric")) else "orange",
        )
    if filtered_data.empty:
        st.info("No records match the selected filters. Adjust the sidebar filters to see metrics and charts.")

    metric_rows = [
        (
            "Total revenue",
            format_currency(metrics["total_revenue"], currency_symbol),
            metrics["availability"]["revenue"],
            comparisons.get("revenue"),
            "%",
        ),
        (
            "Total expenses",
            format_currency(metrics["total_expenses"], currency_symbol),
            metrics["availability"]["expenses"],
            comparisons.get("expenses"),
            "%",
        ),
        (
            "Net profit",
            format_currency(metrics["net_profit"], currency_symbol),
            metrics["availability"]["profit"],
            comparisons.get("profit"),
            "%",
        ),
        (
            "Units sold",
            format_number(metrics["total_units_sold"]),
            metrics["availability"]["units"],
            comparisons.get("units"),
            "%",
        ),
        (
            "Average revenue",
            format_currency(metrics["average_revenue"], currency_symbol),
            metrics["availability"]["average_revenue"],
            comparisons.get("average_revenue"),
            "%",
        ),
        (
            "Profit margin",
            f"{metrics['profit_margin']:.1f}%" if metrics["profit_margin"] is not None else "Unavailable",
            metrics["availability"]["margin"],
            comparisons.get("margin"),
            " pp",
        ),
    ]
    for row_start in (0, 3):
        metric_columns = st.columns(3)
        for column, metric in zip(metric_columns, metric_rows[row_start:row_start + 3]):
            with column:
                render_kpi(*metric)

    leaders = []
    if metrics["best_product"]:
        leaders.append(f"Top product: **{metrics['best_product'][0]}**")
    if metrics["best_category"]:
        leaders.append(f"Top category: **{metrics['best_category'][0]}**")
    if leaders:
        st.caption("  ·  ".join(leaders))
    render_chart_cards(charts, {"Revenue trend", "Revenue and expenses"})
    with st.expander("Data quality"):
        render_quality(quality)

elif page == "Sales Analytics":
    show_page_header(
        "Sales performance",
        "Sales Analytics",
        "Track revenue movement and compare the categories contributing to sales.",
    )
    render_chart_cards(charts, {"Revenue trend", "Revenue and expenses", "Revenue by category"})
    if metrics["best_category"]:
        st.caption(
            f"Highest-revenue category in this selection: **{metrics['best_category'][0]}** "
            f"({format_currency(metrics['best_category'][1], currency_symbol)})."
        )

elif page == "Product Performance":
    show_page_header(
        "Product mix",
        "Product Performance",
        "See which products generate revenue and how many units are being sold.",
    )
    render_chart_cards(charts, {"Revenue by product", "Units sold by product", "Units sold over time"})
    if metrics["best_product"]:
        st.metric(
            "Leading product by revenue",
            metrics["best_product"][0],
            help=f"Revenue: {format_currency(metrics['best_product'][1], currency_symbol)}",
        )
    elif not any(title in {"Revenue by product", "Units sold by product"} for title, _ in charts):
        st.info("Map product, revenue, or units sold columns to see product performance.")

elif page == "Financial Analytics":
    show_page_header(
        "Financial health",
        "Financial Analytics",
        "Compare revenue with expenses and follow the resulting profit over time.",
    )
    render_chart_cards(charts, {"Revenue and expenses", "Profit trend", "Expenses by category"})
    financial_columns = st.columns(3)
    financial_columns[0].metric(
        "Revenue",
        format_currency(metrics["total_revenue"], currency_symbol),
        help=metrics["availability"]["revenue"],
    )
    financial_columns[1].metric(
        "Expenses",
        format_currency(metrics["total_expenses"], currency_symbol),
        help=metrics["availability"]["expenses"],
    )
    financial_columns[2].metric(
        "Net profit",
        format_currency(metrics["net_profit"], currency_symbol),
        help=metrics["availability"]["profit"],
    )

elif page == "Data Explorer":
    count_columns = st.columns(3)
    count_columns[0].metric("Source records", f"{len(data):,}")
    count_columns[1].metric("Filtered records", f"{len(filtered_data):,}")
    count_columns[2].metric("Columns", f"{len(data.columns):,}")
    with st.expander("Data quality and detected schema", expanded=False):
        render_quality(quality)
        st.dataframe(schema, width="stretch", hide_index=True)

    if filtered_data.empty:
        st.info("No records match the selected filters.")
    else:
        selected_columns = st.multiselect(
            "Columns to display and export",
            list(filtered_data.columns),
            default=list(filtered_data.columns),
        )
        if not selected_columns:
            st.info("Select at least one column to display or download records.")
        else:
            controls = st.columns([1.2, 1, 1])
            with controls[0]:
                sort_column = st.selectbox("Sort by", selected_columns)
            with controls[1]:
                sort_order = st.selectbox("Sort order", ["Ascending", "Descending"])
            with controls[2]:
                page_size = st.selectbox("Rows shown", [25, 50, 100, "All"], index=0)

            view_data = filtered_data[selected_columns].copy()
            sort_type = infer_column_types(filtered_data)[sort_column]
            if sort_type.startswith("numeric"):
                sort_key = lambda values: pd.to_numeric(values, errors="coerce")
            elif sort_type == "date/time":
                sort_key = lambda values: pd.to_datetime(values, errors="coerce")
            else:
                sort_key = lambda values: values.astype("string").str.casefold()
            view_data = view_data.sort_values(
                sort_column,
                key=sort_key,
                ascending=sort_order == "Ascending",
                na_position="last",
                kind="stable",
            )
            visible_data = view_data if page_size == "All" else view_data.head(page_size)
            st.caption(f"Showing {len(visible_data):,} of {len(view_data):,} filtered rows.")
            st.dataframe(visible_data, width="stretch", hide_index=True)
            st.download_button(
                "Download filtered data as CSV",
                data=export_csv(view_data),
                file_name="blitzlitics_filtered_data.csv",
                mime="text/csv",
                key="download_filtered_csv",
            )

elif page == "Business Insights":
    show_page_header(
        "Signals from your data",
        "Business Insights",
        "Plain-language observations and practical next steps based only on the selected records.",
    )
    st.caption(f"Insights reflect {len(filtered_data):,} filtered record(s) · {reporting_period(filtered_data)}")
    for insight in insights:
        with st.container(border=True):
            if insight["type"] == "warning":
                st.badge("Needs attention", icon=":material/warning:", color="orange")
            elif insight["type"] == "positive":
                st.badge("Positive signal", icon=":material/trending_up:", color="green")
            else:
                st.badge("Observation", icon=":material/lightbulb:", color="blue")
            st.markdown(f"**{insight['title']}**")
            st.write(insight["detail"])
    if not insights:
        st.info("Map additional fields or select more records to uncover business insights.")

else:
    show_page_header(
        "Share your analysis",
        "Reports",
        "Download a portable summary of the filtered records, key metrics, insights, and data quality.",
    )
    st.caption(f"Reports include {len(filtered_data):,} filtered record(s) · {reporting_period(filtered_data)}")
    category_chart_available = any(title == "Revenue by category" for title, _ in charts)
    include_charts = st.multiselect(
        "Optional chart for the PDF report",
        ["Revenue by category"] if category_chart_available else [],
        default=["Revenue by category"] if category_chart_available else [],
    )
    file_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", dataset_name.strip()).strip("_") or "blitzlitics_report"
    report_columns = st.columns(3)
    with report_columns[0]:
        with st.container(border=True):
            st.subheader("CSV records")
            st.caption("A straightforward export of every filtered row and column.")
            st.download_button(
                "Download CSV",
                data=export_csv(filtered_data),
                file_name=f"{file_stem}_records.csv",
                mime="text/csv",
                key="report_csv",
            )
    with report_columns[1]:
        with st.container(border=True):
            st.subheader("Excel report")
            st.caption("Records, summary metrics, business insights, and data-quality details.")
            st.download_button(
                "Download Excel",
                data=export_excel(filtered_data, dataset_name, metrics, insights, filtered_quality),
                file_name=f"{file_stem}_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="report_xlsx",
            )
    with report_columns[2]:
        with st.container(border=True):
            st.subheader("PDF report")
            st.caption("A presentation-ready summary with an optional category chart.")
            try:
                pdf_data = export_pdf(
                    filtered_data,
                    dataset_name,
                    metrics,
                    insights,
                    filtered_quality,
                    currency_symbol,
                    ["category_revenue"] if "Revenue by category" in include_charts else [],
                )
            except (ValueError, OSError, KeyError) as error:
                st.error(f"Could not generate the PDF report: {error}")
            else:
                st.download_button(
                    "Download PDF",
                    data=pdf_data,
                    file_name=f"{file_stem}_report.pdf",
                    mime="application/pdf",
                    key="report_pdf",
                )
