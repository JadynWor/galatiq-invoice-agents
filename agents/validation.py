from models.invoice import ValidationFlag, ValidationResult
from tools.database import check_inventory, check_vendor, check_pricing
from config import FRAUD_KEYWORDS


def validate_node(state):
    """Validate extracted invoice data against database and business rules."""
    invoice = state.get("invoice")
    
    if not invoice:
        return {
            "validation": {"passed": False, "flags": [], "inventory_checks": {}},
            "logs": ["ERROR: No invoice data to validate"]
        }
    
    flags = []
    inventory_checks = {}
    
    # Check 1: Missing required fields
    if not invoice.get("vendor"):
        flags.append(ValidationFlag(
            severity="critical",
            field="vendor",
            message="Vendor name is missing",
            code="MISSING_VENDOR"
        ))
    if not invoice.get("due_date"):
        flags.append(ValidationFlag(
            severity="critical",
            field="due_date",
            message="Due date is missing",
            code="MISSING_DUE_DATE"
        ))
      
    # Check 2: Negative quantities
    for item in invoice.get("line_items", []):
        if item.get("quantity", 0) <= 0:
            flags.append(ValidationFlag(
                severity="critical",
                field=f"line_items.{item.get('item')}",
                message=f"{item.get('item')} has invalid quantity: {item.get('quantity')}",
                code="NEGATIVE_QTY"
            ))

    # Check 3: Inventory checks per line item
    for item in invoice.get("line_items", []):
        item_name = item.get("item")
        quantity = item.get("quantity", 0)
        result = check_inventory(item_name, quantity)
        inventory_checks[item_name] = result
        
        if not result["exists"]:
            flags.append(ValidationFlag(
                severity="critical",
                field=f"line_items.{item_name}",
                message=f"{item_name} not found in inventory database",
                code="UNKNOWN_ITEM"
            ))
        elif not result["sufficient"]:
            flags.append(ValidationFlag(
                severity="critical",
                field=f"line_items.{item_name}",
                message=f"{item_name}: requested {quantity} but only {result['stock']} in stock",
                code="STOCK_EXCEEDED"
            ))
    # Check 4: Vendor check
    vendor_name = invoice.get("vendor")
    if vendor_name:
        vendor_result = check_vendor(vendor_name)
        if not vendor_result["exists"]:
            flags.append(ValidationFlag(
                severity="critical",
                field="vendor",
                message=f"Vendor {vendor_name} is unknown",
                code="UNKNOWN_VENDOR"
            ))
        elif not vendor_result["trusted"]:
            flags.append(ValidationFlag(
                severity="critical",
                field="vendor",
                message=f"Vendor {vendor_name} is untrusted",
                code="UNTRUSTED_VENDOR"
            ))
    # Check 5: Pricing check
    for item in invoice.get("line_items", []):
        item_name = item.get("item")
        unit_price = item.get("unit_price", 0)
        price_result = check_pricing(item_name, unit_price)
        if price_result.get("known_price") and not price_result.get("within_tolerance"):
            flags.append(ValidationFlag(
                severity="warning",
                field=f"line_items.{item_name}",
                message=f"{item_name}: price ${unit_price} outside expected ${price_result['expected']} ±{int(price_result.get('within_tolerance', 0.2) * 100)}%",
                code="PRICE_OUTLIER"
            ))

    # Check 6: Fraud keyword scan
    notes = (invoice.get("notes") or "").lower()
    found_keywords = [kw for kw in FRAUD_KEYWORDS if kw in notes]
    if found_keywords:
        flags.append(ValidationFlag(
            severity="warning",
            field="notes",
            message=f"Fraud signals detected: {', '.join(found_keywords)}",
            code="FRAUD_SIGNAL"
        ))

    # Determine pass/fail
    passed = not any(f.severity == "critical" for f in flags)

    inv_num = invoice.get("invoice_number", "unknown")
    flag_count = len(flags)
    critical_count = sum(1 for f in flags if f.severity == "critical")

    # Return state update
    return {
        "validation": {
            "passed": passed,
            "flags": [f.model_dump() for f in flags],
            "inventory_checks": inventory_checks
        },
        "logs": [f"Validated {inv_num}: {'PASSED' if passed else 'FAILED'} ({critical_count} critical, {flag_count} total flags)"]
    }