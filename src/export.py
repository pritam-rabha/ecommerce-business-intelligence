from __future__ import annotations

from io import BytesIO

import pandas as pd

try:
    from src.utils import get_logger
except ImportError:
    from utils import get_logger

logger = get_logger(__name__)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to CSV bytes, suitable for st.download_button."""
    try:
        return df.to_csv(index=False).encode("utf-8")
    except Exception as exc:
        logger.error("CSV export failed: %s", exc)
        raise


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Filtered Data") -> bytes:
    """
    Serialize a DataFrame to Excel (.xlsx) bytes using openpyxl, with
    light formatting (bold header row, auto column width) for a
    professional look when opened.
    """
    try:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]

            # Bold header row
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)

            # Auto-fit column widths (approximate, based on content length)
            for i, column in enumerate(df.columns, start=1):
                max_len = max(df[column].astype(str).map(len).max() if not df.empty else 0, len(column))
                worksheet.column_dimensions[worksheet.cell(row=1, column=i).column_letter].width = min(max_len + 4, 40)

        buffer.seek(0)
        return buffer.getvalue()
    except Exception as exc:
        logger.error("Excel export failed: %s", exc)
        raise
