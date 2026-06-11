"""Tool: Query Business Metrics (Digital Twin)"""

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def query_metrics(metric_names: str | None = None, category: str | None = None) -> str:
    """Query current business metrics from the Digital Twin.

    Args:
        metric_names: Optional comma-separated metric names to query (e.g., "revenue,orders"). If None, returns all.
        category: Optional category filter (e.g., "revenue", "cost", "inventory", "hr", "operations")

    Returns:
        Formatted text with current metric values.
    """
    # This is a declaration tool — actual implementation is in BusinessMetricsService
    # The tool is registered for agent awareness; data is injected via orchestrator context
    return "Business metrics are available in the context. Use the context to answer metric-related questions."


@tool
def get_metric_trend(metric_name: str, periods: int = 6) -> str:
    """Get historical trend data for a specific business metric.

    Args:
        metric_name: The metric to get trend for (e.g., "revenue", "inventory_level")
        periods: Number of periods to look back (default 6)

    Returns:
        Time series data with period-to-period changes.
    """
    return f"Trend data for '{metric_name}' over {periods} periods would be retrieved from the Digital Twin."
