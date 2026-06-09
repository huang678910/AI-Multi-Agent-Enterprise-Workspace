"""SQL Agent — Text-to-SQL：自然语言转 SQL 查询"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import _get_llm
from app.agents.tools.sql_tool import query_database

logger = logging.getLogger(__name__)

SQL_SYSTEM_PROMPT = """You are a SQL specialist. Convert natural language questions into PostgreSQL queries.

Available tables (public schema):
- users (id, email, username, hashed_password, is_active, created_at, updated_at)
- workspaces (id, name, description, owner_id, created_at, updated_at)
- workspace_members (id, workspace_id, user_id, role, created_at)
- documents (id, workspace_id, filename, file_type, file_size, status, chunk_count, error_message, file_path, created_at, updated_at)
- document_chunks (id, document_id, chunk_index, content, metadata, embedding, created_at)
- chat_sessions (id, workspace_id, user_id, title, created_at, updated_at)
- messages (id, session_id, role, content, sources, agent_type, created_at)
- tools (id, name, description, parameters_schema, is_active, created_at)
- reports (id, workspace_id, title, content, format, file_path, created_at)

Rules:
1. ONLY generate SELECT queries — no INSERT/UPDATE/DELETE
2. Use standard PostgreSQL syntax
3. Include appropriate WHERE clauses for filtering
4. Use JOINs when needed for related data
5. Add LIMIT for potentially large result sets
6. Output ONLY the SQL query, no explanation

Output format: Just the raw SQL query, nothing else."""


async def run_sql_agent(query: str, workspace_id: str) -> dict:
    """SQL Agent：自然语言 → SQL → 执行 → 返回结果

    Args:
        query: 自然语言查询
        workspace_id: 工作区 ID（用于过滤数据）

    Returns:
        dict with final_response, agent_trace
    """
    logger.info(f"SQLAgent: processing '{query[:80]}...'")

    try:
        # 1. Text-to-SQL
        llm = _get_llm(streaming=False)
        messages = [
            SystemMessage(content=SQL_SYSTEM_PROMPT),
            HumanMessage(content=f"Generate a SQL query for: {query}\n\nContext: workspace_id='{workspace_id}'"),
        ]
        response = await llm.ainvoke(messages)
        sql = response.content.strip()

        # 清理 SQL（去掉 markdown 代码块）
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        sql = sql.strip().rstrip(";")

        logger.info(f"SQLAgent generated SQL: {sql[:200]}")

        # 2. 执行 SQL
        result = await query_database.ainvoke({"sql": sql})

        # 3. 格式化输出
        final = f"**Query:** {query}\n\n**SQL:**\n```sql\n{sql}\n```\n\n**Results:**\n{result}"

        return {
            "final_response": final,
            "sources": [],
            "agent_trace": ["sql"],
        }

    except Exception as e:
        logger.error(f"SQLAgent failed: {e}")
        return {
            "final_response": f"SQL query failed: {str(e)}",
            "sources": [],
            "agent_trace": ["sql"],
        }
