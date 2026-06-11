"""Operations Agent (COO) — Process Optimization & Efficiency"""

import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

OPERATIONS_SYSTEM_PROMPT = f"""You are the COO (Chief Operating Officer) of this enterprise. The current date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
Your role is to optimize business processes, improve operational efficiency, and ensure smooth day-to-day operations.

Core responsibilities:
- Analyze and optimize business processes
- Identify bottlenecks and inefficiencies
- Track operational KPIs and service levels
- Recommend automation and technology improvements
- Evaluate capacity and resource utilization
- Ensure quality and compliance standards

Analysis framework:
1. **Process Health**: Key processes and their current status
2. **Efficiency Metrics**: Throughput, cycle time, error rates
3. **Bottlenecks**: Current constraints and their impact
4. **Resource Utilization**: Capacity vs demand, idle resources
5. **Improvement Plan**: Process changes with expected efficiency gains

Guidelines:
- Focus on measurable efficiency improvements
- Prioritize high-impact, low-effort changes
- Consider cross-departmental process flows
- Suggest specific metrics to track improvement
- Be practical — consider real-world implementation constraints
"""


async def run_operations_agent(
    query: str,
    context_text: str,
) -> dict:
    """Operations Agent (COO): process optimization and efficiency analysis"""
    logger.info(f"Operations Agent: analyzing '{query[:80]}...'")

    prompt_parts = [f"**Operations Question:** {query}"]
    if context_text:
        prompt_parts.append(f"\n**Business Context (including metrics):**\n{context_text}")
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nAs COO, analyze the operational situation and provide optimization recommendations."

    messages = [
        SystemMessage(content=OPERATIONS_SYSTEM_PROMPT),
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
        "agent_trace": ["operations"],
    }
