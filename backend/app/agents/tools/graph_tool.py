"""Graph Tool — query knowledge graph & GraphRAG search"""

import logging
from langchain_core.tools import tool

from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


@tool
async def query_graph(cypher: str, workspace_id: str) -> str:
    """Query the enterprise knowledge graph using Cypher.

    Use this to find relationships between entities:
    - Who works in which department
    - Which products belong to which market
    - Who manages a department
    - What goals does a department have

    Args:
        cypher: A read-only Cypher query (MATCH/RETURN only)
        workspace_id: Current workspace UUID
    """
    try:
        svc = GraphService(workspace_id)
        results = svc.query(cypher)
        if not results:
            return "No results found."
        if len(results) == 1 and "error" in results[0]:
            return f"Query error: {results[0]['error']}"

        # Format results
        parts = [f"Found {len(results)} result(s):"]
        for i, row in enumerate(results[:10]):
            parts.append(f"{i+1}. {row}")
        return "\n".join(parts)
    except Exception as e:
        logger.error(f"query_graph failed: {e}")
        return f"Graph query failed: {e}"


@tool
async def search_graph(query: str, workspace_id: str) -> str:
    """Search the knowledge graph for entities and their relationships.

    Use this for natural language questions about entity relationships:
    - "Who is responsible for product X?"
    - "Which departments does employee Y work in?"
    - "What customers are in market Z?"

    Args:
        query: Natural language search query
        workspace_id: Current workspace UUID
    """
    try:
        svc = GraphService(workspace_id)
        results = svc.search(query, top_k=5)
        if not results:
            return "No entities or relationships found."

        parts = [f"Found {len(results)} related entities:"]
        for r in results:
            entity = r["entity"]
            etype = ", ".join(r.get("type", []))
            related = r.get("related", [])
            rel_str = "; ".join(f"{rel['relationship']} → {rel['entity']}" for rel in related[:5])
            parts.append(f"- [{etype}] {entity}: {rel_str}" if rel_str else f"- [{etype}] {entity}")
        return "\n".join(parts)
    except Exception as e:
        logger.error(f"search_graph failed: {e}")
        return f"Graph search failed: {e}"
