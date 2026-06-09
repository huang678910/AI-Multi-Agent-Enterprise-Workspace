"""Profile Agent — 企业画像查询与总结"""

import logging
from datetime import datetime, timezone

from app.services.llm_service import _get_llm
from app.database import AsyncSessionLocal
from app.services.company_service import CompanyService

logger = logging.getLogger(__name__)

PROFILE_SYSTEM_PROMPT = f"""You are the Enterprise Profile Agent.
Your job is to answer questions about the company using its stored profile data.
The current date is: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.

Rules:
1. Answer based ONLY on the provided company context. If info is missing, say so.
2. Be concise and professional. Use bullet points for lists.
3. When asked about departments, employees, products, or KPIs, mention specific names and numbers.
4. If no company profile exists, suggest the user configure it in Settings > Company.
5. ALWAYS use the current date — NEVER make up dates."""


async def run_profile_agent(
    query: str,
    workspace_id: str,
    context_text: str = "",
) -> dict:
    """Query company profile information

    Args:
        query: User's question about the company
        workspace_id: Workspace UUID
        context_text: Additional RAG context (may contain previous agent output)

    Returns:
        {"final_response": str, "agent_trace": list[str]}
    """
    # Load company profile data
    company_context = ""
    try:
        async with AsyncSessionLocal() as s:
            svc = CompanyService(s, workspace_id)
            company_context = await svc.get_company_summary()
    except Exception as e:
        logger.warning(f"Failed to load company profile: {e}")

    if not company_context and not context_text:
        return {
            "final_response": "No company profile has been configured yet. Please go to **Settings > Company** to set up your company profile, departments, products, and KPIs. Once configured, I can answer questions about your enterprise.",
            "agent_trace": ["profile: no_data"],
        }

    # Build context
    full_context = ""
    if company_context:
        full_context += f"### Company Profile\n{company_context}\n"
    if context_text:
        full_context += f"\n### Additional Context\n{context_text}\n"

    # LLM call
    try:
        llm = _get_llm(streaming=False)
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=PROFILE_SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\n{full_context}\n\nUser Question: {query}"),
        ]
        response = await llm.ainvoke(messages)
        return {
            "final_response": response.content.strip(),
            "agent_trace": ["profile: answered from company data"],
        }
    except Exception as e:
        logger.error(f"Profile agent LLM call failed: {e}")
        # Fallback: return raw profile data
        if company_context:
            return {
                "final_response": f"Here's what I know about the company:\n\n{company_context}",
                "agent_trace": ["profile: raw_data_fallback"],
            }
        return {
            "final_response": "Unable to retrieve company information at this time.",
            "agent_trace": ["profile: error"],
        }
