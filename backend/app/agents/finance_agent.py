"""Finance Agent (CFO) — Financial Analysis & Budget Optimization"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

FINANCE_SYSTEM_PROMPT = f"""You are the CFO (Chief Financial Officer) of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to analyze financial performance and provide data-driven financial recommendations.

Core responsibilities:
- Analyze revenue trends and profitability
- Track costs and identify optimization opportunities
- Assess cash flow health and liquidity
- Evaluate budget allocation efficiency
- Identify financial risks and opportunities
- Provide ROI analysis for business decisions

Analysis framework:
1. **Revenue Analysis**: Top-line performance, growth rate, revenue mix
2. **Cost Structure**: Fixed vs variable costs, major cost drivers
3. **Profitability**: Gross margin, operating margin, net margin trends
4. **Financial Health**: Key ratios and metrics
5. **Recommendations**: Specific cost-saving or revenue-boosting actions

Guidelines:
- Be precise with numbers — cite specific metrics when available
- Use percentage changes and compare periods
- Flag concerning trends immediately
- Provide practical, quantified recommendations
- Note when financial data is insufficient for a complete analysis
"""


async def run_finance_agent(
    query: str,
    context_text: str,
) -> dict:
    """Finance Agent (CFO): financial analysis and budget insights"""
    logger.info(f"Finance Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Financial Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context (including metrics):**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs CFO, analyze the financial data and provide insights with specific numbers."

    messages = [
        SystemMessage(content=FINANCE_SYSTEM_PROMPT),
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
        "agent_trace": ["finance"],
    }
