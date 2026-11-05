from pathlib import Path
import math
from zipfile import BadZipFile

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

from modules.analytics import COLUMN_ALIASES, find_column, _normalize_column


FIELD_LABELS = {
    "date": "Date",
    "revenue": "Revenue",
    "expenses": "Expenses",
    "units": "Units sold",
    "product": "Product",
    "category": "Category",
}


def _validate_dataframe(data):
    if len(data.columns) == 0:
        raise ValueError("The selected file does not contain any columns.")
    data.columns = [str(column).strip() for column in data.columns]
    if any(not column for column in data.columns):
        raise ValueError("Every column must have a non-empty header.")
    if len(set(data.columns)) != len(data.columns):
        raise ValueError("Column names must be unique.")
    return data


def infer_column_mappings(data):
    """Suggest semantic fields only when a single recognized header matches."""
    mappings = {}
    candidates = {}
    for field in FIELD_LABELS:
        matches = [
            column for column in data.columns
            if _normalize_column(column) in COLUMN_ALIASES[field]
        ]
        candidates[field] = matches
        if len(matches) == 1:
            mappings[field] = matches[0]
    return mappings, candidates


def apply_column_mappings(data, mappings):
    """Attach explicit field mappings while preserving every original header and value."""
    if any(
        source is not None and source not in data.columns
        for field, source in mappings.items()
        if field in FIELD_LABELS
    ):
        raise ValueError("A mapped source column is no longer present in the dataset.")
    selected = {field: source for field, source in mappings.items() if field in FIELD_LABELS}
    selected = {
        field: source if source in data.columns else None
        for field, source in selected.items()
    }
    selected_sources = [source for source in selected.values() if source is not None]
    if len(set(selected_sources)) != len(selected_sources):
        raise ValueError("Each business field must be mapped to a different source column.")
    result = data.copy()
    result.attrs["bizlytics_column_mapping"] = selected
    return result


def infer_column_types(data):
    """Infer readable column types while retaining the original values."""
    result = {}
    date_column = find_column(data, "date")
    numeric_fields = {
        source for field, source in data.attrs.get("bizlytics_column_mapping", {}).items()
        if field in {"revenue", "expenses", "units"} and source is not None
    }
    numeric_fields.update(
        _normalize_column(alias)
        for field in ("revenue", "expenses", "units")
        for alias in COLUMN_ALIASES[field]
    )
    for column in data.columns:
        series = data[column].dropna()
        if pd.api.types.is_bool_dtype(data[column]):
            kind = "boolean"
        elif pd.api.types.is_numeric_dtype(data[column]):
            kind = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(data[column]):
            kind = "date/time"
        elif series.empty:
            kind = "empty"
        elif column == date_column:
            parsed = pd.to_datetime(series, errors="coerce")
            kind = "date/time" if parsed.notna().mean() >= 0.5 else "text"
        else:
            numeric = pd.to_numeric(series, errors="coerce")
            normalized = _normalize_column(column)
            if numeric.notna().mean() >= 0.8 or column in numeric_fields or normalized in numeric_fields:
                kind = "numeric" if numeric.notna().all() else "numeric (with invalid values)"
            elif "date" in normalized or "time" in normalized:
                parsed = pd.to_datetime(series, errors="coerce")
                kind = "date/time" if parsed.notna().mean() >= 0.8 else "text"
            else:
                kind = "text"
        result[column] = kind
    return result


def inspect_data_quality(data):
    """Report data issues without altering or dropping source records."""
    mappings, _ = infer_column_mappings(data)
    mappings.update(data.attrs.get("bizlytics_column_mapping", {}))
    date_column = mappings.get("date")
    if date_column is None:
        date_column = next(
            (column for column in data.columns
             if pd.api.types.is_datetime64_any_dtype(data[column])),
            None,
        )
    invalid_dates = {}
    if date_column:
        values = data[date_column]
        present = values.notna() & values.astype(str).str.strip().ne("")
        parsed = pd.to_datetime(values, errors="coerce")
        count = int((present & parsed.isna()).sum())
        if count:
            invalid_dates[date_column] = count

    invalid_numeric = {}
    numeric_columns = set()
    inferred_types = infer_column_types(data)
    for column in data.columns:
        if (
            pd.api.types.is_numeric_dtype(data[column])
            and not pd.api.types.is_bool_dtype(data[column])
        ) or inferred_types.get(column, "").startswith("numeric"):
            numeric_columns.add(column)
    numeric_columns.update(
        source for field, source in mappings.items()
        if field in {"revenue", "expenses", "units"} and source is not None
    )
    for column in numeric_columns:
        values = data[column]
        present = values.notna() & values.astype(str).str.strip().ne("")
        numeric = pd.to_numeric(values, errors="coerce")
        invalid = present & (numeric.isna() | ~numeric.map(
            lambda value: pd.isna(value) or math.isfinite(value)
        ))
        count = int(invalid.sum())
        if count:
            invalid_numeric[column] = count

    missing_mask = data.isna().copy()
    for column in data.columns:
        if pd.api.types.is_object_dtype(data[column]) or pd.api.types.is_string_dtype(data[column]):
            missing_mask[column] |= data[column].astype("string").str.strip().eq("").fillna(False)
    missing = {
        str(column): int(count)
        for column, count in missing_mask.sum().items()
        if count
    }
    return {
        "row_count": int(len(data)),
        "column_count": int(len(data.columns)),
        "missing_values": missing,
        "duplicate_rows": int(data.duplicated().sum()),
        "invalid_dates": invalid_dates,
        "invalid_numeric": invalid_numeric,
    }


def load_sample_data(path):
    """Load the bundled fictional demonstration dataset."""
    data = pd.read_csv(Path(path))
    return _validate_dataframe(data)


def load_uploaded_file(uploaded_file):
    """Read an uploaded CSV or Excel workbook and validate its headers."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise ValueError("Unsupported file type. Please choose a CSV or XLSX file.")
    try:
        if suffix == ".csv":
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)
    except (
        BadZipFile,
        InvalidFileException,
        OSError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        ValueError,
    ) as error:
        raise ValueError(f"Could not read {uploaded_file.name}: {error}") from error
    return _validate_dataframe(data)
