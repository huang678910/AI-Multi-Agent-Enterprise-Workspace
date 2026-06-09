"""SQL 工具 — 只读数据库查询"""

import logging

from langchain_core.tools import tool
from sqlalchemy import text

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# 白名单：只允许 SELECT（大小写不敏感）
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
]


@tool
async def query_database(sql: str) -> str:
    """对 PostgreSQL 数据库执行只读 SQL 查询。

    仅支持 SELECT 语句。结果自动格式化为 Markdown 表格。

    Args:
        sql: 要执行的 SQL 查询（仅允许 SELECT）

    Returns:
        格式化为 Markdown 表格的查询结果，或错误消息
    """
    # 安全检查：只允许 SELECT
    sql_upper = sql.strip().upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            return f"Error: Forbidden SQL operation '{keyword}'. Only SELECT queries are allowed."

    if not sql_upper.startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    # 限制 SQL 长度
    if len(sql) > 2000:
        return "Error: SQL query too long (max 2000 characters)."

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(sql))
            rows = result.fetchall()

            if not rows:
                return "Query returned no results."

            # 限制返回行数
            if len(rows) > 100:
                rows = rows[:100]
                truncated = True
            else:
                truncated = False

            # 格式化为 Markdown 表格
            columns = list(result.keys())
            header = "| " + " | ".join(columns) + " |"
            separator = "|" + "|".join(["---" for _ in columns]) + "|"
            body = "\n".join(
                "| " + " | ".join(str(v) for v in row) + " |"
                for row in rows
            )

            table = f"{header}\n{separator}\n{body}"
            if truncated:
                table += "\n\n*(Results truncated to 100 rows)*"
            return table

    except Exception as e:
        logger.error(f"SQL query failed: {e}")
        return f"SQL error: {str(e)}"
