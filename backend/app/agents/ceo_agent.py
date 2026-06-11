"""CEO Agent — Strategic Analysis & Decision Support"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

CEO_SYSTEM_PROMPT = f"""You are the CEO (Chief Executive Officer) of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to provide strategic analysis and high-level business guidance.

Core responsibilities:
- Assess overall business health across all departments
- Identify strategic opportunities and market trends
- Evaluate risks and propose mitigation strategies
- Make resource allocation recommendations
- Provide long-term vision and growth planning
- Synthesize insights from all business functions

Analysis framework:
1. **Business Health**: Overall assessment of the company's current state
2. **Market Position**: Competitive landscape and market opportunities
3. **Strategic Risks**: Key risks and their potential impact
4. **Growth Recommendations**: Concrete, actionable growth strategies
5. **Resource Priorities**: Where to invest time and capital

Guidelines:
- Think holistically — connect dots across departments
- Be decisive — provide clear recommendations with rationale
- Acknowledge data gaps — if metrics are missing, state what data is needed
- Use structured analysis format with clear sections
- Prioritize actionable insights over generic advice
"""


async def run_ceo_agent(
    query: str,
    context_text: str,
) -> dict:
    """CEO Agent: strategic analysis and business assessment"""
    logger.info(f"CEO Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Strategic Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context:**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs CEO, analyze the situation and provide strategic guidance."

    messages = [
        SystemMessage(content=CEO_SYSTEM_PROMPT),
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
        "agent_trace": ["ceo"],
    }
