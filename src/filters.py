"""
filters.py
----------
Builds the sidebar filter UI and applies the selected filters to the
cleaned DataFrame. Kept separate from app.py so the filtering logic can
be unit tested without a running Streamlit session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import streamlit as st

try:
    from src.utils import get_logger
except ImportError:
    from utils import get_logger

logger = get_logger(__name__)


@dataclass
class FilterState:
    """Holds the currently selected sidebar filter values."""
    start_date: date
    end_date: date
    countries: list = field(default_factory=list)
    customer_ids: list = field(default_factory=list)
    products: list = field(default_factory=list)
    invoice_no: str = ""


def render_sidebar_filters(df: pd.DataFrame) -> FilterState:
    """
    Render all sidebar filter widgets and return the selected state.

    Args:
        df: The full cleaned DataFrame (unfiltered), used to populate
            filter option lists.

    Returns:
        A FilterState dataclass with the user's current selections.
    """
    st.sidebar.markdown("### 🔍 Filters")

    min_date = df["InvoiceDate"].min().date() if not df.empty else date.today()
    max_date = df["InvoiceDate"].max().date() if not df.empty else date.today()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # st.date_input returns a single date until both ends are picked
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    country_options = sorted(df["Country"].dropna().unique().tolist()) if not df.empty else []
    countries = st.sidebar.multiselect("Country", options=country_options, default=[])

    customer_options = sorted(df["CustomerID"].dropna().unique().tolist()) if not df.empty else []
    customer_ids = st.sidebar.multiselect("Customer ID", options=customer_options, default=[])

    product_options = sorted(df["Description"].dropna().unique().tolist()) if not df.empty else []
    products = st.sidebar.multiselect("Product", options=product_options, default=[])

    invoice_no = st.sidebar.text_input("Invoice Number contains", value="")

    if st.sidebar.button("🔄 Reset Filters", use_container_width=True):
        st.rerun()

    return FilterState(
        start_date=start_date,
        end_date=end_date,
        countries=countries,
        customer_ids=customer_ids,
        products=products,
        invoice_no=invoice_no.strip(),
    )


def apply_filters(df: pd.DataFrame, filters: FilterState) -> pd.DataFrame:
    """
    Apply a FilterState to the cleaned DataFrame and return the filtered
    subset. All filters are combined with logical AND.
    """
    if df.empty:
        return df

    filtered = df.copy()

    filtered = filtered[
        (filtered["InvoiceDate"].dt.date >= filters.start_date)
        & (filtered["InvoiceDate"].dt.date <= filters.end_date)
    ]

    if filters.countries:
        filtered = filtered[filtered["Country"].isin(filters.countries)]

    if filters.customer_ids:
        filtered = filtered[filtered["CustomerID"].isin(filters.customer_ids)]

    if filters.products:
        filtered = filtered[filtered["Description"].isin(filters.products)]

    if filters.invoice_no:
        filtered = filtered[
            filtered["InvoiceNo"].str.contains(filters.invoice_no, case=False, na=False)
        ]

    logger.info("Filters applied: %s rows -> %s rows", f"{len(df):,}", f"{len(filtered):,}")
    return filtered
