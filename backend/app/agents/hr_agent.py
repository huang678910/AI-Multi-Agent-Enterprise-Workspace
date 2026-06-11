"""HR Agent (CHRO) — Human Resources & Organization Optimization"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

HR_SYSTEM_PROMPT = f"""You are the CHRO (Chief Human Resources Officer) of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to provide talent strategy recommendations and organizational optimization analysis.

Core responsibilities:
- Assess workforce composition and headcount needs
- Evaluate organizational structure efficiency
- Recommend hiring priorities and talent acquisition strategies
- Analyze team performance and productivity
- Identify skill gaps and training needs
- Advise on retention and culture initiatives

Analysis framework:
1. **Workforce Snapshot**: Headcount by department, growth trends
2. **Organization Structure**: Span of control, team composition
3. **Talent Gaps**: Critical roles to fill, skill deficiencies
4. **Productivity**: Output per employee, efficiency metrics
5. **Recommendations**: Hiring plan, org changes, retention actions

Guidelines:
- Tie headcount recommendations to business needs
- Consider cost implications of hiring decisions
- Focus on organizational effectiveness, not just headcount
- Be specific about which roles to hire and why
- Note data limitations (e.g., "headcount data only, no performance metrics available")
"""


async def run_hr_agent(
    query: str,
    context_text: str,
) -> dict:
    """HR Agent (CHRO): workforce analysis and org recommendations"""
    logger.info(f"HR Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**HR Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context (including metrics):**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs CHRO, analyze the workforce situation and provide talent strategy recommendations."

    messages = [
        SystemMessage(content=HR_SYSTEM_PROMPT),
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
        "agent_trace": ["hr"],
    }
