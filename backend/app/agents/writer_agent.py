"""Writer Agent — 报告生成 Agent"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

from datetime import datetime, timezone

WRITER_SYSTEM_PROMPT = f"""You are a professional report writer for an enterprise AI workspace.
The current date is: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

Your task is to synthesize information into well-structured, professional reports.

Guidelines:
- ALWAYS use the current date ({datetime.now(timezone.utc).strftime('%Y-%m-%d')}) — NEVER make up dates like 'October 2023'
- Use clear headings and subheadings (##, ###)
- Include an executive summary at the top
- Present data in Markdown tables when applicable
- Cite all sources in [Source: filename] format
- Add a "Key Findings" section
- Add a "Recommendations" section when appropriate
- Use professional, concise language
- Format: Markdown with proper structure

Report Types:
1. **Technical Analysis Report** -- System architecture, code changes, performance analysis
2. **Business Research Report** -- Market analysis, competitor research, industry trends
3. **Risk Analysis Report** -- Security risks, compliance gaps, operational risks
4. **Data Summary Report** -- Statistical summaries, trend analysis, data insights
"""


async def run_writer_agent(
    title: str,
    context: str,
    user_query: str,
    report_type: str = "technical",
) -> dict:
    """Writer Agent：根据上下文生成结构化报告

    Args:
        title: 报告标题
        context: 上下文信息（搜索结果、数据等）
        user_query: 原始用户请求
        report_type: 报告类型 ("technical", "business", "risk", "data")

    Returns:
        dict with final_response, sources
    """
    logger.info(f"WriterAgent: generating '{report_type}' report: {title[:80]}")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""Generate a {report_type} report with the following details:

**Report Date:** {today} (USE THIS DATE, do not make up dates)
**Report Title:** {title}

**User Request:** {user_query}

**Available Context:**
{context}

Please generate a comprehensive, well-structured report in Markdown format.
Include: Executive Summary, Key Findings, Detailed Analysis, and Recommendations (if applicable).
"""

    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    llm = _get_llm(streaming=True)
    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content

    return {
        "final_response": f"# {title}\n\n{full_response}",
        "sources": [],
        "agent_trace": ["writer"],
    }
