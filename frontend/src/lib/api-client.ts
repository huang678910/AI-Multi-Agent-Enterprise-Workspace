import api from "./api";
// Types used implicitly by API responses

// ---- Auth ----
export async function login(email: string, password: string) {
  const res = await api.post("/api/v1/auth/login", { email, password });
  return res.data;
}

export async function register(email: string, username: string, password: string) {
  const res = await api.post("/api/v1/auth/register", { email, username, password });
  return res.data;
}

// ---- Workspaces ----
export async function listWorkspaces() {
  const res = await api.get("/api/v1/workspaces");
  return res.data;
}

export async function createWorkspace(name: string, description?: string) {
  const res = await api.post("/api/v1/workspaces", { name, description });
  return res.data;
}

export async function deleteWorkspace(id: string) {
  await api.delete(`/api/v1/workspaces/${id}`);
}

// ---- Documents ----
export async function listDocuments(workspaceId: string) {
  const res = await api.get(`/api/v1/workspaces/${workspaceId}/documents`);
  return res.data;
}

export async function uploadDocument(workspaceId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post(
    `/api/v1/workspaces/${workspaceId}/documents/upload`,
    formData
    // axios auto-sets Content-Type with correct boundary for FormData
  );
  return res.data;
}

export async function deleteDocument(workspaceId: string, documentId: string) {
  await api.delete(`/api/v1/workspaces/${workspaceId}/documents/${documentId}`);
}

// ---- Search ----
export async function searchKnowledge(workspaceId: string, query: string, topK = 5) {
  const res = await api.post(`/api/v1/workspaces/${workspaceId}/search`, { query, top_k: topK });
  return res.data;
}

// ---- Chat Sessions ----
export async function listChatSessions(workspaceId: string) {
  const res = await api.get(`/api/v1/workspaces/${workspaceId}/chat/sessions`);
  return res.data;
}

export async function createChatSession(workspaceId: string, title = "New Chat") {
  const res = await api.post(`/api/v1/workspaces/${workspaceId}/chat/sessions`, { title });
  return res.data;
}

export async function deleteChatSession(workspaceId: string, sessionId: string) {
  await api.delete(`/api/v1/workspaces/${workspaceId}/chat/sessions/${sessionId}`);
}

export async function listMessages(workspaceId: string, sessionId: string) {
  const res = await api.get(`/api/v1/workspaces/${workspaceId}/chat/sessions/${sessionId}/messages`);
  // Backend returns array directly (not wrapped in {messages: [...]})
  return Array.isArray(res.data) ? res.data : (res.data.messages || []);
}

// ---- Members ----
export async function listMembers(workspaceId: string) {
  const res = await api.get(`/api/v1/workspaces/${workspaceId}/members`);
  return res.data;
}

export async function addMember(workspaceId: string, userId: string, role: string) {
  const res = await api.post(`/api/v1/workspaces/${workspaceId}/members`, { user_id: userId, role });
  return res.data;
}

export async function updateMemberRole(workspaceId: string, memberId: string, role: string) {
  const res = await api.patch(`/api/v1/workspaces/${workspaceId}/members/${memberId}`, { role });
  return res.data;
}

export async function removeMember(workspaceId: string, memberId: string) {
  await api.delete(`/api/v1/workspaces/${workspaceId}/members/${memberId}`);
}

export async function deleteReport(workspaceId: string, reportId: string) {
  await api.delete(`/api/v1/workspaces/${workspaceId}/reports/${reportId}`);
}

// ---- Users ----
export async function searchUsers(query: string, limit = 10) {
  const res = await api.get("/api/v1/users/search", { params: { q: query, limit } });
  return res.data; // { users: UserSearchResult[], total: number }
}

// ---- Chat (HTTP fallback, non-streaming) ----
export async function sendChatMessage(
  workspaceId: string,
  sessionId: string,
  message: string,
): Promise<{ reply: string; sources: unknown[] }> {
  const res = await api.post(
    `/api/v1/workspaces/${workspaceId}/chat/send`,
    { session_id: sessionId, message },
    { timeout: 120000 }  // 2 minutes for LLM
  );
  return res.data;
}

// ─── Company Profile ─────────────────────────────────

export interface CompanyData {
  id: string; workspace_id: string; name: string; industry?: string;
  description?: string; founded_year?: number; employee_count: number;
  markets: string[]; headquarters?: string; website?: string;
  extra_data: Record<string, unknown>;
  created_at: string; updated_at: string;
}

export async function getCompany(workspaceId: string): Promise<CompanyData | null> {
  const res = await api.get(`/api/v1/workspaces/${workspaceId}/company/profile`);
  return res.data;
}

export async function upsertCompany(workspaceId: string, data: Partial<CompanyData>): Promise<CompanyData> {
  const res = await api.put(`/api/v1/workspaces/${workspaceId}/company/profile`, data);
  return res.data;
}

// ─── Departments ──────────────────────────────────────

export interface DeptData {
  id: string; company_id: string; parent_id?: string; name: string;
  type?: string; description?: string; head_id?: string;
  sort_order: number; children?: DeptData[];
  created_at: string; updated_at: string;
}

export async function listDepartments(ws: string): Promise<DeptData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/departments`);
  return res.data;
}
export async function createDepartment(ws: string, data: Partial<DeptData>): Promise<DeptData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/departments`, data);
  return res.data;
}
export async function updateDepartment(ws: string, id: string, data: Partial<DeptData>): Promise<DeptData> {
  const res = await api.put(`/api/v1/workspaces/${ws}/company/departments/${id}`, data);
  return res.data;
}
export async function deleteDepartment(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/departments/${id}`);
}

// ─── Positions ────────────────────────────────────────

export interface PosData {
  id: string; company_id: string; department_id?: string;
  title: string; level?: string; description?: string;
  created_at: string; updated_at: string;
}

export async function listPositions(ws: string): Promise<PosData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/positions`);
  return res.data;
}
export async function createPosition(ws: string, data: Partial<PosData>): Promise<PosData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/positions`, data);
  return res.data;
}
export async function updatePosition(ws: string, id: string, data: Partial<PosData>): Promise<PosData> {
  const res = await api.put(`/api/v1/workspaces/${ws}/company/positions/${id}`, data);
  return res.data;
}
export async function deletePosition(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/positions/${id}`);
}

// ─── Employees ────────────────────────────────────────

export interface EmpData {
  id: string; company_id: string; user_id?: string; department_id?: string;
  position_id?: string; name: string; email?: string; phone?: string;
  hire_date?: string; status: string; extra_data: Record<string, unknown>;
  created_at: string; updated_at: string;
}

export async function listEmployees(ws: string): Promise<EmpData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/employees`);
  return res.data;
}
export async function createEmployee(ws: string, data: Partial<EmpData>): Promise<EmpData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/employees`, data);
  return res.data;
}
export async function updateEmployee(ws: string, id: string, data: Partial<EmpData>): Promise<EmpData> {
  const res = await api.put(`/api/v1/workspaces/${ws}/company/employees/${id}`, data);
  return res.data;
}
export async function deleteEmployee(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/employees/${id}`);
}

// ─── Products ─────────────────────────────────────────

export interface ProdData {
  id: string; company_id: string; name: string; category?: string;
  description?: string; target_market: string[]; status: string;
  launch_date?: string; extra_data: Record<string, unknown>;
  created_at: string; updated_at: string;
}

export async function listProducts(ws: string): Promise<ProdData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/products`);
  return res.data;
}
export async function createProduct(ws: string, data: Partial<ProdData>): Promise<ProdData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/products`, data);
  return res.data;
}
export async function deleteProduct(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/products/${id}`);
}

// ─── Customers ────────────────────────────────────────

export interface CustData {
  id: string; company_id: string; name: string; market?: string;
  type?: string; contact_email?: string; extra_data: Record<string, unknown>;
  created_at: string; updated_at: string;
}

export async function listCustomers(ws: string): Promise<CustData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/customers`);
  return res.data;
}
export async function createCustomer(ws: string, data: Partial<CustData>): Promise<CustData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/customers`, data);
  return res.data;
}
export async function deleteCustomer(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/customers/${id}`);
}

// ─── Business Processes ───────────────────────────────

export interface ProcData {
  id: string; company_id: string; name: string; department_id?: string;
  owner_id?: string; description?: string; steps: unknown[];
  status: string; created_at: string; updated_at: string;
}

export async function listProcesses(ws: string): Promise<ProcData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/processes`);
  return res.data;
}
export async function createProcess(ws: string, data: Partial<ProcData>): Promise<ProcData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/processes`, data);
  return res.data;
}
export async function deleteProcess(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/processes/${id}`);
}

// ─── Company Goals ────────────────────────────────────

export interface GoalData {
  id: string; company_id: string; type: string; title: string;
  description?: string; target_value?: number; current_value?: number;
  progress_pct: number; start_date?: string; end_date?: string;
  status: string; created_at: string; updated_at: string;
}

export async function listGoals(ws: string): Promise<GoalData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/goals`);
  return res.data;
}
export async function createGoal(ws: string, data: Partial<GoalData>): Promise<GoalData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/goals`, data);
  return res.data;
}
export async function deleteGoal(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/goals/${id}`);
}

// ─── Company KPIs ─────────────────────────────────────

export interface KPIData {
  id: string; company_id: string; name: string; category?: string;
  current_value?: number; target_value?: number; unit?: string;
  period?: string; last_updated: string; created_at: string;
}

export async function listKPIs(ws: string): Promise<KPIData[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/company/kpis`);
  return res.data;
}
export async function createKPI(ws: string, data: Partial<KPIData>): Promise<KPIData> {
  const res = await api.post(`/api/v1/workspaces/${ws}/company/kpis`, data);
  return res.data;
}
export async function updateKPI(ws: string, id: string, data: Partial<KPIData>): Promise<KPIData> {
  const res = await api.put(`/api/v1/workspaces/${ws}/company/kpis/${id}`, data);
  return res.data;
}
export async function deleteKPI(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/company/kpis/${id}`);
}

// ─── Enterprise Memory ────────────────────────────────

export interface MemoryResult {
  id: string; memory_type: string; title: string; content: string;
  importance: number; access_count: number; entity_type?: string;
  similarity?: number; created_at: string; updated_at: string;
}

export async function listMemories(ws: string, type?: string): Promise<MemoryResult[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/memories`, { params: type ? { memory_type: type } : {} });
  return res.data;
}
export async function createMemory(ws: string, data: Partial<MemoryResult>): Promise<MemoryResult> {
  const res = await api.post(`/api/v1/workspaces/${ws}/memories`, data);
  return res.data;
}
export async function deleteMemory(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/memories/${id}`);
}
export async function recallMemories(ws: string, query: string, topK = 5): Promise<MemoryResult[]> {
  const res = await api.post(`/api/v1/workspaces/${ws}/memories/recall`, { query, top_k: topK });
  return res.data;
}

export interface MemoryEventResult {
  id: string; title: string; description?: string; event_date?: string;
  impact: string; tags: string[]; related_entities: unknown[];
  created_at: string;
}

export async function listMemoryEvents(ws: string): Promise<MemoryEventResult[]> {
  const res = await api.get(`/api/v1/workspaces/${ws}/memories/events`);
  return res.data;
}
export async function createMemoryEvent(ws: string, data: Partial<MemoryEventResult>): Promise<MemoryEventResult> {
  const res = await api.post(`/api/v1/workspaces/${ws}/memories/events`, data);
  return res.data;
}
export async function deleteMemoryEvent(ws: string, id: string): Promise<void> {
  await api.delete(`/api/v1/workspaces/${ws}/memories/events/${id}`);
}

// ─── Knowledge Graph ──────────────────────────────────

export interface GraphStats {
  nodes: number; relationships: number;
  labels: { label: string; count: number }[];
  connected: boolean;
}

export async function getGraphStats(ws: string): Promise<GraphStats> {
  const res = await api.get(`/api/v1/workspaces/${ws}/graph/stats`);
  return res.data;
}
export async function searchGraph(ws: string, query: string, topK = 5) {
  const res = await api.post(`/api/v1/workspaces/${ws}/graph/search`, { query, top_k: topK });
  return res.data;
}
export async function graphQuery(ws: string, cypher: string) {
  const res = await api.post(`/api/v1/workspaces/${ws}/graph/query`, { query: cypher });
  return res.data;
}
export async function syncGraph(ws: string) {
  const res = await api.post(`/api/v1/workspaces/${ws}/graph/sync`);
  return res.data;
}
