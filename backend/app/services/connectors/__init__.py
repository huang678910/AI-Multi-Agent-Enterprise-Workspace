"""Enterprise Knowledge Connectors — external data source integrations"""

from app.services.connectors.base import BaseConnector, ConnectorResult
from app.services.connectors.github_connector import GitHubConnector
from app.services.connectors.notion_connector import NotionConnector
from app.services.connectors.jira_connector import JiraConnector
from app.services.connectors.confluence_connector import ConfluenceConnector

# Registry of available connectors
CONNECTOR_REGISTRY = {
    "github": GitHubConnector,
    "notion": NotionConnector,
    "jira": JiraConnector,
    "confluence": ConfluenceConnector,
}

__all__ = [
    "BaseConnector", "ConnectorResult",
    "GitHubConnector", "NotionConnector", "JiraConnector", "ConfluenceConnector",
    "CONNECTOR_REGISTRY",
]
