"""Payment schemas for request/response validation"""
from datetime import date, datetime

from pydantic import UUID4, BaseModel, Field

from app.models.payment import InvoiceStatus, PaymentMethod, PaymentStatus


class StudentMin(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    registration_number: str

    class Config:
        from_attributes = True


# Payment schemas
class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="GNF", max_length=3)
    payment_date: date
    payment_method: PaymentMethod
    notes: str | None = Field(None, max_length=500)


class PaymentCreate(PaymentBase):
    student_id: UUID4
    invoice_id: UUID4 | None = None
    transaction_id: str | None = Field(None, max_length=255)


class PaymentUpdate(BaseModel):
    amount: float | None = Field(None, gt=0)
    payment_date: date | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    notes: str | None = Field(None, max_length=500)


class Payment(PaymentBase):
    id: UUID4
    tenant_id: UUID4
    student_id: UUID4
    invoice_id: UUID4 | None
    status: PaymentStatus
    reference: str
    transaction_id: str | None
    receipt_url: str | None
    students: StudentMin | None = Field(None, alias="student")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class PaymentList(BaseModel):
    items: list[Payment]
    total: int
    page: int
    page_size: int
    pages: int


# Invoice schemas
class InvoiceBase(BaseModel):
    issue_date: date
    due_date: date
    subtotal: float = Field(..., ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    total_amount: float = Field(..., gt=0)
    currency: str = Field(default="GNF", max_length=3)
    description: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=500)


class InvoiceCreate(InvoiceBase):
    student_id: UUID4
    invoice_number: str = Field(..., min_length=1, max_length=50)


class InvoiceUpdate(BaseModel):
    due_date: date | None = None
    subtotal: float | None = Field(None, ge=0)
    tax_amount: float | None = Field(None, ge=0)
    discount_amount: float | None = Field(None, ge=0)
    total_amount: float | None = Field(None, gt=0)
    status: InvoiceStatus | None = None
    description: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=500)


class Invoice(InvoiceBase):
    id: UUID4
    tenant_id: UUID4
    student_id: UUID4
    invoice_number: str
    status: InvoiceStatus
    amount_paid: float
    pdf_url: str | None
    created_at: datetime
    updated_at: datetime

    amount_due: float
    is_paid: bool
    student: StudentMin | None = None

    class Config:
        from_attributes = True


class InvoiceList(BaseModel):
    items: list[Invoice]
    total: int
    page: int
    page_size: int
    pages: int
