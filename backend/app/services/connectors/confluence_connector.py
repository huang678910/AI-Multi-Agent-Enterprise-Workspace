"""Confluence 连接器 — 同步 Confluence 空间和页面到知识库"""

import logging
from app.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class ConfluenceConnector(BaseConnector):
    """Confluence Knowledge Connector — sync spaces and pages"""

    source_type = "confluence"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_token = config.get("api_token", "")
        self.email = config.get("email", "")
        self.domain = config.get("domain", "")  # e.g., "mycompany.atlassian.net"
        self.space_key = config.get("space_key", "")

    async def validate_connection(self) -> bool:
        """Test Confluence API connection"""
        if not self.api_token or not self.domain:
            return False
        try:
            import httpx
            from base64 import b64encode
            auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://{self.domain}/wiki/rest/api/user/current",
                    headers={"Authorization": f"Basic {auth}"},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Confluence connection failed: {e}")
            return False

    async def list_resources(self) -> list[dict]:
        """List available spaces"""
        resources = []
        try:
            import httpx
            from base64 import b64encode
            auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://{self.domain}/wiki/rest/api/space",
                    headers={"Authorization": f"Basic {auth}"},
                    params={"limit": 10},
                )
                if resp.status_code == 200:
                    for space in resp.json().get("results", []):
                        resources.append({
                            "id": space["id"],
                            "key": space["key"],
                            "name": space["name"],
                            "type": "space",
                        })
        except Exception as e:
            logger.error(f"Confluence list_resources error: {e}")
        return resources

    async def fetch_all(self) -> list[ConnectorResult]:
        """Fetch recent Confluence pages"""
        results = []
        try:
            import httpx
            from base64 import b64encode
            auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            spaces = await self.list_resources()
            space_key = self.space_key or (spaces[0]["key"] if spaces else "")

            if not space_key:
                return results

            async with httpx.AsyncClient(timeout=30) as client:
                # Get pages from space
                resp = await client.get(
                    f"https://{self.domain}/wiki/rest/api/content",
                    headers={"Authorization": f"Basic {auth}"},
                    params={"spaceKey": space_key, "limit": 10, "expand": "body.storage"},
                )
                if resp.status_code == 200:
                    pages = resp.json().get("results", [])
                    for page in pages:
                        title = page.get("title", "Untitled")
                        body = page.get("body", {}).get("storage", {}).get("value", "")
                        # Strip HTML tags for plain text
                        import re
                        clean_text = re.sub(r"<[^>]+>", "", body).strip() if body else ""
                        if clean_text:
                            results.append(ConnectorResult(
                                title=f"[Confluence] {title}",
                                content=clean_text,
                                source_url=f"https://{self.domain}/wiki{page['_links']['webui']}",
                                metadata={
                                    "page_id": page["id"],
                                    "space_key": space_key,
                                    "version": page.get("version", {}).get("number"),
                                },
                            ))
        except Exception as e:
            logger.error(f"Confluence fetch_all error: {e}")
        return results
