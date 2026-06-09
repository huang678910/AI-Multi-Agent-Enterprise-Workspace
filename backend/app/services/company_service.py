"""企业画像 CRUD 业务逻辑"""

import uuid
import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import (
    Company, Department, Position, Employee,
    Product, Customer, BusinessProcess, CompanyGoal, CompanyKPI,
)
from app.schemas.company import (
    CompanyCreate, CompanyUpdate,
    DepartmentCreate, DepartmentUpdate,
    PositionCreate, PositionUpdate,
    EmployeeCreate, EmployeeUpdate,
    ProductCreate, ProductUpdate,
    CustomerCreate, CustomerUpdate,
    ProcessCreate, ProcessUpdate,
    GoalCreate, GoalUpdate,
    KPICreate, KPIUpdate,
)

logger = logging.getLogger(__name__)


class CompanyService:

    def __init__(self, db: AsyncSession, workspace_id: str):
        self.db = db
        self.workspace_id = uuid.UUID(workspace_id)

    async def _get_company(self) -> Company | None:
        """获取该 workspace 的企业（1:1），不存在则返回 None"""
        result = await self.db.execute(
            select(Company).where(Company.workspace_id == self.workspace_id)
        )
        return result.scalar_one_or_none()

    async def _get_or_404(self, model, id_val):
        """通用获取或404"""
        company = await self._get_company()
        if not company:
            raise ValueError("Company profile not found. Create it first.")
        result = await self.db.execute(
            select(model).where(
                model.id == id_val,
                model.company_id == company.id
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise ValueError(f"{model.__name__} not found")
        return obj

    # ─── Company Profile ───────────────────────────────

    async def get_profile(self) -> Company | None:
        return await self._get_company()

    async def create_or_update_profile(self, data: CompanyUpdate) -> Company:
        company = await self._get_company()
        update_dict = data.model_dump(exclude_unset=True)
        if company:
            for k, v in update_dict.items():
                setattr(company, k, v)
        else:
            # Creating new — name is required
            if not update_dict.get("name"):
                raise ValueError("Company name is required to create a profile")
            company = Company(workspace_id=self.workspace_id, **update_dict)
            self.db.add(company)
        await self.db.flush()
        await self.db.refresh(company)
        return company

    async def get_company_summary(self) -> str:
        """生成企业信息摘要文本（注入 Agent 上下文）"""
        company = await self._get_company()
        if not company:
            return ""

        parts = [f"Company: {company.name}"]
        if company.industry:
            parts.append(f"Industry: {company.industry}")
        if company.description:
            parts.append(f"Description: {company.description}")
        if company.markets:
            parts.append(f"Markets: {', '.join(company.markets)}")
        if company.headquarters:
            parts.append(f"HQ: {company.headquarters}")
        if company.employee_count:
            parts.append(f"Employees: {company.employee_count}")

        # 部门
        dept_result = await self.db.execute(
            select(Department).where(Department.company_id == company.id)
        )
        depts = dept_result.scalars().all()
        if depts:
            parts.append(f"Departments: {', '.join(d.name for d in depts)}")

        # 产品
        prod_result = await self.db.execute(
            select(Product).where(Product.company_id == company.id)
        )
        prods = prod_result.scalars().all()
        if prods:
            parts.append(f"Products: {', '.join(p.name for p in prods)}")

        # KPI
        kpi_result = await self.db.execute(
            select(CompanyKPI).where(CompanyKPI.company_id == company.id)
        )
        kpis = kpi_result.scalars().all()
        if kpis:
            parts.append("KPIs: " + "; ".join(
                f"{k.name}={k.current_value}{k.unit or ''}" for k in kpis
            ))

        return "\n".join(parts)

    # ─── Departments ───────────────────────────────────

    async def list_departments(self) -> list[Department]:
        result = await self.db.execute(
            select(Department)
            .where(Department.company_id == (await self._get_company()).id)
            .options(selectinload(Department.children))
            .order_by(Department.sort_order)
        )
        return list(result.scalars().all())

    async def create_department(self, data: DepartmentCreate) -> Department:
        company = await self._get_company()
        dept = Department(company_id=company.id, **data.model_dump())
        self.db.add(dept)
        await self.db.flush()
        await self.db.refresh(dept)
        return dept

    async def update_department(self, dept_id: str, data: DepartmentUpdate) -> Department:
        dept = await self._get_or_404(Department, uuid.UUID(dept_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(dept, k, v)
        await self.db.flush()
        await self.db.refresh(dept)
        return dept

    async def delete_department(self, dept_id: str) -> None:
        dept = await self._get_or_404(Department, uuid.UUID(dept_id))
        await self.db.delete(dept)
        await self.db.flush()

    # ─── Positions ─────────────────────────────────────

    async def list_positions(self) -> list[Position]:
        company = await self._get_company()
        result = await self.db.execute(
            select(Position).where(Position.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_position(self, data: PositionCreate) -> Position:
        company = await self._get_company()
        pos = Position(company_id=company.id, **data.model_dump())
        self.db.add(pos)
        await self.db.flush()
        await self.db.refresh(pos)
        return pos

    async def update_position(self, pos_id: str, data: PositionUpdate) -> Position:
        pos = await self._get_or_404(Position, uuid.UUID(pos_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(pos, k, v)
        await self.db.flush()
        await self.db.refresh(pos)
        return pos

    async def delete_position(self, pos_id: str) -> None:
        pos = await self._get_or_404(Position, uuid.UUID(pos_id))
        await self.db.delete(pos)
        await self.db.flush()

    # ─── Employees ─────────────────────────────────────

    async def list_employees(self) -> list[Employee]:
        company = await self._get_company()
        result = await self.db.execute(
            select(Employee).where(Employee.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_employee(self, data: EmployeeCreate) -> Employee:
        company = await self._get_company()
        emp = Employee(company_id=company.id, **data.model_dump())
        self.db.add(emp)
        await self.db.flush()
        await self.db.refresh(emp)
        return emp

    async def update_employee(self, emp_id: str, data: EmployeeUpdate) -> Employee:
        emp = await self._get_or_404(Employee, uuid.UUID(emp_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(emp, k, v)
        await self.db.flush()
        await self.db.refresh(emp)
        return emp

    async def delete_employee(self, emp_id: str) -> None:
        emp = await self._get_or_404(Employee, uuid.UUID(emp_id))
        await self.db.delete(emp)
        await self.db.flush()

    # ─── Products ──────────────────────────────────────

    async def list_products(self) -> list[Product]:
        company = await self._get_company()
        result = await self.db.execute(
            select(Product).where(Product.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_product(self, data: ProductCreate) -> Product:
        company = await self._get_company()
        prod = Product(company_id=company.id, **data.model_dump())
        self.db.add(prod)
        await self.db.flush()
        await self.db.refresh(prod)
        return prod

    async def update_product(self, prod_id: str, data: ProductUpdate) -> Product:
        prod = await self._get_or_404(Product, uuid.UUID(prod_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(prod, k, v)
        await self.db.flush()
        await self.db.refresh(prod)
        return prod

    async def delete_product(self, prod_id: str) -> None:
        prod = await self._get_or_404(Product, uuid.UUID(prod_id))
        await self.db.delete(prod)
        await self.db.flush()

    # ─── Customers ─────────────────────────────────────

    async def list_customers(self) -> list[Customer]:
        company = await self._get_company()
        result = await self.db.execute(
            select(Customer).where(Customer.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_customer(self, data: CustomerCreate) -> Customer:
        company = await self._get_company()
        cust = Customer(company_id=company.id, **data.model_dump())
        self.db.add(cust)
        await self.db.flush()
        await self.db.refresh(cust)
        return cust

    async def update_customer(self, cust_id: str, data: CustomerUpdate) -> Customer:
        cust = await self._get_or_404(Customer, uuid.UUID(cust_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(cust, k, v)
        await self.db.flush()
        await self.db.refresh(cust)
        return cust

    async def delete_customer(self, cust_id: str) -> None:
        cust = await self._get_or_404(Customer, uuid.UUID(cust_id))
        await self.db.delete(cust)
        await self.db.flush()

    # ─── Business Processes ────────────────────────────

    async def list_processes(self) -> list[BusinessProcess]:
        company = await self._get_company()
        result = await self.db.execute(
            select(BusinessProcess).where(BusinessProcess.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_process(self, data: ProcessCreate) -> BusinessProcess:
        company = await self._get_company()
        proc = BusinessProcess(company_id=company.id, **data.model_dump())
        self.db.add(proc)
        await self.db.flush()
        await self.db.refresh(proc)
        return proc

    async def update_process(self, proc_id: str, data: ProcessUpdate) -> BusinessProcess:
        proc = await self._get_or_404(BusinessProcess, uuid.UUID(proc_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(proc, k, v)
        await self.db.flush()
        await self.db.refresh(proc)
        return proc

    async def delete_process(self, proc_id: str) -> None:
        proc = await self._get_or_404(BusinessProcess, uuid.UUID(proc_id))
        await self.db.delete(proc)
        await self.db.flush()

    # ─── Goals ─────────────────────────────────────────

    async def list_goals(self) -> list[CompanyGoal]:
        company = await self._get_company()
        result = await self.db.execute(
            select(CompanyGoal).where(CompanyGoal.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_goal(self, data: GoalCreate) -> CompanyGoal:
        company = await self._get_company()
        # Auto-calculate progress from current/target if not explicitly set
        values = data.model_dump()
        if not values.get("progress_pct") and values.get("current_value") and values.get("target_value"):
            target = values["target_value"]
            if target and target > 0:
                values["progress_pct"] = round((values["current_value"] / target) * 100)
        goal = CompanyGoal(company_id=company.id, **values)
        self.db.add(goal)
        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def update_goal(self, goal_id: str, data: GoalUpdate) -> CompanyGoal:
        goal = await self._get_or_404(CompanyGoal, uuid.UUID(goal_id))
        update_dict = data.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            setattr(goal, k, v)
        # Recalculate progress if current or target changed
        if "current_value" in update_dict or "target_value" in update_dict:
            cv = goal.current_value
            tv = goal.target_value
            if cv is not None and tv is not None and tv > 0:
                goal.progress_pct = round((cv / tv) * 100)
        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def delete_goal(self, goal_id: str) -> None:
        goal = await self._get_or_404(CompanyGoal, uuid.UUID(goal_id))
        await self.db.delete(goal)
        await self.db.flush()

    # ─── KPIs ──────────────────────────────────────────

    async def list_kpis(self) -> list[CompanyKPI]:
        company = await self._get_company()
        result = await self.db.execute(
            select(CompanyKPI).where(CompanyKPI.company_id == company.id)
        )
        return list(result.scalars().all())

    async def create_kpi(self, data: KPICreate) -> CompanyKPI:
        company = await self._get_company()
        kpi = CompanyKPI(company_id=company.id, **data.model_dump())
        self.db.add(kpi)
        await self.db.flush()
        await self.db.refresh(kpi)
        return kpi

    async def update_kpi(self, kpi_id: str, data: KPIUpdate) -> CompanyKPI:
        kpi = await self._get_or_404(CompanyKPI, uuid.UUID(kpi_id))
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(kpi, k, v)
        await self.db.flush()
        await self.db.refresh(kpi)
        return kpi

    async def delete_kpi(self, kpi_id: str) -> None:
        kpi = await self._get_or_404(CompanyKPI, uuid.UUID(kpi_id))
        await self.db.delete(kpi)
        await self.db.flush()
