from __future__ import annotations

import pandas as pd

try:
    from src.utils import CLEAN_DATA_PATH, RAW_DATA_PATH, get_logger
except ImportError:  # allows running this file directly as a script
    from utils import CLEAN_DATA_PATH, RAW_DATA_PATH, get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country",
]


class DataCleaner:
    """Encapsulates the full raw-to-clean transformation pipeline."""

    def __init__(self, raw_path=RAW_DATA_PATH):
        self.raw_path = raw_path
        self.df: pd.DataFrame | None = None
        self.stats: dict[str, int] = {}

    def load(self) -> pd.DataFrame:
        """Load the raw CSV file into a DataFrame."""
        try:
            logger.info("Loading raw data from %s", self.raw_path)
            df = pd.read_csv(self.raw_path, encoding="utf-8")
        except UnicodeDecodeError:
            # The real Kaggle file ships with latin-1 encoding.
            logger.warning("UTF-8 decode failed, retrying with latin-1 encoding")
            df = pd.read_csv(self.raw_path, encoding="latin-1")
        except FileNotFoundError as exc:
            logger.error("Raw data file not found at %s", self.raw_path)
            raise exc

        missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Raw dataset is missing required columns: {missing_cols}")

        self.df = df
        self.stats["rows_loaded"] = len(df)
        logger.info("Loaded %s rows", f"{len(df):,}")
        return df

    def _enforce_dtypes(self) -> None:
        """Convert columns to their correct types."""
        df = self.df
        df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
        df["StockCode"] = df["StockCode"].astype(str).str.strip()
        df["Description"] = df["Description"].astype(str).str.strip().str.upper()
        df["Country"] = df["Country"].astype(str).str.strip()

        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
        df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
        df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")

        self.df = df

    def _remove_duplicates(self) -> None:
        before = len(self.df)
        self.df = self.df.drop_duplicates()
        removed = before - len(self.df)
        self.stats["duplicates_removed"] = removed
        logger.info("Removed %s duplicate rows", f"{removed:,}")

    def _remove_cancelled_orders(self) -> None:
        before = len(self.df)
        cancelled_mask = self.df["InvoiceNo"].str.startswith("C", na=False)
        self.df = self.df.loc[~cancelled_mask].copy()
        removed = before - len(self.df)
        self.stats["cancelled_orders_removed"] = removed
        logger.info("Removed %s cancelled orders", f"{removed:,}")

    def _remove_invalid_rows(self) -> None:
        before = len(self.df)
        invalid_mask = (
            self.df["Quantity"].isna()
            | (self.df["Quantity"] <= 0)
            | self.df["UnitPrice"].isna()
            | (self.df["UnitPrice"] <= 0)
            | self.df["InvoiceDate"].isna()
        )
        self.df = self.df.loc[~invalid_mask].copy()
        removed = before - len(self.df)
        self.stats["invalid_rows_removed"] = removed
        logger.info("Removed %s rows with invalid quantity/price/date", f"{removed:,}")

    def _handle_missing_values(self) -> None:
        before = len(self.df)
        # Rows without a CustomerID cannot support customer-level analytics
        # (CLV, segmentation, top customers), so they are dropped. This
        # mirrors standard practice for this dataset.
        self.df = self.df.dropna(subset=["CustomerID"]).copy()
        self.df["CustomerID"] = self.df["CustomerID"].astype(int)

        # A missing description doesn't invalidate the transaction; fill
        # with a placeholder so downstream groupby operations don't drop it.
        self.df["Description"] = self.df["Description"].fillna("UNKNOWN ITEM")

        removed = before - len(self.df)
        self.stats["missing_customer_rows_removed"] = removed
        logger.info("Removed %s rows with missing CustomerID", f"{removed:,}")

    def _create_derived_columns(self) -> None:
        df = self.df
        df["TotalPrice"] = (df["Quantity"] * df["UnitPrice"]).round(2)
        df["Year"] = df["InvoiceDate"].dt.year
        df["Month"] = df["InvoiceDate"].dt.month
        df["MonthName"] = df["InvoiceDate"].dt.strftime("%b %Y")
        df["Day"] = df["InvoiceDate"].dt.day
        df["Weekday"] = df["InvoiceDate"].dt.day_name()
        df["Week"] = df["InvoiceDate"].dt.isocalendar().week
        df["Date"] = df["InvoiceDate"].dt.date
        self.df = df

    def clean(self) -> pd.DataFrame:
        """Run the full cleaning pipeline and return the cleaned DataFrame."""
        if self.df is None:
            self.load()

        logger.info("Starting data cleaning pipeline")
        self._enforce_dtypes()
        self._remove_duplicates()
        self._remove_cancelled_orders()
        self._remove_invalid_rows()
        self._handle_missing_values()
        self._create_derived_columns()

        self.stats["rows_final"] = len(self.df)
        logger.info(
            "Cleaning complete: %s rows -> %s rows",
            f"{self.stats['rows_loaded']:,}",
            f"{self.stats['rows_final']:,}",
        )
        return self.df

    def save(self, output_path=CLEAN_DATA_PATH) -> None:
        """Persist the cleaned DataFrame to CSV."""
        if self.df is None:
            raise RuntimeError("Nothing to save -- call clean() first")
        self.df.to_csv(output_path, index=False)
        logger.info("Saved cleaned data to %s", output_path)


def run_cleaning_pipeline(raw_path=RAW_DATA_PATH, output_path=CLEAN_DATA_PATH) -> pd.DataFrame:
    """Convenience function: load, clean, and save in one call."""
    cleaner = DataCleaner(raw_path=raw_path)
    cleaner.load()
    cleaner.clean()
    cleaner.save(output_path=output_path)
    return cleaner.df


if __name__ == "__main__":
    run_cleaning_pipeline()
