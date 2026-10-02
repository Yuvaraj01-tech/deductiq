from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CreateClaimRequest(BaseModel):
    retailer: str = Field(..., example="Walmart")
    deduction_code: str = Field(..., example="Code 22")
    deduction_reason: str = Field(..., example="Goods Shortage / Undershipment")
    amount: float = Field(..., gt=0, example=4250.00)
    invoice_number: str = Field(..., example="INV-2026-9041")
    invoice_date: str = Field(..., example="2026-09-15")
    invoice_amount: float = Field(..., gt=0, example=24000.00)
    po_number: str = Field(..., example="PO-WM-55102")
    po_date: str = Field(..., example="2026-09-01")
    bol_number: Optional[str] = Field("BOL-883912", example="BOL-883912")
    pod_status: Optional[str] = Field("Signed Clean - Stamp Verified", example="Signed Clean - Stamp Verified")
    signed_qty: Optional[int] = Field(1200, example=1200)
    invoiced_qty: Optional[int] = Field(1200, example=1200)
    claimed_shortage_qty: Optional[int] = Field(85, example=85)
    unit_price: Optional[float] = Field(50.0, example=50.0)
    notes: Optional[str] = Field(None, example="Automated creation from ERP EDI 812")

class UpdateClaimRequest(BaseModel):
    status: Optional[str] = None
    dispute_amount: Optional[float] = None
    win_probability: Optional[float] = None
    risk_level: Optional[str] = None
    notes: Optional[str] = None

class BatchDisputeRequest(BaseModel):
    claim_ids: List[int]

class UpdateSettingsRequest(BaseModel):
    settings: Dict[str, str]

class DisputeDossierUpdateRequest(BaseModel):
    legal_rebuttal: str
    status: Optional[str] = "Draft"
