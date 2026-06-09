"""知识连接器基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ConnectorResult:
    """连接器同步结果"""
    title: str
    content: str
    source_url: str | None = None
    metadata: dict | None = None


class BaseConnector(ABC):
    """外部数据源连接器基类"""

    source_type: str = "unknown"

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def validate_connection(self) -> bool:
        """验证连接是否有效"""
        ...

    @abstractmethod
    async def list_resources(self) -> list[dict]:
        """列出可同步的资源"""
        ...

    @abstractmethod
    async def fetch_all(self) -> list[ConnectorResult]:
        """获取所有数据"""
        ...
