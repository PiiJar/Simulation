import os
import io
import time
import pandas as pd
from pathlib import Path

# Minimal Streamlit-based CSV editor for the initialization folder
# - Lists CSVs under initialization/
# - Lets you edit them in an interactive grid
# - Validates simple rules (types, duplicates)
# - Saves with automatic timestamped backups

try:
    import streamlit as st
except Exception as e:  # pragma: no cover
    raise SystemExit("Streamlit is required: pip install streamlit\n" + str(e))


INIT_DIR = Path(__file__).resolve().parents[2] / "initialization"


def _list_csvs() -> list[Path]:
    if not INIT_DIR.exists():
        return []
    return sorted([p for p in INIT_DIR.glob("*.csv") if p.is_file()])


def _read_csv(path: Path) -> pd.DataFrame:
    # Robust read: preserve strings as-is, avoid dtype surprises
    return pd.read_csv(path, dtype=str).fillna("")


def _infer_numeric_columns(df: pd.DataFrame) -> list[str]:
    numeric_cols = []
    for c in df.columns:
        # Heuristic: if all non-empty values can be parsed as float, consider numeric
        ser = df[c].astype(str)
        ok = True
        for v in ser:
            if v == "":
                continue
            try:
                float(v)
            except ValueError:
                ok = False
                break
        if ok:
            numeric_cols.append(c)
    return numeric_cols


def _validate_df(filename: str, df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Returns: (errors, warnings)
    - Generic checks: duplicate key in first column, numeric parse errors for numeric-like columns
    - File-specific hints for common schemas
    """
    errors: list[str] = []
    warnings: list[str] = []

    if df.empty:
        warnings.append("File is empty.")
        return errors, warnings

    # Duplicate check by first column (common identifier, e.g., Number/Batch/Stage)
    first_col = df.columns[0]
    dups = df[first_col][df[first_col] != ""].duplicated(keep=False)
    if dups.any():
        dup_vals = sorted(df.loc[dups, first_col].unique().tolist())
        warnings.append(f"Duplicate values in first column '{first_col}': {dup_vals}")

    # Numeric parse check
    numeric_cols = _infer_numeric_columns(df)
    for c in numeric_cols:
        try:
            pd.to_numeric(df[c].replace({"": None}))
        except Exception:
            errors.append(f"Column '{c}' contains non-numeric values but appears numeric.")

    # File-specific lightweight checks
    name = filename.lower()
    if "stations" in name:
        # Expect Number and X Position columns
        for must in ("Number", "X Position"):
            if must not in df.columns:
                errors.append(f"Missing required column: {must}")
    if "treatment_program" in name:
        # Expect Stage
        if "Stage" not in df.columns:
            errors.append("Missing required column: Stage")
    if name.endswith("production.csv"):
        for must in ("Batch", "Start_station"):
            if must not in df.columns:
                errors.append(f"Missing required column: {must}")

    return errors, warnings


def _save_with_backup(path: Path, df: pd.DataFrame) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    if path.exists():
        path.replace(backup)
    # Convert back: try to preserve numeric types for numeric-like columns
    df_out = df.copy()
    for c in _infer_numeric_columns(df_out):
        # Empty strings remain empty; otherwise cast to float, then to int if integer-like
        ser = pd.to_numeric(df_out[c].replace({"": None}), errors="coerce")
        # If all finite values are integers, cast to Int64
        if ser.dropna().apply(float.is_integer).all():
            df_out[c] = ser.astype("Int64")
        else:
            df_out[c] = ser
    df_out.to_csv(path, index=False)
    return backup


def main():
    st.set_page_config(page_title="Initialization CSV Manager", layout="wide")
    st.title("Initialization CSV Manager")
    st.caption(f"Editing files under: {INIT_DIR}")

    files = _list_csvs()
    if not files:
        st.error("No CSV files found under 'initialization/'.")
        return

    selected = st.sidebar.selectbox("Select CSV", options=[str(p.name) for p in files])
    path = INIT_DIR / selected

    df = _read_csv(path)
    st.subheader(selected)
    with st.expander("Validation", expanded=True):
        errs, warns = _validate_df(selected, df)
        if errs:
            st.error("\n".join(errs))
        if warns:
            st.warning("\n".join(warns))
        if not errs and not warns:
            st.success("No issues detected.")

    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button("Save", type="primary"):
            backup = _save_with_backup(path, edited)
            st.success(f"Saved to {path.name}. Backup created: {backup.name}")
    with col2:
        st.download_button("Download CSV", data=edited.to_csv(index=False), file_name=path.name, mime="text/csv")
    with col3:
        st.caption("Tip: Use the sidebar to switch between files. Edits are not saved until you click Save.")


if __name__ == "__main__":
    main()
