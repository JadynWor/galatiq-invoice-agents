from tools.payment_api import mock_payment

def pay_node(state):
    """Process payment if approved, log result either way."""
    invoice = state.get("invoice", {})
    approval = state.get("approval", {})
    
    inv_num = invoice.get("invoice_number", "unknown")
    vendor = invoice.get("vendor", "unknown")
    total = invoice.get("total", 0) or 0
    status = approval.get("status", "rejected")

    if status != "approved":
        return {
            "payment": {"success": False, "message": f"Payment skipped: invoice {status}", "transaction_id": None},
            "logs": [f"PAYMENT SKIPPED for {inv_num}: status is {status}"]
        }

    result = mock_payment(vendor, total)

    return {
        "payment": result.model_dump(),
        "logs": [f"PAID {inv_num}: ${total:.2f} to {vendor} (tx: {result.transaction_id})"]
    }