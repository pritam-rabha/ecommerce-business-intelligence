"""
charts.py
---------
Plotly chart-building functions for the dashboard.

Every function takes a prepared DataFrame (already aggregated by
analysis.py) and returns a Plotly Figure object ready to be rendered
with `st.plotly_chart(fig, use_container_width=True)`.

A consistent color palette and template are applied throughout so the
dashboard has a coherent, professional look regardless of which chart
type is used.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    from src.utils import get_logger
except ImportError:
    from utils import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# Shared style constants
# --------------------------------------------------------------------------
COLOR_PALETTE = [
    "#2563EB", "#0EA5E9", "#06B6D4", "#10B981", "#84CC16",
    "#F59E0B", "#F97316", "#EF4444", "#EC4899", "#8B5CF6",
]
PRIMARY_COLOR = "#2563EB"
SECONDARY_COLOR = "#10B981"
ACCENT_COLOR = "#F59E0B"
TEMPLATE = "plotly_white"

CHART_LAYOUT_DEFAULTS = dict(
    template=TEMPLATE,
    font=dict(family="Segoe UI, Roboto, Arial, sans-serif", size=13, color="#1F2937"),
    margin=dict(l=40, r=20, t=60, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    colorway=COLOR_PALETTE,
    hoverlabel=dict(bgcolor="white", font_size=13),
)


def _apply_layout(fig: go.Figure, title: str) -> go.Figure:
    """Apply the shared layout/theme to a figure and set its title."""
    fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"), **CHART_LAYOUT_DEFAULTS)
    return fig


# --------------------------------------------------------------------------
# Line / Area charts (trends)
# --------------------------------------------------------------------------
def line_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> go.Figure:
    """Line chart, typically used for revenue-over-time trends."""
    fig = px.line(df, x=x, y=y, markers=True, color_discrete_sequence=[PRIMARY_COLOR])
    fig.update_traces(line=dict(width=3), hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>")
    return _apply_layout(fig, title)


def area_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> go.Figure:
    """Filled area chart, used for cumulative or volume-style trends."""
    fig = px.area(df, x=x, y=y, color_discrete_sequence=[SECONDARY_COLOR])
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>")
    return _apply_layout(fig, title)


def forecast_chart(df: pd.DataFrame, title: str = "Sales Forecast") -> go.Figure:
    """
    Line chart distinguishing actual vs. forecasted revenue, expects a
    DataFrame with columns [Period, Revenue, Type].
    """
    fig = go.Figure()
    for segment, color, dash in [("Actual", PRIMARY_COLOR, "solid"), ("Forecast", ACCENT_COLOR, "dash")]:
        subset = df[df["Type"] == segment]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["Period"], y=subset["Revenue"], mode="lines+markers", name=segment,
            line=dict(color=color, width=3, dash=dash),
        ))
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Bar charts
# --------------------------------------------------------------------------
def bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "", horizontal: bool = False) -> go.Figure:
    """Vertical or horizontal bar chart."""
    if horizontal:
        fig = px.bar(df, x=y, y=x, orientation="h", color_discrete_sequence=[PRIMARY_COLOR])
        fig.update_yaxes(categoryorder="total ascending")
    else:
        fig = px.bar(df, x=x, y=y, color_discrete_sequence=[PRIMARY_COLOR])
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>" if not horizontal else None)
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Pie / Donut charts
# --------------------------------------------------------------------------
def pie_chart(df: pd.DataFrame, names: str, values: str, title: str = "") -> go.Figure:
    """Standard pie chart."""
    fig = px.pie(df, names=names, values=values, color_discrete_sequence=COLOR_PALETTE)
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>%{value:,.2f}<extra></extra>")
    return _apply_layout(fig, title)


def donut_chart(df: pd.DataFrame, names: str, values: str, title: str = "") -> go.Figure:
    """Donut chart (pie chart with a hole), used for segment breakdowns."""
    fig = px.pie(df, names=names, values=values, hole=0.55, color_discrete_sequence=COLOR_PALETTE)
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>%{value:,.2f}<extra></extra>")
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Treemap
# --------------------------------------------------------------------------
def treemap_chart(df: pd.DataFrame, path: list, values: str, title: str = "") -> go.Figure:
    """Treemap chart, useful for hierarchical revenue breakdowns (e.g. by product)."""
    fig = px.treemap(df, path=path, values=values, color=values, color_continuous_scale="Blues")
    fig.update_traces(hovertemplate="%{label}<br>%{value:,.2f}<extra></extra>")
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Heatmap
# --------------------------------------------------------------------------
def heatmap_chart(pivot_df: pd.DataFrame, title: str = "") -> go.Figure:
    """Heatmap chart from a pivoted DataFrame (e.g. Weekday x Month revenue)."""
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values, x=pivot_df.columns, y=pivot_df.index,
        colorscale="Blues", hovertemplate="%{x} / %{y}<br>Revenue: %{z:,.2f}<extra></extra>",
    ))
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Scatter plot
# --------------------------------------------------------------------------
def scatter_chart(df: pd.DataFrame, x: str, y: str, size: str = None, color: str = None, title: str = "") -> go.Figure:
    """Scatter plot, useful for e.g. Orders vs. Revenue per customer."""
    fig = px.scatter(
        df, x=x, y=y, size=size, color=color,
        color_discrete_sequence=COLOR_PALETTE, opacity=0.75,
    )
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Histogram
# --------------------------------------------------------------------------
def histogram_chart(df: pd.DataFrame, x: str, title: str = "", nbins: int = 30) -> go.Figure:
    """Histogram, useful for order-value or basket-size distributions."""
    fig = px.histogram(df, x=x, nbins=nbins, color_discrete_sequence=[PRIMARY_COLOR])
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# Geographic map
# --------------------------------------------------------------------------
def choropleth_map(df: pd.DataFrame, locations: str, values: str, title: str = "") -> go.Figure:
    """
    Interactive world choropleth map of revenue by country.
    `locations` should contain country names (Plotly resolves them via
    its built-in country-name database).
    """
    fig = px.choropleth(
        df, locations=locations, locationmode="country names", color=values,
        color_continuous_scale="Blues", hover_name=locations,
    )
    fig.update_geos(showframe=False, showcoastlines=True, projection_type="natural earth")
    return _apply_layout(fig, title)


# --------------------------------------------------------------------------
# KPI delta indicator (used on the Executive Dashboard)
# --------------------------------------------------------------------------
def kpi_gauge(value: float, title: str = "", suffix: str = "%") -> go.Figure:
    """Small gauge/indicator chart for a single KPI with a growth delta."""
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=value,
        number={"suffix": suffix},
        delta={"reference": 0, "relative": False},
    ))
    fig.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=10), template=TEMPLATE)
    return fig
