"""
insights.py
-----------
Generates automatic, natural-language business insights from the cleaned
DataFrame for the "Business Insights" dashboard page. Each insight is
returned as a dict of {label, value, detail} so the page can render them
as clean cards without extra parsing logic.
"""

from __future__ import annotations

import pandas as pd

try:
    from src.analysis import average_basket_size, calculate_revenue_growth
    from src.utils import format_currency, get_logger
except ImportError:
    from analysis import average_basket_size, calculate_revenue_growth
    from utils import format_currency, get_logger

logger = get_logger(__name__)


def generate_business_insights(df: pd.DataFrame) -> list[dict]:
    """
    Generate a list of auto-computed business insights.

    Returns:
        A list of dicts, each with keys: icon, label, value, detail.
    """
    if df.empty:
        return [{"icon": "⚠️", "label": "No Data", "value": "--", "detail": "No records match the current filters."}]

    insights = []

    # Highest revenue month
    monthly = df.groupby("MonthName")["TotalPrice"].sum()
    if not monthly.empty:
        best_month = monthly.idxmax()
        insights.append({
            "icon": "📅", "label": "Highest Revenue Month", "value": best_month,
            "detail": f"Generated {format_currency(monthly.max())} in revenue.",
        })

    # Best product
    product_revenue = df.groupby("Description")["TotalPrice"].sum()
    if not product_revenue.empty:
        best_product = product_revenue.idxmax()
        insights.append({
            "icon": "🏆", "label": "Best-Selling Product", "value": best_product,
            "detail": f"Generated {format_currency(product_revenue.max())} in revenue.",
        })

        worst_product = product_revenue.idxmin()
        insights.append({
            "icon": "📉", "label": "Lowest-Selling Product", "value": worst_product,
            "detail": f"Generated only {format_currency(product_revenue.min())} in revenue.",
        })

    # Highest revenue country
    country_revenue = df.groupby("Country")["TotalPrice"].sum()
    if not country_revenue.empty:
        best_country = country_revenue.idxmax()
        insights.append({
            "icon": "🌍", "label": "Top Market by Revenue", "value": best_country,
            "detail": f"Contributed {format_currency(country_revenue.max())} "
                      f"({country_revenue.max() / country_revenue.sum() * 100:.1f}% of total revenue).",
        })

    # Best customer
    customer_revenue = df.groupby("CustomerID")["TotalPrice"].sum()
    if not customer_revenue.empty:
        best_customer = customer_revenue.idxmax()
        insights.append({
            "icon": "🥇", "label": "Highest-Value Customer", "value": f"Customer #{int(best_customer)}",
            "detail": f"Spent {format_currency(customer_revenue.max())} in total.",
        })

    # Average basket size
    basket = average_basket_size(df)
    insights.append({
        "icon": "🧺", "label": "Average Basket Size", "value": f"{basket:.1f} items",
        "detail": "Average number of items purchased per invoice.",
    })

    # Growth percentage
    growth = calculate_revenue_growth(df)
    trend_word = "increase" if growth >= 0 else "decrease"
    insights.append({
        "icon": "📈" if growth >= 0 else "📉", "label": "Month-over-Month Growth",
        "value": f"{growth:+.1f}%", "detail": f"Revenue saw a {trend_word} vs. the previous month.",
    })

    return insights
