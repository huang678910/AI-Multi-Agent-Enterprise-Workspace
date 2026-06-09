"""Analyst Agent — Data Analysis"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = f"""You are a data analyst specialist. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Analyze data and provide insights. Always use the current date, never make up dates.

Guidelines:
- Interpret the data clearly and concisely
- Identify trends, patterns, and outliers
- Provide statistical summaries when applicable
- Use Markdown tables to present structured data
- Suggest visualizations (charts, graphs) where appropriate
- Highlight key metrics and KPIs
- Note any data quality issues or limitations

Output:
- "Key Metrics" section with important numbers
- "Trends & Patterns" section
- "Anomalies" section (if any)
- "Recommendations" section
"""


async def run_analyst_agent(
    query: str,
    data_context: str,
    python_output: str = "",
) -> dict:
    """Analyst Agent：数据分析

    Args:
        query: 分析问题
        data_context: 数据上下文（SQL 查询结果、文档数据等）
        python_output: Python 执行器的输出

    Returns:
        dict with final_response, agent_trace
    """
    logger.info(f"AnalystAgent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Analysis Request:** {query}"]
    if data_context:
        prompt_parts.append(f"\n**Available Data:**\n{data_context}")
    if python_output:
        prompt_parts.append(f"\n**Python Analysis Output:**\n{python_output}")

    prompt = "\n".join(prompt_parts)
    prompt += "\n\nPlease analyze the data and provide insights."

    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    llm = _get_llm(streaming=True)
    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content

    return {
        "final_response": full_response,
        "sources": [],
        "agent_trace": ["analyst"],
    }
