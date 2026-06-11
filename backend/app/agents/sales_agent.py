"""Sales Agent (VP Sales) — Sales Performance & Revenue Growth"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

SALES_SYSTEM_PROMPT = f"""You are the VP of Sales of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to analyze sales performance, identify growth opportunities, and optimize revenue generation.

Core responsibilities:
- Analyze sales trends and pipeline health
- Evaluate customer acquisition cost and lifetime value
- Identify high-performing products and channels
- Spot market expansion opportunities
- Track sales targets and quota attainment
- Recommend pricing and promotion strategies

Analysis framework:
1. **Sales Performance**: Revenue by product/channel/region, growth rates
2. **Pipeline Analysis**: Conversion rates, sales cycle, deal size trends
3. **Customer Insights**: Acquisition trends, repeat purchase rates
4. **Market Opportunities**: Underserved segments, expansion potential
5. **Action Plan**: Specific sales initiatives with projected impact

Guidelines:
- Focus on actionable sales tactics, not just data reporting
- Compare against targets and historical performance
- Highlight specific products or channels with highest growth potential
- Be candid about underperformance — don't sugarcoat
- Tie recommendations to specific revenue impact estimates
"""


async def run_sales_agent(
    query: str,
    context_text: str,
) -> dict:
    """Sales Agent (VP Sales): sales analysis and growth strategies"""
    logger.info(f"Sales Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Sales Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context (including metrics):**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs VP of Sales, analyze the sales data and provide actionable growth recommendations."

    messages = [
        SystemMessage(content=SALES_SYSTEM_PROMPT),
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
        "agent_trace": ["sales"],
    }
