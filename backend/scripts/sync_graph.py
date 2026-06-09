"""知识图谱同步脚本 — 将 Layer 1 企业画像数据全量同步到 Neo4j

用法:
    cd backend
    python scripts/sync_graph.py <workspace_id>
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal
from app.services.graph_service import GraphService


async def main(workspace_id: str):
    print(f"Syncing knowledge graph for workspace: {workspace_id}")

    svc = GraphService(workspace_id)

    # Check Neo4j connectivity
    stats = svc.get_stats()
    if not stats.get("connected"):
        print("ERROR: Neo4j is not connected. Make sure Neo4j is running (docker-compose up -d neo4j)")
        return

    print(f"Before sync: {stats['nodes']} nodes, {stats['relationships']} relationships")

    # Run full sync
    async with AsyncSessionLocal() as session:
        result = await svc.full_sync_from_db(session)

    if "error" in result:
        print(f"Sync error: {result['error']}")
        return

    print(f"Synced: {result}")

    # Verify
    stats = svc.get_stats()
    print(f"After sync: {stats['nodes']} nodes, {stats['relationships']} relationships")
    print("Labels:", stats["labels"])
    print("\nDone! Visit http://localhost:7474 to explore the graph in Neo4j Browser.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/sync_graph.py <workspace_id>")
        print("Example: python scripts/sync_graph.py 550e8400-e29b-41d4-a716-446655440000")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
