"""企业画像 Pydantic Schemas"""

from datetime import datetime, date
from pydantic import BaseModel, Field
import uuid


# ─── Company ───────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    industry: str | None = None
    description: str | None = None
    founded_year: int | None = None
    employee_count: int = 0
    markets: list[str] = []
    headquarters: str | None = None
    website: str | None = None
    extra_data: dict = {}


class CompanyUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    description: str | None = None
    founded_year: int | None = None
    employee_count: int | None = None
    markets: list[str] | None = None
    headquarters: str | None = None
    website: str | None = None
    extra_data: dict | None = None


class CompanyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    industry: str | None = None
    description: str | None = None
    founded_year: int | None = None
    employee_count: int
    markets: list
    headquarters: str | None = None
    website: str | None = None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Department ────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    type: str | None = None
    description: str | None = None
    head_id: uuid.UUID | None = None
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    name: str | None = None
    parent_id: uuid.UUID | None = None
    type: str | None = None
    description: str | None = None
    head_id: uuid.UUID | None = None
    sort_order: int | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str
    type: str | None = None
    description: str | None = None
    head_id: uuid.UUID | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentTreeResponse(DepartmentResponse):
    children: list["DepartmentTreeResponse"] = []


# ─── Position ──────────────────────────────────────────

class PositionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    department_id: uuid.UUID | None = None
    level: str | None = None
    description: str | None = None


class PositionUpdate(BaseModel):
    title: str | None = None
    department_id: uuid.UUID | None = None
    level: str | None = None
    description: str | None = None


class PositionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    department_id: uuid.UUID | None = None
    title: str
    level: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Employee ──────────────────────────────────────────

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    user_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    email: str | None = None
    phone: str | None = None
    hire_date: date | None = None
    status: str = "active"
    extra_data: dict = {}


class EmployeeUpdate(BaseModel):
    name: str | None = None
    user_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    email: str | None = None
    phone: str | None = None
    hire_date: date | None = None
    status: str | None = None
    extra_data: dict | None = None


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    hire_date: date | None = None
    status: str
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Product ───────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = None
    description: str | None = None
    target_market: list[str] = []
    status: str = "active"
    launch_date: date | None = None
    extra_data: dict = {}


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    target_market: list[str] | None = None
    status: str | None = None
    launch_date: date | None = None
    extra_data: dict | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    category: str | None = None
    description: str | None = None
    target_market: list
    status: str
    launch_date: date | None = None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Customer ──────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    market: str | None = None
    type: str | None = None
    contact_email: str | None = None
    extra_data: dict = {}


class CustomerUpdate(BaseModel):
    name: str | None = None
    market: str | None = None
    type: str | None = None
    contact_email: str | None = None
    extra_data: dict | None = None


class CustomerResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    market: str | None = None
    type: str | None = None
    contact_email: str | None = None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Business Process ──────────────────────────────────

class ProcessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    department_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    description: str | None = None
    steps: list[dict] = []
    status: str = "active"


class ProcessUpdate(BaseModel):
    name: str | None = None
    department_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    description: str | None = None
    steps: list[dict] | None = None
    status: str | None = None


class ProcessResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    department_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    description: str | None = None
    steps: list
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Company Goal ──────────────────────────────────────

class GoalCreate(BaseModel):
    type: str = "KPI"
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    target_value: float | None = None
    current_value: float | None = None
    progress_pct: float = 0
    direction: str = "higher"  # "higher" = 越高越好, "lower" = 越低越好（如退货率、成本）
    start_date: date | None = None
    end_date: date | None = None
    status: str = "active"


class GoalUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    description: str | None = None
    target_value: float | None = None
    current_value: float | None = None
    progress_pct: float | None = None
    direction: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class GoalResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    type: str
    title: str
    description: str | None = None
    target_value: float | None = None
    current_value: float | None = None
    progress_pct: float
    direction: str = "higher"
    start_date: date | None = None
    end_date: date | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Company KPI ───────────────────────────────────────

class KPICreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = None
    current_value: float | None = None
    target_value: float | None = None
    unit: str | None = None
    period: str | None = None


class KPIUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    current_value: float | None = None
    target_value: float | None = None
    unit: str | None = None
    period: str | None = None


class KPIResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    category: str | None = None
    current_value: float | None = None
    target_value: float | None = None
    unit: str | None = None
    period: str | None = None
    last_updated: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
