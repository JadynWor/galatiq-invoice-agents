from pathlib import Path
from tools.parsers import parse_invoice
from tools.llm_client import LLMClient
from models.invoice import InvoiceData, LineItem
import json


def ingest_node(state):
    """Extract structured data from an invoice file."""
    file_path = state["invoice_path"]

    # Step 1: Read the raw file content
    try:
        with open(file_path, "r") as f:
            raw_content = f.read()
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}", "logs": [f"ERROR: Failed to read {file_path}"]}

    # Step 2: Try the deterministic parser first (json, csv, xml)
    ext = Path(file_path).suffix.lower()
    invoice = parse_invoice(file_path)
    if invoice:
        return {
            "raw_content": raw_content,
            "file_format": ext,
            "invoice": invoice.model_dump(),
            "extraction_attempts": 1,
            "logs": [f"Parsed {file_path} using deterministic {ext} parser"]
        }

    # Step 3: Use LLM for messy formats (txt, pdf)
    llm = LLMClient()

    system_prompt = """Extract structured invoice data from this text.
Return JSON with these exact fields:
- invoice_number (string)
- vendor (string)
- date (string)
- due_date (string)
- line_items (array of objects with: item, quantity, unit_price)
- subtotal (number)
- tax_amount (number)
- total (number)
- currency (string, default USD)
- payment_terms (string)
- notes (string, any extra info)
Handle typos and abbreviations. If a field is missing, use null."""

    response = llm.call(system_prompt, raw_content, json_mode=True)

    if not response:
        return {
            "raw_content": raw_content,
            "file_format": ext,
            "error": "LLM returned no response",
            "extraction_attempts": 1,
            "logs": [f"ERROR: LLM failed to extract data from {file_path}"]
        }

    # Step 4: Parse LLM response into InvoiceData
    try:
        data = json.loads(response)

        line_items = []
        for item in data.get("line_items", []):
            line_items.append(LineItem(
                item=item.get("item"),
                quantity=item.get("quantity"),
                unit_price=item.get("unit_price")
            ))

        invoice = InvoiceData(
            invoice_number=data.get("invoice_number"),
            vendor=data.get("vendor"),
            date=data.get("date"),
            due_date=data.get("due_date"),
            subtotal=data.get("subtotal"),
            tax_amount=data.get("tax_amount"),
            total=data.get("total"),
            currency=data.get("currency", "USD"),
            payment_terms=data.get("payment_terms"),
            notes=data.get("notes"),
            line_items=line_items,
            raw_format=ext.replace(".", "")
        )

        return {
            "raw_content": raw_content,
            "file_format": ext,
            "invoice": invoice.model_dump(),
            "extraction_attempts": 1,
            "logs": [f"Extracted invoice via LLM from {file_path}"],
            "token_usage": llm.token_usage
        }
    except Exception as e:
        return {
            "raw_content": raw_content,
            "file_format": ext,
            "error": f"LLM extraction failed: {str(e)}",
            "extraction_attempts": 1,
            "logs": [f"ERROR: LLM extraction failed for {file_path}: {str(e)}"]
        }