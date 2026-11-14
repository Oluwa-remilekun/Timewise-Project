"""Plotly figures used by the dashboard pages."""

from datetime import date

import plotly.graph_objects as go

from timewise.analytics import format_duration
from timewise.constants import ACTIVITY_CATEGORY_COLORS

_COMPLETED_COLOR = "#12a594"
_REMAINING_COLOR = "#e9e2d6"
_TRANSPARENT = "rgba(0, 0, 0, 0)"
_BASE_LAYOUT = {
    "margin": {"t": 10, "b": 10, "l": 10, "r": 10},
    "height": 270,
    "paper_bgcolor": _TRANSPARENT,
    "plot_bgcolor": _TRANSPARENT,
}


def _donut(labels: list[str], values: list[int], colors: list[str], center_text: str):
    figure = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.68,
            marker={"colors": colors, "line": {"color": "#fbf8f3", "width": 4}},
            sort=False,
            textinfo="none",
            hovertemplate="%{label}: %{percent}<extra></extra>",
        )
    )
    figure.update_layout(
        annotations=[{"text": f"<b>{center_text}</b>", "showarrow": False, "font": {"size": 24}}],
        legend={"orientation": "h", "y": -0.05, "x": 0.5, "xanchor": "center"},
        **_BASE_LAYOUT,
    )
    return figure


def category_donut(summary: dict[str, int]) -> go.Figure:
    """Share of the day's tracked time per activity category."""
    return _donut(
        labels=list(summary),
        values=list(summary.values()),
        colors=[ACTIVITY_CATEGORY_COLORS[category] for category in summary],
        center_text=format_duration(sum(summary.values())),
    )


def completion_donut(completed: int, total: int, center_text: str) -> go.Figure:
    """Completed versus remaining tasks."""
    return _donut(
        labels=["Completed", "Remaining"],
        values=[completed, total - completed],
        colors=[_COMPLETED_COLOR, _REMAINING_COLOR],
        center_text=center_text,
    )


def daily_trend_bars(trend: dict[date, dict[str, int]]) -> go.Figure:
    """Stacked hours per category for each day in the trend."""
    days = [f"{day:%a} {day.day}" for day in trend]
    figure = go.Figure()
    for category, color in ACTIVITY_CATEGORY_COLORS.items():
        figure.add_bar(
            name=category,
            x=days,
            y=[round(totals[category] / 60, 2) for totals in trend.values()],
            marker={"color": color, "cornerradius": 6},
            hovertemplate="%{y} h<extra>" + category + "</extra>",
        )
    figure.update_layout(
        barmode="stack",
        bargap=0.35,
        yaxis={"title": "Hours", "gridcolor": "#e9e2d6"},
        legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        **_BASE_LAYOUT,
    )
    return figure
