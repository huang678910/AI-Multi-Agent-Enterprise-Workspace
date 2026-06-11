"""Notion 连接器 — 同步 Notion 页面和数据库到知识库"""

import logging
from app.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    """Notion Knowledge Connector — sync pages and databases"""

    source_type = "notion"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.database_id = config.get("database_id", "")
        self.page_id = config.get("page_id", "")

    async def validate_connection(self) -> bool:
        """Test Notion API connection"""
        if not self.api_key:
            return False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.notion.com/v1/users/me",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Notion-Version": "2022-06-28",
                    },
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Notion connection failed: {e}")
            return False

    async def list_resources(self) -> list[dict]:
        """List available pages and databases"""
        resources = []
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                # Search for pages and databases
                resp = await client.post(
                    "https://api.notion.com/v1/search",
                    headers=headers,
                    json={"page_size": 20},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        obj_type = item.get("object", "unknown")
                        title = "Untitled"
                        if obj_type == "page":
                            title_prop = item.get("properties", {}).get("title", {})
                            title_list = title_prop.get("title", [])
                            title = title_list[0]["plain_text"] if title_list else item.get("id", "Untitled")
                        elif obj_type == "database":
                            title_list = item.get("title", [])
                            title = title_list[0]["plain_text"] if title_list else item.get("id", "Untitled")
                        resources.append({
                            "id": item["id"],
                            "type": obj_type,
                            "title": title,
                            "last_edited": item.get("last_edited_time", ""),
                        })
        except Exception as e:
            logger.error(f"Notion list_resources error: {e}")
        return resources

    async def fetch_all(self) -> list[ConnectorResult]:
        """Fetch content from Notion pages"""
        results = []
        try:
            resources = await self.list_resources()
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
            }
            async with httpx.AsyncClient(timeout=30) as client:
                for res in resources[:10]:  # Limit to 10 pages
                    if res["type"] == "page":
                        # Get page blocks (content)
                        resp = await client.get(
                            f"https://api.notion.com/v1/blocks/{res['id']}/children",
                            headers=headers,
                            params={"page_size": 50},
                        )
                        if resp.status_code == 200:
                            blocks = resp.json().get("results", [])
                            text_parts = []
                            for block in blocks:
                                block_type = block.get("type", "")
                                if block_type in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"):
                                    rich_text = block.get(block_type, {}).get("rich_text", [])
                                    content = "".join(t.get("plain_text", "") for t in rich_text)
                                    if content:
                                        text_parts.append(content)
                            if text_parts:
                                results.append(ConnectorResult(
                                    title=f"[Notion] {res['title']}",
                                    content="\n\n".join(text_parts),
                                    source_url=f"https://notion.so/{res['id'].replace('-', '')}",
                                    metadata={"notion_id": res["id"], "last_edited": res.get("last_edited")},
                                ))
        except Exception as e:
            logger.error(f"Notion fetch_all error: {e}")
        return results
