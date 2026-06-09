"""报告生成工具 — 生成 Markdown/PDF/DOCX 报告"""

import logging
from datetime import datetime, timezone

from langchain_core.tools import tool

from app.database import AsyncSessionLocal
from app.services.chat_service import ChatService
from app.services.agent_orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


@tool
async def generate_report(title: str, content: str, format: str = "markdown") -> str:
    """生成一份结构化报告。

    用于创建技术分析报告、企业研究报告、风险分析报告等。

    Args:
        title: 报告标题
        content: 报告正文（Markdown 格式）
        format: 输出格式，支持 "markdown"（PDF/DOCX 后续版本支持）

    Returns:
        生成的报告内容（Markdown 格式）
    """
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        report = f"""# {title}

> 生成时间：{now}
> 格式：{format}

---

{content}

---

*本报告由 AI Multi-Agent Enterprise Workspace 自动生成*
"""

        return report

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return f"Report generation error: {str(e)}"
