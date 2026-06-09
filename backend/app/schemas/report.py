"""报告 Pydantic Schemas"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """生成报告请求"""
    title: str = Field(..., description="报告标题")
    content: str = Field(default="", description="报告内容（为空时由 AI 生成）")
    query: str = Field(default="", description="生成报告的查询/问题")
    format: str = Field(default="markdown", description="输出格式: markdown | pdf | docx")
    report_type: str = Field(default="technical", description="报告类型: technical | business | risk | data")


class ReportResponse(BaseModel):
    """报告信息"""
    id: UUID
    workspace_id: UUID
    title: str
    content: str
    format: str
    file_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """报告列表"""
    reports: list[ReportResponse]
    total: int
