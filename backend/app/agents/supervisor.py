"""Supervisor Agent - LangGraph Multi-Agent LLM Router"""

import logging
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.services.llm_service import _get_llm

logger = logging.getLogger(__name__)

# ---- AgentState ----

class AgentState(TypedDict, total=False):
    """LangGraph shared state"""
    messages: list[dict]
    workspace_id: str
    session_id: str
    user_query: str
    next_agent: str
    next_agents: list[str]
    context_text: str
    sources: list[dict]
    final_response: str
    agent_trace: list[str]


# ---- Route Decision Model ----

class RouteDecision(BaseModel):
    """LLM routing decision - supports multi-agent pipelines"""
    next_agents: list = Field(default=["chat"], description="Ordered list of agents to execute in sequence. Example: ['search','analyst','writer'] for 'search docs, analyze, generate report'")
    reason: str = Field(default="", description="Brief explanation")


ROUTE_SYSTEM_PROMPT = """You are a routing supervisor for an enterprise AI workspace.
Analyze the user's message and plan which agents should work on it, in what order.

Available agents and their capabilities:
- "search": Find info in uploaded documents/knowledge base. Required before other agents can use document data.
- "analyst": Data analysis, statistics, numerical insights.
- "writer": Generate/produce/create a report or document.
- "research": Deep multi-step research with web and knowledge base.
- "sql": SQL queries, database counts, data retrieval.
- "chat": Simple conversation, greetings, explanations.
- "profile": Company/organization questions ("tell me about our company", "what departments do we have", "list our products", "who works in sales").
- "memory": Past events, decisions, historical context ("what did we decide about X", "remember when Y happened", "what are our key facts about Z").
- "ceo": Strategic analysis, business health, market assessment, risk evaluation, resource allocation. Use for broad strategic questions.
- "finance": Revenue, profit, budget, costs, cashflow, financial analysis, ROI. Use for financial/numerical business questions.
- "sales": Sales performance, pipeline, customer acquisition, revenue growth, pricing. Use for sales-related questions.
- "hr": Hiring, headcount, organization structure, team optimization, recruitment. Use for workforce/people questions.
- "customer": Customer satisfaction, churn, retention, NPS, complaints. Use for customer experience questions.
- "operations": Process optimization, efficiency, workflow analysis, quality. Use for operational questions.
- "procurement": Inventory, supply chain, vendor analysis, purchasing, stock levels. Use for procurement/supply questions.

CRITICAL PIPELINE RULES:
1. For document-heavy questions, put "search" FIRST, then the domain agent: ["search", "analyst"] or ["search", "finance"]
2. For business/strategic questions, route to the appropriate department agent directly: ["ceo"], ["finance"], ["sales"], etc.
3. For questions spanning multiple domains, use a pipeline: ["finance", "ceo"] for deep financial-strategic analysis
4. Simple queries use ONE agent: greetings → ["chat"], SQL question → ["sql"], company info → ["profile"]
5. "writer" should typically be last (produces final output)
6. "memory" should be first when user asks about past events or decisions

Return valid JSON with "next_agents" (ordered list) and "reason" fields.
Example: {"next_agents": ["finance","ceo"], "reason": "Financial analysis then strategic assessment"}"""

_route_prompt = ChatPromptTemplate.from_messages([
    ("system", ROUTE_SYSTEM_PROMPT),
    ("human", "{user_input}"),
])


async def _llm_route(user_input: str) -> RouteDecision:
    """Use LLM to make routing decision - supports multi-agent pipelines"""
    import json as json_mod
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = _get_llm(streaming=False)
    messages = [
        SystemMessage(content=ROUTE_SYSTEM_PROMPT),
        HumanMessage(content=f"User message: {user_input}\n\nPlan the agent pipeline. Return JSON with next_agents (ordered list) and reason."),
    ]
    try:
        response = await llm.ainvoke(messages)
        text = response.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        data = json_mod.loads(text)
        agents = data.get("next_agents", data.get("next_agent", ["chat"]))
        if isinstance(agents, str):
            agents = [agents]
        return RouteDecision(next_agents=agents, reason=data.get("reason", ""))
    except Exception as e:
        raise ValueError(f"Failed to parse LLM route: {e}")


# ---- Graph Nodes ----

async def supervisor_node(state: AgentState) -> dict:
    """Supervisor Node - LLM routing decision"""
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")

    if not user_query and messages:
        for m in reversed(messages):
            if m.get("role") == "user":
                user_query = m.get("content", "")
                break

    if not user_query:
        return {"next_agents": ["chat"], "agent_trace": ["supervisor->chat(no_query)"]}

    try:
        decision = await _llm_route(user_query)
        agents = decision.next_agents if decision.next_agents else ["chat"]
        logger.info(f"Supervisor pipeline: {agents} - {decision.reason}")
        return {
            "next_agents": agents,
            "agent_trace": [f"supervisor->{'->'.join(agents)}: {decision.reason}"],
        }
    except Exception as e:
        logger.error(f"LLM routing failed: {e} - falling back to keyword routing")
        q = user_query.lower()
        sql_kw = ["count", "sql", "select", "database", "query", "how many", "total", "list all"]
        writer_kw = ["report", "generate", "create a", "write a", "make a"]
        analyst_kw = ["analyze", "analysis", "statistics", "trend", "metrics"]
        research_kw = ["research", "deep dive", "investigate", "comprehensive"]
        search_kw = ["search", "find", "document", "knowledge"]
        profile_kw = ["company", "department", "employee", "product", "our ", "we have", "tell me about", "who works", "what are our", "list our", "org chart"]
        memory_kw = ["remember", "memory", "past", "history", "decision", "decided", "previous", "before", "recall", "what happened"]
        finance_kw = ["revenue", "profit", "budget", "cost", "cashflow", "financial", "finance", "margin", "expense", "income", "roi"]
        hr_kw = ["hiring", "headcount", "recruit", "hr", "workforce", "staff", "team structure", "salary", "compensation"]
        sales_kw = ["sales", "pipeline", "revenue growth", "customer acquisition", "pricing", "discount", "deal"]
        ceo_kw = ["strategy", "strategic", "growth", "market", "risk", "overall", "business health", "enterprise", "vision", "roadmap"]
        customer_kw = ["customer satisf", "churn", "nps", "retention", "complaint", "feedback", "loyalty"]
        operations_kw = ["efficiency", "process", "workflow", "optimization", "bottleneck", "quality", "throughput"]
        procurement_kw = ["inventory", "supply chain", "vendor", "supplier", "purchasing", "procurement", "stock", "reorder"]

        # Build pipeline based on keyword combinations
        pipeline = []
        if any(kw in q for kw in memory_kw):
            pipeline.append("memory")
        if any(kw in q for kw in profile_kw):
            pipeline.append("profile")
        if any(kw in q for kw in search_kw):
            pipeline.append("search")
        if any(kw in q for kw in ceo_kw):
            pipeline.append("ceo")
        if any(kw in q for kw in finance_kw):
            pipeline.append("finance")
        if any(kw in q for kw in sales_kw):
            pipeline.append("sales")
        if any(kw in q for kw in hr_kw):
            pipeline.append("hr")
        if any(kw in q for kw in customer_kw):
            pipeline.append("customer")
        if any(kw in q for kw in operations_kw):
            pipeline.append("operations")
        if any(kw in q for kw in procurement_kw):
            pipeline.append("procurement")
        if any(kw in q for kw in sql_kw):
            pipeline.append("sql")
        if any(kw in q for kw in analyst_kw):
            pipeline.append("analyst")
        if any(kw in q for kw in research_kw):
            pipeline.append("research")
        if any(kw in q for kw in writer_kw):
            pipeline.append("writer")
        if not pipeline:
            pipeline = ["chat"]

        return {
            "next_agents": pipeline,
            "agent_trace": [f"supervisor(fallback)->{'->'.join(pipeline)}"],
        }


async def search_node(state: AgentState) -> dict:
    """Search node - RAG retrieval + LLM synthesis"""
    logger.info("SearchAgent: executing RAG search")
    from app.agents.search_agent import run_search_agent
    result = await run_search_agent(
        query=state.get("user_query", ""),
        workspace_id=state.get("workspace_id", ""),
        top_k=5,
        context_text=state.get("context_text", ""),
    )
    return {
        "context_text": result.get("context_text", ""),
        "sources": result.get("sources", []),
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["search"]),
    }


async def chat_node(state: AgentState) -> dict:
    """Chat node - general conversation"""
    logger.info("ChatAgent: executing general chat")
    from app.agents.chat_agent import run_chat_agent
    result = await run_chat_agent(
        messages=state.get("messages", []),
        user_query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["chat"]),
    }


async def research_node(state: AgentState) -> dict:
    """Research node - deep multi-step research"""
    logger.info("ResearchAgent: executing deep research")
    from app.agents.research_agent import run_research_agent
    result = await run_research_agent(
        query=state.get("user_query", ""),
        knowledge_context=state.get("context_text", ""),
        workspace_id=state.get("workspace_id", ""),
        web_context=state.get("web_context", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["research"]),
    }


async def analyst_node(state: AgentState) -> dict:
    """Analyst node - data analysis"""
    logger.info("AnalystAgent: executing data analysis")
    from app.agents.analyst_agent import run_analyst_agent
    result = await run_analyst_agent(
        query=state.get("user_query", ""),
        data_context=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["analyst"]),
    }


async def writer_node(state: AgentState) -> dict:
    """Writer node - report generation"""
    logger.info("WriterAgent: generating report")
    from app.agents.writer_agent import run_writer_agent
    result = await run_writer_agent(
        title=f"Report: {state.get('user_query', 'Untitled')[:100]}",
        context=state.get("context_text", "") or state.get("final_response", ""),
        user_query=state.get("user_query", ""),
        report_type="technical",
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["writer"]),
    }


async def sql_node(state: AgentState) -> dict:
    """SQL node - database query"""
    logger.info("SQLAgent: executing database query")
    from app.agents.sql_agent import run_sql_agent
    result = await run_sql_agent(
        query=state.get("user_query", ""),
        workspace_id=state.get("workspace_id", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["sql"]),
    }


async def profile_node(state: AgentState) -> dict:
    """Profile node - company profile query"""
    logger.info("ProfileAgent: querying company profile")
    from app.agents.profile_agent import run_profile_agent
    result = await run_profile_agent(
        query=state.get("user_query", ""),
        workspace_id=state.get("workspace_id", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["profile"]),
    }


async def memory_node(state: AgentState) -> dict:
    """Memory node - enterprise memory recall"""
    logger.info("MemoryAgent: recalling enterprise memories")
    from app.agents.memory_agent import run_memory_agent
    result = await run_memory_agent(
        query=state.get("user_query", ""),
        workspace_id=state.get("workspace_id", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["memory"]),
    }


# ── Department Agent Nodes ──────────────────────────────

async def ceo_node(state: AgentState) -> dict:
    """CEO node - strategic analysis"""
    logger.info("CEO Agent: strategic analysis")
    from app.agents.ceo_agent import run_ceo_agent
    result = await run_ceo_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["ceo"]),
    }


async def finance_node(state: AgentState) -> dict:
    """Finance node - financial analysis"""
    logger.info("Finance Agent: financial analysis")
    from app.agents.finance_agent import run_finance_agent
    result = await run_finance_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["finance"]),
    }


async def sales_node(state: AgentState) -> dict:
    """Sales node - sales analysis"""
    logger.info("Sales Agent: sales analysis")
    from app.agents.sales_agent import run_sales_agent
    result = await run_sales_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["sales"]),
    }


async def hr_node(state: AgentState) -> dict:
    """HR node - workforce analysis"""
    logger.info("HR Agent: workforce analysis")
    from app.agents.hr_agent import run_hr_agent
    result = await run_hr_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["hr"]),
    }


async def customer_node(state: AgentState) -> dict:
    """Customer node - customer insights"""
    logger.info("Customer Agent: customer analysis")
    from app.agents.customer_agent import run_customer_agent
    result = await run_customer_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["customer"]),
    }


async def operations_node(state: AgentState) -> dict:
    """Operations node - operations analysis"""
    logger.info("Operations Agent: operations analysis")
    from app.agents.operations_agent import run_operations_agent
    result = await run_operations_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["operations"]),
    }


async def procurement_node(state: AgentState) -> dict:
    """Procurement node - supply chain analysis"""
    logger.info("Procurement Agent: procurement analysis")
    from app.agents.procurement_agent import run_procurement_agent
    result = await run_procurement_agent(
        query=state.get("user_query", ""),
        context_text=state.get("context_text", ""),
    )
    return {
        "final_response": result.get("final_response", ""),
        "agent_trace": result.get("agent_trace", ["procurement"]),
    }


async def formatter_node(state: AgentState) -> dict:
    """Formatter node - finalize output"""
    agent_trace = state.get("agent_trace", [])
    agent_trace.append("formatter")
    return {"agent_trace": agent_trace, "next_agent": "end"}


# ---- Routing Functions ----

AGENT_NAMES = (
    "search", "chat", "research", "analyst", "writer", "sql", "profile", "memory",
    "ceo", "finance", "sales", "hr", "customer", "operations", "procurement",
)


def route_decision(state: AgentState) -> str:
    next_agent = state.get("next_agent", "chat")
    if next_agent not in AGENT_NAMES:
        return "chat"
    return next_agent


# ---- Graph Construction ----

def create_supervisor_graph() -> CompiledStateGraph:
    """Build Supervisor Agent state graph"""

    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("search", search_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("research", research_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("sql", sql_node)
    workflow.add_node("profile", profile_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("ceo", ceo_node)
    workflow.add_node("finance", finance_node)
    workflow.add_node("sales", sales_node)
    workflow.add_node("hr", hr_node)
    workflow.add_node("customer", customer_node)
    workflow.add_node("operations", operations_node)
    workflow.add_node("procurement", procurement_node)
    workflow.add_node("formatter", formatter_node)

    workflow.set_entry_point("supervisor")

    route_map = {a: a for a in AGENT_NAMES}
    workflow.add_conditional_edges("supervisor", route_decision, route_map)

    for agent in AGENT_NAMES:
        workflow.add_edge(agent, "formatter")

    workflow.add_edge("formatter", END)

    return workflow.compile()


supervisor_graph = create_supervisor_graph()
