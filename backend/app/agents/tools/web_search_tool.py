"""联网搜索工具 — 基于 Tavily Search API"""

import logging
from typing import Optional

from langchain_core.tools import tool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@tool
async def search_web(query: str, max_results: int = 5) -> str:
    """在互联网上搜索最新信息。

    当需要获取实时信息、最新新闻、外部知识，或知识库中没有的信息时使用。

    Args:
        query: 搜索查询文本
        max_results: 返回的最大结果数（默认 5，最大 10）

    Returns:
        格式化的搜索结果，包含标题、URL 和摘要
    """
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return "Web search is not configured. Please set TAVILY_API_KEY in .env"

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=min(max_results, 10),
            search_depth="basic",
        )

        results = response.get("results", [])
        if not results:
            return f"No results found for: {query}"

        parts = [f"Web search results for '{query}':\n"]
        for i, r in enumerate(results):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")
            parts.append(f"{i+1}. **{title}**\n   URL: {url}\n   {content}\n")

        return "\n".join(parts)

    except ImportError:
        return "tavily-python is not installed. Run: pip install tavily-python"
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Search error: {str(e)}"
