from typing import TypedDict, Optional, Annotated
from operator import add


class AgentState(TypedDict):
    invoice_path: str
    raw_content: str
    file_format: str
    invoice: Optional[dict]
    extraction_attempts: int
    validation: Optional[dict]
    approval: Optional[dict]
    payment: Optional[dict]
    logs: Annotated[list[str], add]
    error: Optional[str]
    token_usage: dict