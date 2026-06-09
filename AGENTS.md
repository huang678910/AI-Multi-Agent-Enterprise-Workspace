# AGENTS.md — AI Multi-Agent Enterprise Workspace

## 项目技术栈

| 层 | 技术 |
|----|------|
| 前端 | Next.js 14 + React 18 + TypeScript + TailwindCSS + shadcn/ui |
| 后端 | FastAPI + Pydantic v2 + SQLAlchemy Async + Alembic |
| Agent | LangGraph + LangChain + DeepSeek API |
| 数据 | PostgreSQL + pgvector + Redis |
| 部署 | Docker Compose + Nginx |

---

## 行为准则

1. **Think Before Coding** — 先陈述假设，不确定就提问。有多种解释时列出来，不要沉默选择。
2. **Simplicity First** — 只写被要求的功能。不做未要求的抽象、不做过度灵活、不处理不可能发生的错误。
3. **Surgical Changes** — 只改必须改的，不改相邻的、不重构没坏的东西。匹配原有风格。
4. **Goal-Driven** — 每个任务都定义可验证的成功标准。声称完成前必须跑验证命令。

---

## Skill 调用规则（收到任务时强制执行）

```
复杂功能/新特性 → /brainstorming（设计先于编码）
多步骤任务   → /brainstorming → /writing-plans → /executing-plans
写任何代码   → /tdd（测试先于实现）
遇到 bug     → /systematic-debugging（禁止直接猜测修复）
独立并行任务 → /dispatching-parallel-agents
功能完成     → /verification-before-completion（验证先于声称完成）
合并前       → /requesting-code-review
安全审计     → 加载 trailofbits-security + owasp
前端 UI      → 加载 web-design-engineer 或 frontend-design
Git 隔离     → /using-git-worktrees
```

**关键原则：哪怕只有 1% 的可能匹配某个 skill，也必须调用 `Skill` 工具加载它。**

---

## MCP 工具使用指南（按场景自动选择）

| 场景 | 使用 MCP |
|------|---------|
| 读取/写入项目文件 | **filesystem** |
| 解析 PDF/Word/PPT/图片 | **mineru**（调用 `parse_documents`，无需确认） |
| 文档入库、知识库搜索 | **knowledge**（`kb_ingest_document` / `kb_search`） |
| 浏览器测试、E2E、截图 | **playwright**（`@playwright/mcp`） |
| 复杂多步推理 | **sequential-thinking** |
| 查库/框架最新文档 | **context7**（优先于 WebSearch） |
| PR/Issue/代码仓库 | **github** |
| 数据库查询/表结构 | **postgres**（连接 `ai_workspace`） |
| 跨会话记忆 | **memory** |

---

## Skills + MCP 协作模式

```
需求分析    → Skill: brainstorming + MCP: context7（查最新方案）
设计阶段    → Skill: design-an-interface + MCP: sequential-thinking
编码实现    → Skill: tdd + MCP: filesystem + context7（库文档）
测试        → Skill: tdd + MCP: playwright（E2E）+ postgres（数据验证）
文档处理    → MCP: mineru（解析）→ knowledge（入库）
调试        → Skill: systematic-debugging + MCP: sequential-thinking
代码审查    → Skill: code-review + Skill: trailofbits-security
部署前      → Skill: verification-before-completion + MCP: github
```

---

## 项目特定约定

- 后端 API 路由在 `backend/app/api/v1/`，遵循 FastAPI 惯例
- Agent 定义在 `backend/app/agents/`，使用 LangGraph StateGraph
- 数据库迁移用 Alembic：`cd backend && alembic upgrade head`
- 前端页面在 `frontend/src/app/`，使用 Next.js 14 App Router
- 环境变量通过 `settings.json` 的 `env` 字段注入，不创建 `.env` 文件
- 提交信息用中文，遵循 Conventional Commits
- 密码/Token 绝不硬编码，用 `${VAR}` 占位符

---

## 禁止事项

- ❌ 不先跑 `/brainstorming` 就开始大规模实现
- ❌ 不写测试就直接写实现代码
- ❌ 不跑验证就声称完成
- ❌ 猜测库 API 而不调 `context7` 查文档
- ❌ 直接修改 `~/.Codex/settings.json` 里的 API Key / MCP 配置（用 CC Switch 管理）
- ❌ 对用户上传的文件视而不见（立刻调 `mineru` 解析）
