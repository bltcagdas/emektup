from typing import Optional
from pydantic import BaseModel, Field

class PdfGenerateJobPayload(BaseModel):
    job_type: str = Field(default="pdf_generate")
    job_id: str
    order_id: str
    tracking_code: Optional[str] = None
    requested_by: str = Field(default="system:webhook")
    attempt: int = Field(default=1)

class PiiCleanupJobPayload(BaseModel):
    job_type: str = Field(default="pii_cleanup")
    job_id: str
    cutoff_days: int = Field(default=30)
    dry_run: bool = Field(default=True)
    requested_by: str = Field(default="system:scheduler")

class OpsJobResponse(BaseModel):
    message: str
    status: str
    job_id: str
