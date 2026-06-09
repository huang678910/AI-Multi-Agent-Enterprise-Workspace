"""GitHub 连接器 — 同步 README + Issues + Wiki 到知识库"""

import logging
from app.services.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """GitHub Repository Knowledge Connector"""

    source_type = "github"

    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get("token", "")
        self.owner = config.get("owner", "")
        self.repo = config.get("repo", "")

    async def validate_connection(self) -> bool:
        """Test GitHub API connection"""
        if not self.token:
            return False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{self.repo}",
                    headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"GitHub connection check failed: {e}")
            return False

    async def list_resources(self) -> list[dict]:
        """List available resources in the repo"""
        resources = [
            {"type": "readme", "name": "README.md"},
            {"type": "issues", "name": f"Open Issues ({self.owner}/{self.repo})"},
        ]
        return resources

    async def fetch_all(self) -> list[ConnectorResult]:
        """Fetch README + recent Issues as knowledge chunks"""
        results = []
        import httpx

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Fetch README
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{self.repo}/readme",
                    headers=headers,
                )
                if resp.status_code == 200:
                    import base64
                    readme_content = base64.b64decode(resp.json()["content"]).decode("utf-8", errors="replace")
                    results.append(ConnectorResult(
                        title=f"{self.owner}/{self.repo} README",
                        content=readme_content[:10000],  # Cap at 10K chars
                        source_url=f"https://github.com/{self.owner}/{self.repo}",
                        metadata={"source_type": "github", "resource_type": "readme"},
                    ))
            except Exception as e:
                logger.warning(f"GitHub README fetch failed: {e}")

            # 2. Fetch recent Issues (top 5)
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{self.owner}/{self.repo}/issues?state=all&per_page=5&sort=updated",
                    headers=headers,
                )
                if resp.status_code == 200:
                    issues = resp.json()
                    for issue in issues:
                        results.append(ConnectorResult(
                            title=f"Issue #{issue['number']}: {issue['title']}",
                            content=f"State: {issue['state']}\n\n{issue.get('body', '') or '(no description)'}"[:3000],
                            source_url=issue["html_url"],
                            metadata={"source_type": "github", "resource_type": "issue", "issue_number": issue["number"]},
                        ))
            except Exception as e:
                logger.warning(f"GitHub Issues fetch failed: {e}")

        logger.info(f"GitHub connector: fetched {len(results)} items from {self.owner}/{self.repo}")
        return results
