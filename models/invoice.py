from pydantic import BaseModel, Field
from typing import Optional, Literal


class LineItem(BaseModel):
    """One row on an invoice."""
    item: str
    quantity: int
    unit_price: float


class InvoiceData(BaseModel):
    """The full data for an invoice."""
    invoice_number: Optional[str] = None
    vendor: Optional[str] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total: Optional[float] = None
    currency: str = "USD"
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    raw_format: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)


class ValidationFlag(BaseModel):
    """A single validation flag raised during invoice processing."""
    severity: Literal["critical", "warning", "info"]
    field: str
    message: str
    code: str


class ValidationResult(BaseModel):
    """Full output from the validation agent."""
    passed: bool = False
    flags: list[ValidationFlag] = Field(default_factory=list)
    inventory_checks: dict = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    """Output from the approval agent."""
    status: Literal["approved", "rejected", "escalated"]
    reasoning: str = ""
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reflection: Optional[str] = None
    requires_human_review: bool = False


class PaymentResult(BaseModel):
    """Payment processing outcome."""
    success: bool = False
    message: str = ""
    transaction_id: Optional[str] = None


class PipelineState(BaseModel):
    """Master state object that flows through the entire LangGraph pipeline."""
    invoice_path: str = ""
    raw_content: str = ""
    file_format: str = ""
    invoice: Optional[InvoiceData] = None
    extraction_attempts: int = 0
    validation: Optional[ValidationResult] = None
    approval: Optional[ApprovalDecision] = None
    payment: Optional[PaymentResult] = None
    logs: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    token_usage: dict = Field(default_factory=lambda: {"prompt": 0, "completion": 0, "total": 0})