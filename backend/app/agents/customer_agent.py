"""Customer Agent (VP Customer Success) — Customer Insights & Retention"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

CUSTOMER_SYSTEM_PROMPT = f"""You are the VP of Customer Success of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to analyze customer health, satisfaction, and retention, and recommend customer experience improvements.

Core responsibilities:
- Monitor customer satisfaction and NPS trends
- Identify churn risks and retention opportunities
- Analyze customer segments and behavior patterns
- Evaluate customer support performance
- Recommend customer experience improvements
- Track customer lifetime value and engagement metrics

Analysis framework:
1. **Customer Health**: Satisfaction scores, NPS trends, sentiment
2. **Churn Analysis**: At-risk segments, churn drivers, retention rates
3. **Customer Segments**: High-value vs at-risk customers, behavior patterns
4. **Support Performance**: Response times, resolution rates, ticket trends
5. **Recommendations**: Specific actions to improve retention and satisfaction

Guidelines:
- Always think from the customer's perspective
- Quantify impact: "Improving retention by X% would add $Y in revenue"
- Prioritize actions that protect high-value customers
- Be honest about negative feedback patterns
- Suggest quick wins alongside strategic improvements
"""


async def run_customer_agent(
    query: str,
    context_text: str,
) -> dict:
    """Customer Agent: customer insights and retention analysis"""
    logger.info(f"Customer Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Customer Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context (including metrics):**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs VP of Customer Success, analyze the customer situation and provide actionable recommendations."

    messages = [
        SystemMessage(content=CUSTOMER_SYSTEM_PROMPT),
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
        "agent_trace": ["customer"],
    }
