"""Jira 连接器 — 同步 Jira Issues 到知识库"""

import logging
from app.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class JiraConnector(BaseConnector):
    """Jira Knowledge Connector — sync issues and projects"""

    source_type = "jira"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_token = config.get("api_token", "")
        self.email = config.get("email", "")
        self.domain = config.get("domain", "")  # e.g., "mycompany.atlassian.net"
        self.project_key = config.get("project_key", "")

    async def validate_connection(self) -> bool:
        """Test Jira API connection"""
        if not self.api_token or not self.domain:
            return False
        try:
            import httpx
            from base64 import b64encode
            auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://{self.domain}/rest/api/3/myself",
                    headers={"Authorization": f"Basic {auth}"},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Jira connection failed: {e}")
            return False

    async def list_resources(self) -> list[dict]:
        """List available projects"""
        resources = []
        try:
            import httpx
            from base64 import b64encode
            auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://{self.domain}/rest/api/3/project",
                    headers={"Authorization": f"Basic {auth}"},
                )
                if resp.status_code == 200:
                    for proj in resp.json():
                        resources.append({
                            "id": proj["id"],
                            "key": proj["key"],
                            "name": proj["name"],
                            "type": "project",
                        })
        except Exception as e:
            logger.error(f"Jira list_resources error: {e}")
        return resources

    async def fetch_all(self) -> list[ConnectorResult]:
        """Fetch recent Jira issues"""
        results = []
        try:
            import httpx
            from base64 import b64encode
            auth = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            jql = ""
            if self.project_key:
                jql = f"project={self.project_key}"
            else:
                resources = await self.list_resources()
                if resources:
                    jql = f"project={resources[0]['key']}"

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://{self.domain}/rest/api/3/search",
                    headers={"Authorization": f"Basic {auth}"},
                    params={"jql": jql, "maxResults": 20, "fields": "summary,description,status,created,updated"},
                )
                if resp.status_code == 200:
                    issues = resp.json().get("issues", [])
                    for issue in issues:
                        fields = issue.get("fields", {})
                        summary = fields.get("summary", "No title")
                        description = fields.get("description", {})
                        desc_text = ""
                        if description and isinstance(description, dict):
                            desc_text = "\n".join(
                                c.get("text", "") for c in description.get("content", [{}])[0].get("content", [])
                                if c.get("type") == "text"
                            )
                        status = fields.get("status", {}).get("name", "Unknown")
                        results.append(ConnectorResult(
                            title=f"[Jira] {issue['key']}: {summary}",
                            content=f"Status: {status}\n\n{desc_text}" if desc_text else f"Status: {status}",
                            source_url=f"https://{self.domain}/browse/{issue['key']}",
                            metadata={"issue_key": issue["key"], "status": status, "created": fields.get("created")},
                        ))
        except Exception as e:
            logger.error(f"Jira fetch_all error: {e}")
        return results
