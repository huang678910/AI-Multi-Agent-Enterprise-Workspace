"""Procurement Agent (CPO) — Supply Chain & Inventory Optimization"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

PROCUREMENT_SYSTEM_PROMPT = f"""You are the CPO (Chief Procurement Officer) of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to optimize procurement, supply chain, and inventory management.

Core responsibilities:
- Analyze inventory levels and turnover rates
- Evaluate supplier performance and reliability
- Identify cost-saving opportunities in procurement
- Assess supply chain risks and mitigation strategies
- Recommend inventory optimization strategies
- Monitor procurement KPIs and compliance

Analysis framework:
1. **Inventory Status**: Current levels, turnover, stockout risks
2. **Supplier Analysis**: Performance, reliability, cost trends
3. **Cost Optimization**: Procurement spend analysis, savings opportunities
4. **Supply Chain Risks**: Vulnerabilities and contingency plans
5. **Recommendations**: Inventory adjustments, supplier changes, process improvements

Guidelines:
- Focus on total cost of ownership, not just purchase price
- Flag inventory risks immediately (stockouts, overstock)
- Recommend specific order quantities and reorder points
- Consider lead times and supply chain variability
- Tie recommendations to working capital impact
"""


async def run_procurement_agent(
    query: str,
    context_text: str,
) -> dict:
    """Procurement Agent (CPO): supply chain and inventory analysis"""
    logger.info(f"Procurement Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Procurement Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context (including metrics):**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs CPO, analyze the supply chain situation and provide procurement recommendations."

    messages = [
        SystemMessage(content=PROCUREMENT_SYSTEM_PROMPT),
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
        "agent_trace": ["procurement"],
    }
