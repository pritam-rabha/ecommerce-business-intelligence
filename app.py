"""
app.py
------
E-Commerce Business Intelligence Platform
Main Streamlit application entry point.

Run with:
    streamlit run app.py

The app is organized as a single-file multi-page dashboard using a
sidebar radio for navigation (kept in one file, rather than Streamlit's
native /pages folder, so the whole app is easy to review end-to-end for
resume/portfolio purposes). All heavy logic lives in src/ modules; this
file is primarily responsible for layout, caching, and wiring pages
together.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make src/ importable regardless of the working directory streamlit is
# launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import analysis as an
from src import charts as ch
from src import insights as ins
from src.data_cleaning import run_cleaning_pipeline
from src.database import OrderQueries, build_database_from_clean_csv
from src.export import to_csv_bytes, to_excel_bytes
from src.filters import apply_filters, render_sidebar_filters
from src.utils import (
    CLEAN_DATA_PATH, RAW_DATA_PATH, format_currency, format_number,
    format_percentage, get_logger,
)

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# Page configuration & global style
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="E-Commerce BI Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    /* ---- General layout ---- */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* ---- KPI cards ---- */
    .kpi-card {
        background: var(--background-color, #ffffff);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        height: 100%;
    }
    .kpi-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    .kpi-delta-positive { color: #16A34A; font-weight: 600; font-size: 0.85rem; }
    .kpi-delta-negative { color: #DC2626; font-weight: 600; font-size: 0.85rem; }

    /* ---- Insight cards ---- */
    .insight-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%);
        border-left: 4px solid #2563EB;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
    }
    .insight-label { font-weight: 700; color: #1E3A8A; font-size: 0.95rem; }
    .insight-value { font-size: 1.1rem; font-weight: 600; color: #0F172A; margin: 0.15rem 0; }
    .insight-detail { font-size: 0.85rem; color: #475569; }

    /* ---- Sidebar branding ---- */
    .sidebar-brand {
        display: flex; align-items: center; gap: 0.6rem;
        padding: 0.5rem 0 1rem 0; border-bottom: 1px solid rgba(148,163,184,0.25);
        margin-bottom: 1rem;
    }
    .sidebar-brand-title { font-weight: 700; font-size: 1.05rem; color: #0F172A; }
    .sidebar-brand-subtitle { font-size: 0.75rem; color: #64748B; }

    h1, h2, h3 { color: #0F172A; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Cached data loading pipeline
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and cleaning data...")
def load_clean_data() -> pd.DataFrame:
    """
    Load the cleaned dataset, running the cleaning pipeline if a cleaned
    CSV doesn't already exist. Cached so this expensive step only runs
    once per session (or when the underlying file changes).
    """
    if CLEAN_DATA_PATH.exists():
        df = pd.read_csv(
            CLEAN_DATA_PATH,
            parse_dates=["InvoiceDate"],
            dtype={"InvoiceNo": str, "StockCode": str},
        )
        logger.info("Loaded pre-cleaned data from cache file (%s rows)", f"{len(df):,}")
    else:
        if not RAW_DATA_PATH.exists():
            st.error(
                f"Raw data file not found at `{RAW_DATA_PATH}`. "
                "Please add orders.csv to the data/ folder (see README for the dataset link)."
            )
            st.stop()
        df = run_cleaning_pipeline()
    return df


@st.cache_resource(show_spinner="Initializing database...")
def get_database_queries() -> OrderQueries:
    """Build (or reconnect to) the SQLite database and return a query helper."""
    engine = build_database_from_clean_csv()
    return OrderQueries(engine)


# --------------------------------------------------------------------------
# Reusable UI components
# --------------------------------------------------------------------------
def kpi_card(label: str, value: str, delta: str | None = None, positive: bool = True) -> str:
    """Return HTML for a single KPI card."""
    delta_html = ""
    if delta:
        css_class = "kpi-delta-positive" if positive else "kpi-delta-negative"
        arrow = "▲" if positive else "▼"
        delta_html = f'<div class="{css_class}">{arrow} {delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def render_kpi_row(kpis: dict) -> None:
    """Render the six headline KPI cards in a responsive grid."""
    cols = st.columns(6)
    growth = kpis["revenue_growth_pct"]
    cards = [
        ("Total Revenue", format_currency(kpis["total_revenue"]), None, True),
        ("Total Orders", format_number(kpis["total_orders"]), None, True),
        ("Total Customers", format_number(kpis["total_customers"]), None, True),
        ("Total Products", format_number(kpis["total_products"]), None, True),
        ("Avg Order Value", format_currency(kpis["avg_order_value"]), None, True),
        ("Revenue Growth (MoM)", format_percentage(growth), format_percentage(growth), growth >= 0),
    ]
    for col, (label, value, delta, positive) in zip(cols, cards):
        with col:
            st.markdown(kpi_card(label, value, delta, positive), unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div style="font-size:1.8rem;">🛍️</div>
            <div>
                <div class="sidebar-brand-title">RetailIQ Analytics</div>
                <div class="sidebar-brand-subtitle">E-Commerce BI Platform</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_export_section(df: pd.DataFrame) -> None:
    """Render CSV/Excel download buttons for the currently filtered data."""
    st.markdown("#### ⬇️ Export Filtered Data")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV", data=to_csv_bytes(df), file_name="filtered_orders.csv",
            mime="text/csv", use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Excel", data=to_excel_bytes(df), file_name="filtered_orders.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# --------------------------------------------------------------------------
# Dashboard pages
# --------------------------------------------------------------------------
def page_executive_dashboard(df: pd.DataFrame) -> None:
    st.title("Executive Dashboard")
    st.caption("A high-level overview of business performance for the selected period.")

    kpis = an.get_kpi_summary(df)
    render_kpi_row(kpis)
    st.markdown("---")

    col1, col2 = st.columns((2, 1))
    with col1:
        monthly_revenue = an.revenue_by_period(df, freq="ME")
        fig = ch.area_chart(monthly_revenue, x="Period", y="Revenue", title="Revenue Trend (Monthly)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        top_c = an.revenue_by_country(df, top_n=6)
        fig = ch.donut_chart(top_c, names="Country", values="Revenue", title="Revenue Share by Country")
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        top_p = an.top_products(df, top_n=8)
        fig = ch.bar_chart(top_p, x="Description", y="Revenue", title="Top Products by Revenue", horizontal=True)
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        top_cust = an.top_customers(df, top_n=8)
        top_cust["CustomerID"] = top_cust["CustomerID"].astype(str)
        fig = ch.bar_chart(top_cust, x="CustomerID", y="Revenue", title="Top Customers by Revenue", horizontal=True)
        st.plotly_chart(fig, use_container_width=True)


def page_sales_analytics(df: pd.DataFrame) -> None:
    st.title("Sales Analytics")
    st.caption("Revenue trends across different time granularities, plus a simple forecast.")

    tab1, tab2, tab3, tab4 = st.tabs(["Monthly", "Weekly", "Daily", "Forecast"])
    with tab1:
        monthly = an.revenue_by_period(df, freq="ME")
        st.plotly_chart(ch.line_chart(monthly, "Period", "Revenue", "Monthly Revenue"), use_container_width=True)
    with tab2:
        weekly = an.revenue_by_period(df, freq="W")
        st.plotly_chart(ch.line_chart(weekly, "Period", "Revenue", "Weekly Revenue"), use_container_width=True)
    with tab3:
        daily = an.revenue_by_period(df, freq="D")
        st.plotly_chart(ch.area_chart(daily, "Period", "Revenue", "Daily Revenue"), use_container_width=True)
    with tab4:
        window = st.slider("Moving average window (months)", 2, 6, 3)
        periods = st.slider("Months to forecast", 1, 6, 3)
        forecast = an.sales_forecast_sma(df, window=window, periods_ahead=periods)
        if forecast.empty:
            st.info("Not enough monthly history to generate a forecast for the current filter selection.")
        else:
            st.plotly_chart(ch.forecast_chart(forecast), use_container_width=True)
            st.caption(
                f"Forecast uses a {window}-month simple moving average, "
                "a lightweight baseline appropriate for exploratory analysis "
                "(not a substitute for a production forecasting model)."
            )


def page_customer_analytics(df: pd.DataFrame) -> None:
    st.title("Customer Analytics")
    st.caption("Who your customers are, and where the value is concentrated.")

    col1, col2 = st.columns(2)
    with col1:
        top_cust = an.top_customers(df, top_n=10)
        top_cust["CustomerID"] = top_cust["CustomerID"].astype(str)
        st.plotly_chart(
            ch.bar_chart(top_cust, x="CustomerID", y="Revenue", title="Top 10 Customers", horizontal=True),
            use_container_width=True,
        )
    with col2:
        segment_df = an.new_vs_returning_customers(df)
        st.plotly_chart(
            ch.donut_chart(segment_df, names="Segment", values="Customers", title="New vs. Returning Customers"),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        clv = an.customer_lifetime_value(df, top_n=10)
        clv["CustomerID"] = clv["CustomerID"].astype(str)
        st.plotly_chart(
            ch.bar_chart(clv, x="CustomerID", y="CLV", title="Top 10 by Customer Lifetime Value (simplified)"),
            use_container_width=True,
        )
    with col4:
        seg = an.customer_segmentation(df)
        seg_summary = seg.groupby("Segment", observed=True).size().reset_index(name="Customers")
        st.plotly_chart(
            ch.pie_chart(seg_summary, names="Segment", values="Customers", title="Customer Value Segmentation"),
            use_container_width=True,
        )
    st.caption(
        "Segments are quartile-based on total historical spend: Low / Mid / High / Top Value. "
        "CLV here is a simplified historical-spend proxy, not a predictive lifetime value model."
    )


def page_product_analytics(df: pd.DataFrame) -> None:
    st.title("Product Analytics")
    st.caption("Which products drive revenue, and which are underperforming.")

    col1, col2 = st.columns(2)
    with col1:
        top_p = an.top_products(df, top_n=10)
        st.plotly_chart(
            ch.bar_chart(top_p, x="Description", y="Revenue", title="Top 10 Products by Revenue", horizontal=True),
            use_container_width=True,
        )
    with col2:
        bottom_p = an.bottom_products(df, top_n=10)
        st.plotly_chart(
            ch.bar_chart(bottom_p, x="Description", y="Revenue", title="Bottom 10 Products by Revenue", horizontal=True),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        treemap_df = an.revenue_by_product(df, top_n=20)
        st.plotly_chart(
            ch.treemap_chart(treemap_df, path=["Description"], values="Revenue", title="Revenue Breakdown (Top 20 Products)"),
            use_container_width=True,
        )
    with col4:
        qty_df = top_p.sort_values("QuantitySold", ascending=False)
        st.plotly_chart(
            ch.bar_chart(qty_df, x="Description", y="QuantitySold", title="Quantity Sold (Top 10 by Revenue)", horizontal=True),
            use_container_width=True,
        )


def page_geographic_analytics(df: pd.DataFrame) -> None:
    st.title("Geographic Analytics")
    st.caption("Where in the world revenue and orders are coming from.")

    country_df = an.revenue_by_country(df, top_n=20)

    st.plotly_chart(
        ch.choropleth_map(country_df, locations="Country", values="Revenue", title="Revenue by Country (World Map)"),
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            ch.bar_chart(country_df.head(10), x="Country", y="Revenue", title="Top 10 Countries by Revenue", horizontal=True),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            ch.bar_chart(country_df.head(10), x="Country", y="Orders", title="Top 10 Countries by Order Count", horizontal=True),
            use_container_width=True,
        )

    st.markdown("#### Revenue Heatmap: Weekday vs. Month")
    heatmap_df = an.revenue_heatmap_data(df)
    if not heatmap_df.empty:
        st.plotly_chart(ch.heatmap_chart(heatmap_df, title="Revenue by Weekday and Month"), use_container_width=True)


def page_business_insights(df: pd.DataFrame) -> None:
    st.title("Business Insights")
    st.caption("Automatically generated insights based on the current filtered dataset.")

    insights = ins.generate_business_insights(df)
    cols = st.columns(2)
    for i, insight in enumerate(insights):
        icon = insight.get("icon", "ℹ️")
        label = insight.get("label", "Insight")
        value = insight.get("value", "--")
        detail = insight.get("detail", "")
        with cols[i % 2]:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-label">{icon} {label}</div>
                    <div class="insight-value">{value}</div>
                    <div class="insight-detail">{detail}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("#### Order Value Distribution")
    order_values = df.groupby("InvoiceNo")["TotalPrice"].sum().reset_index()
    st.plotly_chart(
        ch.histogram_chart(order_values, x="TotalPrice", title="Distribution of Order Values"),
        use_container_width=True,
    )

    st.markdown("#### Orders vs. Revenue per Customer")
    scatter_df = df.groupby("CustomerID").agg(
        Orders=("InvoiceNo", "nunique"), Revenue=("TotalPrice", "sum")
    ).reset_index()
    st.plotly_chart(
        ch.scatter_chart(scatter_df, x="Orders", y="Revenue", size="Revenue", title="Customer Orders vs. Revenue"),
        use_container_width=True,
    )


def page_data_explorer(df: pd.DataFrame, db_queries: OrderQueries | None) -> None:
    st.title("Data Explorer & Export")
    st.caption("Inspect the filtered dataset directly and export it, or preview live database query results.")

    st.markdown("#### Filtered Data Preview")
    st.dataframe(df.head(500), use_container_width=True, height=350)
    render_export_section(df)

    if db_queries is not None:
        st.markdown("---")
        st.markdown("#### Database Snapshot (SQLite, unfiltered)")
        st.caption("Read directly from the `orders` table via SQLAlchemy to demonstrate the database layer.")
        db_col1, db_col2, db_col3, db_col4 = st.columns(4)
        db_col1.metric("DB Revenue", format_currency(db_queries.total_revenue()))
        db_col2.metric("DB Orders", format_number(db_queries.total_orders()))
        db_col3.metric("DB Customers", format_number(db_queries.total_customers()))
        db_col4.metric("DB Products", format_number(db_queries.total_products()))
        st.dataframe(db_queries.top_products(10), use_container_width=True)


# --------------------------------------------------------------------------
# Main application flow
# --------------------------------------------------------------------------
def main() -> None:
    render_sidebar_brand()

    df_full = load_clean_data()

    filters = render_sidebar_filters(df_full)
    df_filtered = apply_filters(df_full, filters)

    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Navigate",
        [
            "Executive Dashboard", "Sales Analytics", "Customer Analytics",
            "Product Analytics", "Geographic Analytics", "Business Insights",
            "Data Explorer",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Showing **{len(df_filtered):,}** of **{len(df_full):,}** records")
    st.sidebar.caption("Built with Streamlit, Pandas, Plotly & SQLAlchemy")

    if df_filtered.empty:
        st.warning("No records match the current filter selection. Try widening the date range or filters.")
        return

    try:
        db_queries = get_database_queries()
    except Exception as exc:
        logger.error("Database layer unavailable: %s", exc)
        db_queries = None

    pages = {
        "Executive Dashboard": lambda: page_executive_dashboard(df_filtered),
        "Sales Analytics": lambda: page_sales_analytics(df_filtered),
        "Customer Analytics": lambda: page_customer_analytics(df_filtered),
        "Product Analytics": lambda: page_product_analytics(df_filtered),
        "Geographic Analytics": lambda: page_geographic_analytics(df_filtered),
        "Business Insights": lambda: page_business_insights(df_filtered),
        "Data Explorer": lambda: page_data_explorer(df_filtered, db_queries),
    }
    pages[page]()


if __name__ == "__main__":
    main()
