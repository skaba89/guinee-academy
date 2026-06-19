from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


# --- Employee Schemas ---

class EmployeeBase(BaseModel):
    employee_number: str
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    job_title: str | None = None
    department: str | None = None
    hire_date: date
    is_active: bool = True
    date_of_birth: date | None = None
    place_of_birth: str | None = None
    nationality: str | None = None
    social_security_number: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    bank_name: str | None = None
    bank_iban: str | None = None
    bank_bic: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    employee_number: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    job_title: str | None = None
    department: str | None = None
    hire_date: date | None = None
    is_active: bool | None = None
    date_of_birth: date | None = None
    place_of_birth: str | None = None
    nationality: str | None = None
    social_security_number: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    bank_name: str | None = None
    bank_iban: str | None = None
    bank_bic: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

class Employee(EmployeeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Contract Schemas ---

class ContractBase(BaseModel):
    contract_number: str
    contract_type: str
    start_date: date
    end_date: date | None = None
    trial_period_end: date | None = None
    job_title: str
    gross_monthly_salary: float
    weekly_hours: float = 35.0
    notes: str | None = None
    is_current: bool = True
    employee_id: UUID

class ContractCreate(ContractBase):
    pass

class ContractUpdate(BaseModel):
    contract_number: str | None = None
    contract_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    trial_period_end: date | None = None
    job_title: str | None = None
    gross_monthly_salary: float | None = None
    weekly_hours: float | None = None
    notes: str | None = None
    is_current: bool | None = None

class Contract(ContractBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Leave Request Schemas ---

class LeaveRequestBase(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    total_days: int
    status: str = "PENDING"
    reason: str | None = None
    employee_id: UUID

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestUpdate(BaseModel):
    status: str | None = None
    reviewed_at: date | None = None

class LeaveRequest(LeaveRequestBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    reviewed_at: date | None = None

    class Config:
        from_attributes = True

# --- Payslip Schemas ---

class PayslipBase(BaseModel):
    period_month: int
    period_year: int
    gross_salary: float
    net_salary: float
    pay_date: date
    is_final: str = "false"
    pdf_url: str | None = None
    employee_id: UUID

class PayslipCreate(PayslipBase):
    pass

class PayslipUpdate(BaseModel):
    is_final: str | None = None
    pdf_url: str | None = None

class Payslip(PayslipBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
