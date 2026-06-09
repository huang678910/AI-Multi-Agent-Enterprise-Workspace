"""企业画像 REST API — /api/v1/workspaces/{workspace_id}/company/..."""

import uuid
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.services.company_service import CompanyService
from app.schemas.company import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTreeResponse,
    PositionCreate, PositionUpdate, PositionResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    CustomerCreate, CustomerUpdate, CustomerResponse,
    ProcessCreate, ProcessUpdate, ProcessResponse,
    GoalCreate, GoalUpdate, GoalResponse,
    KPICreate, KPIUpdate, KPIResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/company", tags=["Company Profile"])


# ─── Helpers ───────────────────────────────────────────

async def _get_svc(workspace_id: str, current_user: User, min_role: str, db: AsyncSession) -> CompanyService:
    await require_workspace_role(workspace_id, current_user, min_role, db)
    return CompanyService(db, workspace_id)


# ─── Company Profile ───────────────────────────────────

@router.get("/profile", response_model=CompanyResponse | None)
async def get_profile(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.get_profile()


@router.put("/profile", response_model=CompanyResponse)
async def upsert_profile(
    workspace_id: uuid.UUID,
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_or_update_profile(data)


# ─── Departments ───────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentTreeResponse])
async def list_departments(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_departments()


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    workspace_id: uuid.UUID,
    data: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_department(data)


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    workspace_id: uuid.UUID,
    dept_id: uuid.UUID,
    data: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_department(str(dept_id), data)


@router.delete("/departments/{dept_id}", status_code=204)
async def delete_department(
    workspace_id: uuid.UUID,
    dept_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_department(str(dept_id))


# ─── Positions ─────────────────────────────────────────

@router.get("/positions", response_model=list[PositionResponse])
async def list_positions(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_positions()


@router.post("/positions", response_model=PositionResponse, status_code=201)
async def create_position(
    workspace_id: uuid.UUID,
    data: PositionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_position(data)


@router.put("/positions/{pos_id}", response_model=PositionResponse)
async def update_position(
    workspace_id: uuid.UUID,
    pos_id: uuid.UUID,
    data: PositionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_position(str(pos_id), data)


@router.delete("/positions/{pos_id}", status_code=204)
async def delete_position(
    workspace_id: uuid.UUID,
    pos_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_position(str(pos_id))


# ─── Employees ─────────────────────────────────────────

@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_employees()


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    workspace_id: uuid.UUID,
    data: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_employee(data)


@router.put("/employees/{emp_id}", response_model=EmployeeResponse)
async def update_employee(
    workspace_id: uuid.UUID,
    emp_id: uuid.UUID,
    data: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_employee(str(emp_id), data)


@router.delete("/employees/{emp_id}", status_code=204)
async def delete_employee(
    workspace_id: uuid.UUID,
    emp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_employee(str(emp_id))


# ─── Products ──────────────────────────────────────────

@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_products()


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    workspace_id: uuid.UUID,
    data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_product(data)


@router.put("/products/{prod_id}", response_model=ProductResponse)
async def update_product(
    workspace_id: uuid.UUID,
    prod_id: uuid.UUID,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_product(str(prod_id), data)


@router.delete("/products/{prod_id}", status_code=204)
async def delete_product(
    workspace_id: uuid.UUID,
    prod_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_product(str(prod_id))


# ─── Customers ─────────────────────────────────────────

@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_customers()


@router.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(
    workspace_id: uuid.UUID,
    data: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_customer(data)


@router.put("/customers/{cust_id}", response_model=CustomerResponse)
async def update_customer(
    workspace_id: uuid.UUID,
    cust_id: uuid.UUID,
    data: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_customer(str(cust_id), data)


@router.delete("/customers/{cust_id}", status_code=204)
async def delete_customer(
    workspace_id: uuid.UUID,
    cust_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_customer(str(cust_id))


# ─── Business Processes ────────────────────────────────

@router.get("/processes", response_model=list[ProcessResponse])
async def list_processes(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_processes()


@router.post("/processes", response_model=ProcessResponse, status_code=201)
async def create_process(
    workspace_id: uuid.UUID,
    data: ProcessCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_process(data)


@router.put("/processes/{proc_id}", response_model=ProcessResponse)
async def update_process(
    workspace_id: uuid.UUID,
    proc_id: uuid.UUID,
    data: ProcessUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_process(str(proc_id), data)


@router.delete("/processes/{proc_id}", status_code=204)
async def delete_process(
    workspace_id: uuid.UUID,
    proc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_process(str(proc_id))


# ─── Goals ─────────────────────────────────────────────

@router.get("/goals", response_model=list[GoalResponse])
async def list_goals(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_goals()


@router.post("/goals", response_model=GoalResponse, status_code=201)
async def create_goal(
    workspace_id: uuid.UUID,
    data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_goal(data)


@router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    workspace_id: uuid.UUID,
    goal_id: uuid.UUID,
    data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_goal(str(goal_id), data)


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(
    workspace_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_goal(str(goal_id))


# ─── KPIs ──────────────────────────────────────────────

@router.get("/kpis", response_model=list[KPIResponse])
async def list_kpis(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "member", db)
    return await svc.list_kpis()


@router.post("/kpis", response_model=KPIResponse, status_code=201)
async def create_kpi(
    workspace_id: uuid.UUID,
    data: KPICreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.create_kpi(data)


@router.put("/kpis/{kpi_id}", response_model=KPIResponse)
async def update_kpi(
    workspace_id: uuid.UUID,
    kpi_id: uuid.UUID,
    data: KPIUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    return await svc.update_kpi(str(kpi_id), data)


@router.delete("/kpis/{kpi_id}", status_code=204)
async def delete_kpi(
    workspace_id: uuid.UUID,
    kpi_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = await _get_svc(str(workspace_id), current_user, "admin", db)
    await svc.delete_kpi(str(kpi_id))
