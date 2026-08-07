"""
analysis.py
-----------
Pandas-based analytical functions that power every dashboard page.

All functions are pure (take a DataFrame in, return a DataFrame/scalar out)
so they are easy to unit test and easy to cache with Streamlit's
`@st.cache_data` decorator at the call site in app.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from src.utils import get_logger
except ImportError:
    from utils import get_logger

logger = get_logger(__name__)

# Executive Dashboard
def get_kpi_summary(df: pd.DataFrame) -> dict:
    """
    Compute headline KPIs for the Executive Dashboard.

    Returns:
        dict with total_revenue, total_orders, total_customers,
        total_products, avg_order_value, revenue_growth_pct.
    """
    if df.empty:
        return {
            "total_revenue": 0.0, "total_orders": 0, "total_customers": 0,
            "total_products": 0, "avg_order_value": 0.0, "revenue_growth_pct": 0.0,
        }

    total_revenue = df["TotalPrice"].sum()
    total_orders = df["InvoiceNo"].nunique()
    total_customers = df["CustomerID"].nunique()
    total_products = df["StockCode"].nunique()
    avg_order_value = total_revenue / total_orders if total_orders else 0.0

    growth_pct = calculate_revenue_growth(df)

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_products": total_products,
        "avg_order_value": avg_order_value,
        "revenue_growth_pct": growth_pct,
    }


def calculate_revenue_growth(df: pd.DataFrame) -> float:
    """Percentage change in revenue between the two most recent full months present."""
    if df.empty:
        return 0.0

    monthly = (
        df.assign(period=df["InvoiceDate"].dt.to_period("M"))
        .groupby("period")["TotalPrice"].sum()
        .sort_index()
    )
    if len(monthly) < 2:
        return 0.0

    latest, previous = monthly.iloc[-1], monthly.iloc[-2]
    if previous == 0:
        return 0.0
    return round(((latest - previous) / previous) * 100, 2)

# Sales Analytics
def revenue_by_period(df: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """
    Aggregate revenue by time period.

    Args:
        freq: pandas offset alias -- 'D' for daily, 'W' for weekly,
            'ME' for month-end (monthly). Using the modern 'ME'/'W'/'D'
            aliases required by pandas >= 2.2 (the legacy 'M' alias was
            removed).
    """
    if df.empty:
        return pd.DataFrame(columns=["Period", "Revenue"])

    series = (
        df.set_index("InvoiceDate")["TotalPrice"]
        .resample(freq)
        .sum()
        .reset_index()
        .rename(columns={"InvoiceDate": "Period", "TotalPrice": "Revenue"})
    )
    return series


def sales_forecast_sma(df: pd.DataFrame, window: int = 3, periods_ahead: int = 3) -> pd.DataFrame:
    """
    Simple moving-average forecast on monthly revenue.

    Projects `periods_ahead` future months forward using the average of
    the trailing `window` months as a naive forecast baseline.

    Returns:
        DataFrame with columns [Period, Revenue, Type] where Type is
        'Actual' or 'Forecast'.
    """
    monthly = revenue_by_period(df, freq="ME")
    if monthly.empty or len(monthly) < window:
        return pd.DataFrame(columns=["Period", "Revenue", "Type"])

    monthly["Type"] = "Actual"

    history = monthly["Revenue"].tolist()
    last_period = monthly["Period"].iloc[-1]
    forecast_rows = []

    for _ in range(periods_ahead):
        forecast_value = float(np.mean(history[-window:]))
        last_period = (last_period.to_period("M") + 1).to_timestamp()
        forecast_rows.append({"Period": last_period, "Revenue": forecast_value, "Type": "Forecast"})
        history.append(forecast_value)

    forecast_df = pd.DataFrame(forecast_rows)
    return pd.concat([monthly, forecast_df], ignore_index=True)

# Customer Analytics
def top_customers(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Rank customers by total revenue contributed."""
    if df.empty:
        return pd.DataFrame(columns=["CustomerID", "Revenue", "Orders"])

    result = (
        df.groupby("CustomerID")
        .agg(Revenue=("TotalPrice", "sum"), Orders=("InvoiceNo", "nunique"))
        .sort_values("Revenue", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return result


def new_vs_returning_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each customer as 'New' or 'Returning' based on order count,
    then summarize revenue and customer count per segment.

    A customer with exactly 1 distinct invoice is treated as 'New';
    2 or more is 'Returning'.
    """
    if df.empty:
        return pd.DataFrame(columns=["Segment", "Customers", "Revenue"])

    orders_per_customer = df.groupby("CustomerID")["InvoiceNo"].nunique()
    segment_map = orders_per_customer.apply(lambda n: "New" if n == 1 else "Returning")

    merged = df.merge(
        segment_map.rename("Segment"), left_on="CustomerID", right_index=True
    )
    summary = (
        merged.groupby("Segment")
        .agg(Customers=("CustomerID", "nunique"), Revenue=("TotalPrice", "sum"))
        .reset_index()
    )
    return summary


def customer_lifetime_value(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """
    Simplified CLV: total historical revenue per customer combined with
    purchase frequency and average order value.
    """
    if df.empty:
        return pd.DataFrame(columns=["CustomerID", "CLV", "Orders", "AvgOrderValue"])

    grouped = df.groupby("CustomerID").agg(
        CLV=("TotalPrice", "sum"),
        Orders=("InvoiceNo", "nunique"),
    )
    grouped["AvgOrderValue"] = (grouped["CLV"] / grouped["Orders"]).round(2)
    return grouped.sort_values("CLV", ascending=False).head(top_n).reset_index()


def customer_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple RFM-style value segmentation using quartiles of total spend:
    'Low Value', 'Mid Value', 'High Value', 'Top Value'.
    """
    if df.empty:
        return pd.DataFrame(columns=["CustomerID", "Revenue", "Segment"])

    spend = df.groupby("CustomerID")["TotalPrice"].sum().reset_index()
    spend.columns = ["CustomerID", "Revenue"]

    try:
        spend["Segment"] = pd.qcut(
            spend["Revenue"], q=4, labels=["Low Value", "Mid Value", "High Value", "Top Value"]
        )
    except ValueError:
        # Not enough unique values for 4 quantile bins (small dataset)
        spend["Segment"] = "Unsegmented"

    return spend

# Product Analytics
def top_products(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Rank products by revenue generated."""
    if df.empty:
        return pd.DataFrame(columns=["Description", "Revenue", "QuantitySold"])

    result = (
        df.groupby("Description")
        .agg(Revenue=("TotalPrice", "sum"), QuantitySold=("Quantity", "sum"))
        .sort_values("Revenue", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return result


def bottom_products(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Identify the lowest revenue-generating products (excluding zero-revenue noise)."""
    if df.empty:
        return pd.DataFrame(columns=["Description", "Revenue", "QuantitySold"])

    grouped = df.groupby("Description").agg(
        Revenue=("TotalPrice", "sum"), QuantitySold=("Quantity", "sum")
    )
    return grouped.sort_values("Revenue", ascending=True).head(top_n).reset_index()


def revenue_by_product(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Alias-style helper for the Product Analytics revenue breakdown chart."""
    return top_products(df, top_n=top_n)

# Geographic Analytics
def revenue_by_country(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Aggregate revenue and order counts by country."""
    if df.empty:
        return pd.DataFrame(columns=["Country", "Revenue", "Orders"])

    result = (
        df.groupby("Country")
        .agg(Revenue=("TotalPrice", "sum"), Orders=("InvoiceNo", "nunique"))
        .sort_values("Revenue", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return result

# Cross-cutting helpers
def average_basket_size(df: pd.DataFrame) -> float:
    """Average number of items (Quantity) per invoice."""
    if df.empty:
        return 0.0
    per_invoice = df.groupby("InvoiceNo")["Quantity"].sum()
    return round(float(per_invoice.mean()), 2)


def revenue_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot table of revenue by Weekday x Month, used for the heatmap chart."""
    if df.empty:
        return pd.DataFrame()

    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = df.pivot_table(
        index="Weekday", columns="MonthName", values="TotalPrice", aggfunc="sum", fill_value=0
    )
    pivot = pivot.reindex([d for d in weekday_order if d in pivot.index])
    return pivot
