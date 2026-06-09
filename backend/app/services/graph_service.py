"""企业知识图谱服务 — Neo4j 连接 + 图谱同步 + 查询"""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# Lazy Neo4j driver init
_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        settings = get_settings()
        try:
            from neo4j import GraphDatabase
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            _driver.verify_connectivity()
            logger.info(f"Neo4j connected: {settings.NEO4J_URI}")
        except Exception as e:
            logger.warning(f"Neo4j unavailable at {settings.NEO4J_URI}: {e}")
            _driver = None
    return _driver


def _run_query(cypher: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only Cypher query, return list of records as dicts"""
    driver = _get_driver()
    if not driver:
        return []

    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]


class GraphService:
    """知识图谱服务 — 实体同步 + 查询 + GraphRAG 检索"""

    ENTITY_LABELS = {
        "employee": "Employee",
        "department": "Department",
        "product": "Product",
        "customer": "Customer",
        "process": "Project",
        "goal": "Goal",
        "kpi": "KPI",
    }

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id

    # ─── Sync ──────────────────────────────────────────

    def sync_entity(self, entity_type: str, entity_id: str, name: str, properties: dict | None = None) -> bool:
        """Sync a single entity to Neo4j (MERGE)"""
        label = self.ENTITY_LABELS.get(entity_type)
        if not label:
            logger.warning(f"Unknown entity type for graph: {entity_type}")
            return False

        props = properties or {}
        props["name"] = name
        props["workspace_id"] = self.workspace_id
        props["entity_id"] = entity_id

        set_clause = ", ".join(f"n.{k} = ${k}" for k in props)
        cypher = f"MERGE (n:{label} {{entity_id: $entity_id}}) SET {set_clause}"

        try:
            _run_query(cypher, props)
            return True
        except Exception as e:
            logger.error(f"Graph sync failed for {entity_type}/{entity_id}: {e}")
            return False

    def sync_relation(self, from_type: str, from_id: str, rel_type: str, to_type: str, to_id: str) -> bool:
        """Sync a relationship between two entities"""
        from_label = self.ENTITY_LABELS.get(from_type)
        to_label = self.ENTITY_LABELS.get(to_type)
        if not from_label or not to_label:
            return False

        cypher = f"""
        MATCH (a:{from_label} {{entity_id: $from_id}})
        MATCH (b:{to_label} {{entity_id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        RETURN type(r) as relationship
        """
        try:
            _run_query(cypher, {"from_id": from_id, "to_id": to_id})
            return True
        except Exception as e:
            logger.error(f"Graph relation sync failed: {e}")
            return False

    # ─── Query ─────────────────────────────────────────

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Execute a read-only Cypher query (whitelist enforced)"""
        # Security: only allow read operations
        upper = cypher.strip().upper()
        forbidden = ["CREATE", "DELETE", "DROP", "SET", "REMOVE", "MERGE"]
        for kw in forbidden:
            if upper.startswith(kw) or f"\n{kw}" in upper:
                return [{"error": f"Forbidden operation: {kw}"}]

        if not any(upper.startswith(kw) for kw in ["MATCH", "RETURN", "CALL"]):
            return [{"error": "Only MATCH/RETURN/CALL queries are allowed"}]

        return _run_query(cypher, params or {})

    def search(self, query_text: str, top_k: int = 5) -> list[dict]:
        """Simple GraphRAG: search entities by name and return neighbors"""
        results = _run_query("""
        MATCH (n)
        WHERE n.workspace_id = $ws_id
          AND (toLower(n.name) CONTAINS toLower($query)
               OR toLower(coalesce(n.description, '')) CONTAINS toLower($query))
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n.name as entity_name, labels(n) as entity_type,
               type(r) as relationship, m.name as related_entity
        LIMIT $limit
        """, {"ws_id": self.workspace_id, "query": query_text, "limit": top_k * 3})

        if not results:
            return []

        # Group by entity
        grouped: dict[str, dict] = {}
        for row in results:
            name = row.get("entity_name", "")
            if name not in grouped:
                grouped[name] = {
                    "entity": name,
                    "type": row.get("entity_type", []),
                    "related": [],
                }
            rel = row.get("relationship")
            related = row.get("related_entity")
            if rel and related:
                grouped[name]["related"].append({"relationship": rel, "entity": related})

        return list(grouped.values())[:top_k]

    def get_stats(self) -> dict:
        """Get graph statistics"""
        node_count = _run_query("MATCH (n) WHERE n.workspace_id = $ws_id RETURN count(n) as count", {"ws_id": self.workspace_id})
        rel_count = _run_query("MATCH ()-[r]->() RETURN count(r) as count", {})
        labels = _run_query("MATCH (n) WHERE n.workspace_id = $ws_id RETURN distinct labels(n) as labels, count(n) as count", {"ws_id": self.workspace_id})

        return {
            "nodes": node_count[0]["count"] if node_count else 0,
            "relationships": rel_count[0]["count"] if rel_count else 0,
            "labels": [
                {"label": r["labels"][0], "count": r["count"]}
                for r in labels
            ],
            "connected": _get_driver() is not None,
        }

    # ─── Full Sync from Layer 1 Data ───────────────────

    async def full_sync_from_db(self, db_session) -> dict:
        """Sync all Layer 1 entities to Neo4j. Returns sync stats."""
        from app.models.company import (
            Company, Department, Employee, Product, Customer,
            BusinessProcess, CompanyGoal, CompanyKPI,
        )

        stats = {"departments": 0, "employees": 0, "products": 0, "customers": 0, "processes": 0, "goals": 0, "kpis": 0, "relations": 0}

        try:
            from sqlalchemy import select

            # Get company
            result = await db_session.execute(
                select(Company).where(Company.workspace_id == self.workspace_id)
            )
            company = result.scalar_one_or_none()
            if not company:
                return {"error": "No company profile found. Configure it first."}

            company_id = str(company.id)

            # Sync Departments
            result = await db_session.execute(
                select(Department).where(Department.company_id == company.id)
            )
            depts = result.scalars().all()
            for d in depts:
                self.sync_entity("department", str(d.id), d.name, {"type": d.type or "", "description": d.description or ""})
                stats["departments"] += 1
                if d.parent_id:
                    self.sync_relation("department", str(d.id), "BELONGS_TO", "department", str(d.parent_id))
                    stats["relations"] += 1

            # Sync Employees
            result = await db_session.execute(
                select(Employee).where(Employee.company_id == company.id)
            )
            emps = result.scalars().all()
            for e in emps:
                self.sync_entity("employee", str(e.id), e.name, {"email": e.email or "", "status": e.status})
                stats["employees"] += 1
                if e.department_id:
                    self.sync_relation("employee", str(e.id), "BELONGS_TO", "department", str(e.department_id))
                    stats["relations"] += 1

            # Sync Products
            result = await db_session.execute(
                select(Product).where(Product.company_id == company.id)
            )
            prods = result.scalars().all()
            for p in prods:
                self.sync_entity("product", str(p.id), p.name, {"category": p.category or "", "status": p.status})
                stats["products"] += 1

            # Sync Customers
            result = await db_session.execute(
                select(Customer).where(Customer.company_id == company.id)
            )
            custs = result.scalars().all()
            for c in custs:
                self.sync_entity("customer", str(c.id), c.name, {"market": c.market or "", "type": c.type or ""})
                stats["customers"] += 1

            # Sync Processes
            result = await db_session.execute(
                select(BusinessProcess).where(BusinessProcess.company_id == company.id)
            )
            procs = result.scalars().all()
            for p in procs:
                self.sync_entity("process", str(p.id), p.name, {"status": p.status})
                stats["processes"] += 1

            # Sync Goals
            result = await db_session.execute(
                select(CompanyGoal).where(CompanyGoal.company_id == company.id)
            )
            goals = result.scalars().all()
            for g in goals:
                self.sync_entity("goal", str(g.id), g.title, {"type": g.type, "status": g.status})
                stats["goals"] += 1

            # Sync KPIs
            result = await db_session.execute(
                select(CompanyKPI).where(CompanyKPI.company_id == company.id)
            )
            kpis = result.scalars().all()
            for k in kpis:
                self.sync_entity("kpi", str(k.id), k.name, {"category": k.category or "", "unit": k.unit or ""})
                stats["kpis"] += 1

            logger.info(f"Graph full sync complete: {stats}")
        except Exception as e:
            logger.error(f"Graph full sync failed: {e}")
            stats["error"] = str(e)

        return stats
