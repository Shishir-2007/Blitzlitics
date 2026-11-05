import re
from pathlib import Path

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
    page_title="Bizlytics | Business Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #121b2c;
        --navy-soft: #1a2639;
        --accent: #5865f2;
        --accent-hover: #4854de;
        --accent-soft: #eef0ff;
        --ink: #172338;
        --muted: #718096;
        --surface: #ffffff;
        --canvas: #f6f7fb;
        --border: #e8ebf2;
        --success: #16856f;
        --warning: #a76b12;
        --shadow-card: 0 5px 18px rgba(27, 39, 67, .045), 0 1px 3px rgba(27, 39, 67, .04);
    }
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
    }
    .stApp { background: var(--canvas); color: var(--ink); }
    [data-testid="stAppViewContainer"] > .main { background: var(--canvas); }
    [data-testid="stMainBlockContainer"] {
        max-width: 1540px;
        padding: 2rem clamp(1.15rem, 3vw, 3.1rem) 3rem;
    }
    [data-testid="stHeader"] { background: rgba(246, 247, 251, .88); }
    [data-testid="stSidebar"] {
        background: var(--navy);
        border-right: 1px solid rgba(255,255,255,.07);
    }
    [data-testid="stSidebar"] > div:first-child {
        background: var(--navy);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #aab6c9;
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #bdc7d7 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #eef2fa;
        font-size: .8rem;
        letter-spacing: .11em;
        margin: 1rem 0 .45rem;
        text-transform: uppercase;
    }
    .brand-lockup {
        align-items: center;
        display: flex;
        gap: .75rem;
        margin: .25rem 0 .2rem;
    }
    .brand-mark {
        align-items: center;
        background: linear-gradient(145deg, #7882ff, #5260eb);
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
    .brand { color: #f7f8fc; font-size: 1.38rem; font-weight: 720; letter-spacing: -.045em; margin: 0; }
    .tagline { color: #91a0b7; font-size: .77rem; line-height: 1.55; margin: .45rem 0 1.2rem; }
    .eyebrow { color: var(--accent); font-size: .69rem; font-weight: 750; letter-spacing: .13em; margin: 0 0 .5rem; text-transform: uppercase; }
    .page-title { color: var(--ink); font-size: clamp(1.65rem, 3vw, 2.15rem); font-weight: 730; letter-spacing: -.052em; line-height: 1.17; margin: 0; }
    .page-subtitle { color: var(--muted); font-size: .92rem; line-height: 1.6; margin: .55rem 0 1.45rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: .22rem;
    }
    [data-testid="stSidebar"] input[type="radio"] {
        accent-color: #8992ff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 9px;
        color: #bdc7d7 !important;
        padding: .5rem .7rem;
        transition: background .16s ease, border-color .16s ease, color .16s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(255,255,255,.055);
        color: #fff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: rgba(101, 113, 246, .16);
        border-color: rgba(138, 146, 255, .18);
        color: #fff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        color: #fff !important;
        font-weight: 650;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) [role="radio"] {
        accent-color: #8992ff !important;
        background-color: #8992ff !important;
        border-color: #8992ff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) [role="radio"]::after {
        background: #8992ff !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,.1);
        margin: 1rem 0;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        background: rgba(255,255,255,.075);
        border-color: rgba(255,255,255,.13);
        border-radius: 9px;
        color: #f4f6fb;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] svg {
        fill: #b6c1d2;
    }
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: rgba(108, 121, 244, .24);
        border: 1px solid rgba(150, 158, 255, .2);
        border-radius: 6px;
    }
    [data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
        background: #8590ff;
        border-color: #8590ff;
    }
    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        min-height: 118px;
        padding: 1.05rem 1.15rem .95rem;
        box-shadow: var(--shadow-card);
        transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #d7dcf4;
        box-shadow: 0 9px 24px rgba(27, 39, 67, .075);
        transform: translateY(-2px);
    }
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] label {
        color: #68758c !important;
        font-size: .78rem;
        font-weight: 620;
        letter-spacing: .015em;
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] > div {
        color: var(--ink) !important;
        font-size: clamp(1.05rem, 1.55vw, 1.6rem) !important;
        font-weight: 720;
        letter-spacing: -.045em;
        line-height: 1.2;
        white-space: nowrap;
    }
    div[data-testid="stMetricDelta"] { font-size: .75rem; font-weight: 620; }
    h2, h3 { color: var(--ink); letter-spacing: -.025em; }
    h3 {
        font-size: 1rem;
        font-weight: 680;
        margin: 1.25rem 0 .65rem;
    }
    [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
        scroll-margin-top: 1rem;
    }
    [data-testid="stPlotlyChart"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow-card);
        overflow: hidden;
        padding: .35rem .35rem .05rem;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(27, 39, 67, .035);
        overflow: hidden;
    }
    [data-testid="stExpander"] {
        background: rgba(255,255,255,.8);
        border: 1px solid var(--border);
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(27, 39, 67, .025);
        overflow: hidden;
    }
    [data-testid="stAlert"] {
        background: #fff !important;
        border: 1px solid rgba(88, 101, 242, .1);
        border-radius: 11px;
        box-shadow: 0 2px 8px rgba(27, 39, 67, .025);
    }
    [data-testid="stNotification"], [data-testid="stStatusWidget"] {
        border-radius: 11px;
    }
    [data-testid="stFileUploader"] section {
        background: rgba(255,255,255,.055);
        border: 1px dashed rgba(184, 197, 219, .38);
        border-radius: 12px;
        transition: background .18s ease, border-color .18s ease;
    }
    [data-testid="stFileUploader"] section:hover {
        background: rgba(255,255,255,.09);
        border-color: #8992ff;
    }
    [data-testid="stFileUploader"] button {
        background: #6572f5;
        border-color: #6572f5;
        border-radius: 8px;
        color: #fff;
        font-weight: 620;
    }
    .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
        background: #fff;
        border: 1px solid #dfe4ed;
        border-radius: 9px;
        color: #33415c;
        font-size: .84rem;
        font-weight: 640;
        min-height: 2.55rem;
        padding: .55rem 1rem;
        box-shadow: 0 1px 2px rgba(22, 34, 56, .04);
        transition: background .16s ease, border-color .16s ease, color .16s ease, box-shadow .16s ease, transform .16s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        background: #f5f6ff;
        border-color: #aeb5fb;
        color: #414fd0;
        box-shadow: 0 4px 12px rgba(67, 82, 205, .1);
        transform: translateY(-1px);
    }
    .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {
        box-shadow: 0 0 0 3px rgba(88, 101, 242, .2);
    }
    [data-baseweb="select"] > div, [data-baseweb="input"] > div,
    [data-testid="stDateInput"] input, [data-testid="stTextInput"] input {
        border-color: #e0e5ee;
        border-radius: 9px;
    }
    [data-baseweb="select"] > div:focus-within, [data-baseweb="input"] > div:focus-within,
    [data-testid="stDateInput"] input:focus, [data-testid="stTextInput"] input:focus {
        border-color: #8d96f7;
        box-shadow: 0 0 0 2px rgba(88, 101, 242, .12);
    }
    [data-testid="stProgressBar"] > div > div { background: var(--accent); }
    @media (max-width: 800px) {
        [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem 2rem; }
        div[data-testid="stMetric"] { min-height: 104px; padding: .85rem; }
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


def format_currency(value, symbol):
    if value is None or pd.isna(value):
        return "—"
    if float(value).is_integer():
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"


def show_metric(label, value, help_text, delta=None):
    st.metric(
        label,
        value if value is not None else "N/A",
        delta=delta,
        help=help_text,
    )


def render_quality(quality):
    issue_count = (
        sum(quality["missing_values"].values())
        + quality["duplicate_rows"]
        + sum(quality["invalid_dates"].values())
        + sum(quality["invalid_numeric"].values())
    )
    if issue_count:
        st.warning(f"Data-quality check found {issue_count} issue(s). Review these before relying on the results.")
        if quality["missing_values"]:
            st.write("**Missing values by column:**", quality["missing_values"])
        if quality["duplicate_rows"]:
            st.write(f"**Duplicate rows:** {quality['duplicate_rows']}")
        if quality["invalid_dates"]:
            st.write("**Invalid dates by column:**", quality["invalid_dates"])
        if quality["invalid_numeric"]:
            st.write("**Invalid numeric values by column:**", quality["invalid_numeric"])
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
                "Date range",
                value=(parsed_dates.min().date(), parsed_dates.max().date()),
                min_value=parsed_dates.min().date(),
                max_value=parsed_dates.max().date(),
                key=f"{key_prefix}_date",
            )

    types = infer_column_types(data)
    for column in data.columns:
        if column == date_column:
            continue
        if types[column] in {"text", "boolean"}:
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
        elif types[column].startswith("numeric"):
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


def _show_page_header(eyebrow, title, subtitle):
    st.markdown(f'<p class="eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-title">{title}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-subtitle">{subtitle}</p>', unsafe_allow_html=True)


with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-mark">B</div><p class="brand">Bizlytics</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="tagline">Turn Business Data into Better Decisions.</p>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navigate",
        ["Overview", "Explore data", "Insights & reports"],
        format_func=lambda item: {
            "Overview": "◈  Overview",
            "Explore data": "▤  Explore data",
            "Insights & reports": "✧  Insights & reports",
        }[item],
        label_visibility="collapsed",
    )
    st.divider()
    source = st.radio("Data source", ["Sample data", "Upload a file"])
    uploaded_file = None
    if source == "Upload a file":
        uploaded_file = st.file_uploader(
            "Choose a CSV or Excel file",
            type=["csv", "xlsx"],
            help="Use a header row. You can manually map date, revenue, expenses, product, and category columns.",
        )
        if uploaded_file:
            file_size = uploaded_file.size
            size_label = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"
            st.caption(f"✓ {uploaded_file.name} · {size_label}")
    else:
        st.caption("Sample dataset · fictional demo data")
    currency_options = list(CURRENCY_OPTIONS)
    default_currency = "USD ($)" if source == "Sample data" else "No currency symbol"
    currency_label = st.selectbox(
        "Display currency (format only)",
        currency_options,
        index=currency_options.index(default_currency),
        key=f"currency_{source.replace(' ', '_').lower()}",
    )
    currency_symbol = CURRENCY_OPTIONS[currency_label]
    dataset_name = st.text_input(
        "Business or dataset name",
        value=Path(uploaded_file.name).stem if uploaded_file else "Bizlytics sample business",
    )
    st.divider()
    st.caption("Phase 2 · Business performance and reporting")

if source == "Upload a file" and uploaded_file is None:
    _show_page_header(
        "Business intelligence, made clear",
        "Your business at a glance",
        "Upload a CSV or XLSX file to explore, validate, and report on your data.",
    )
    st.info("Choose a CSV or Excel file in the sidebar to get started.")
    st.stop()

try:
    with st.spinner("Preparing your business data…"):
        raw_data = (
            load_uploaded_file(uploaded_file)
            if source == "Upload a file"
            else load_sample_data(DATA_PATH)
        )
except (ValueError, OSError, pd.errors.ParserError, ImportError) as error:
    st.error(f"Could not load the selected data: {error}")
    st.stop()

is_sample = source == "Sample data"
auto_mappings, mapping_candidates = infer_column_mappings(raw_data)
mapping_values = {}
with st.expander("Confirm or map columns", expanded=not is_sample):
    st.caption(
        "Automatic matches are suggested from column names. Confirm or change them; "
        "source headers and cell values are preserved."
    )
    mapping_columns = st.columns(2)
    options = ["Not mapped"] + list(raw_data.columns)
    for index, (field, label) in enumerate(FIELD_LABELS.items()):
        guess = auto_mappings.get(field)
        candidates = mapping_candidates[field]
        if len(candidates) > 1:
            st.warning(
                f"More than one column could represent {label.lower()}: "
                f"{', '.join(map(str, candidates))}. Choose the correct one."
            )
            guess = None
        default_index = options.index(guess) if guess in options else 0
        with mapping_columns[index % 2]:
            selected = st.selectbox(
                f"{label} column",
                options,
                index=default_index,
                key=f"mapping_{field}_{uploaded_file.name if uploaded_file else 'sample'}",
            )
        mapping_values[field] = None if selected == "Not mapped" else selected

try:
    data = apply_column_mappings(raw_data, mapping_values)
except ValueError as error:
    st.error(f"Column mapping is invalid: {error}")
    st.stop()

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
    date_range, selections, numeric_ranges = render_filters(data, "global")

filtered_data = filter_data(data, date_range, selections)
filtered_data = filter_data_by_ranges(filtered_data, numeric_ranges)
metrics = analyze_business_data(filtered_data)
filtered_quality = inspect_data_quality(filtered_data)
insights = generate_insights(filtered_data, metrics, filtered_quality, currency_symbol)

if is_sample:
    st.info("Fictional sample data — for demonstration only. Replace it with your own business data.")
if raw_data.empty:
    st.warning("This file has column headers but no business records. Review its schema or load another file.")

if page == "Overview":
    _show_page_header(
        "Business performance",
        "Your business at a glance",
        "A clear view of the numbers that matter. All metrics and charts use the filtered records.",
    )
    metric_columns = st.columns(4)
    with metric_columns[0]:
        growth_delta = (
            f"{metrics['revenue_growth']:+.1f}%"
            if metrics["revenue_growth"] is not None
            else None
        )
        show_metric(
            "Revenue",
            format_currency(metrics["total_revenue"], currency_symbol),
            metrics["availability"]["revenue"],
            delta=growth_delta,
        )
    with metric_columns[1]:
        show_metric("Expenses", format_currency(metrics["total_expenses"], currency_symbol), metrics["availability"]["expenses"])
    with metric_columns[2]:
        show_metric("Net profit", format_currency(metrics["net_profit"], currency_symbol), metrics["availability"]["profit"])
    with metric_columns[3]:
        margin = metrics["profit_margin"]
        show_metric("Profit margin", f"{margin:.1f}%" if margin is not None else None, metrics["availability"]["margin"])

    if metrics["revenue_growth"] is not None:
        st.caption("Revenue change compared with the previous available month.")
    elif metrics["availability"]["growth"]:
        st.caption(metrics["availability"]["growth"])
    for field, title in (("best_product", "Top product"), ("best_category", "Top category")):
        result = metrics[field]
        if result:
            st.caption(f"{title} by revenue: **{result[0]}** ({format_currency(result[1], currency_symbol)})")

    if filtered_data.empty:
        st.info("No records match the selected filters. Adjust the filters to see metrics and charts.")
    charts = build_charts(filtered_data, currency_symbol)
    for index in range(0, len(charts), 2):
        chart_columns = st.columns(2)
        for offset, (title, figure) in enumerate(charts[index:index + 2]):
            with chart_columns[offset]:
                st.subheader(title)
                st.plotly_chart(figure, width="stretch")
    if not charts:
        st.info("No charts can be created from the currently available columns.")
    with st.expander("Data quality"):
        render_quality(quality)

elif page == "Explore data":
    _show_page_header(
        "Explore your records",
        "Business data",
        "Filter, inspect, sort, and download the records used in your analysis.",
    )
    count_columns = st.columns(2)
    count_columns[0].metric("Source records", f"{len(data):,}")
    count_columns[1].metric("Filtered records", f"{len(filtered_data):,}")

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
            sort_column = st.selectbox("Sort by", selected_columns)
            sort_order = st.radio(
                "Sort order",
                ["Ascending", "Descending"],
                horizontal=True,
            )
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
                file_name="bizlytics_filtered_data.csv",
                mime="text/csv",
                key="download_filtered_csv",
            )

else:
    _show_page_header(
        "Decisions backed by data",
        "Insights & reports",
        "Rule-based comparisons and downloadable reports for the currently filtered dataset.",
    )
    st.caption(f"Insights and reports use {len(filtered_data):,} filtered record(s).")
    for insight in insights:
        if insight["type"] == "warning":
            st.warning(f"**{insight['title']}** — {insight['detail']}")
        elif insight["type"] == "positive":
            st.success(f"**{insight['title']}** — {insight['detail']}")
        else:
            st.info(f"**{insight['title']}** — {insight['detail']}")

    st.subheader("Download a report")
    st.caption("PDF and Excel reports include the filtered records, metrics, insights, and data-quality summary.")
    include_charts = st.multiselect(
        "Charts to include in PDF",
        ["Revenue by category"],
        default=["Revenue by category"] if mapping_values.get("category") and mapping_values.get("revenue") else [],
    )
    file_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", dataset_name.strip()).strip("_") or "bizlytics_report"
    download_columns = st.columns(3)
    download_columns[0].download_button(
        "Download records CSV",
        data=export_csv(filtered_data),
        file_name=f"{file_stem}_records.csv",
        mime="text/csv",
        key="report_csv",
    )
    download_columns[1].download_button(
        "Download Excel report",
        data=export_excel(filtered_data, dataset_name, metrics, insights, filtered_quality),
        file_name=f"{file_stem}_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="report_xlsx",
    )
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
        download_columns[2].download_button(
            "Download PDF report",
            data=pdf_data,
            file_name=f"{file_stem}_report.pdf",
            mime="application/pdf",
            key="report_pdf",
        )
