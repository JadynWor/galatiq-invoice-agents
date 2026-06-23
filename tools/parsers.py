import json
import csv
import xml.etree.ElementTree as ET
import pdfplumber
from pathlib import Path
from models.invoice import InvoiceData, LineItem


def parse_json(file_path):
    """Parse a JSON invoice file."""
    with open(file_path, "r") as f:
        data = json.load(f)
    
    vendor_raw = data.get("vendor")
    if isinstance(vendor_raw, dict):
        vendor = vendor_raw.get("name")
    else:
        vendor = vendor_raw

    line_items = []
    for item in data.get("line_items", []):
        line_items.append(LineItem(
            item=item.get("item"),
            quantity=item.get("quantity"),
            unit_price=item.get("unit_price")
        ))
    
    return InvoiceData(
        invoice_number=data.get("invoice_number"),
        vendor=vendor,
        date=data.get("date"),
        due_date=data.get("due_date"),
        subtotal=data.get("subtotal"),
        tax_amount=data.get("tax_amount"),
        total=data.get("total"),
        currency=data.get("currency", "USD"),
        payment_terms=data.get("payment_terms"),
        notes=data.get("notes"),
        line_items=line_items,
        raw_format="json"
    )


def parse_csv(file_path):
    """Parse a CSV invoice file. Detects vertical vs columnar format."""
    with open(file_path, "r") as f:
        reader = list(csv.reader(f))
    
    headers = [h.strip().lower() for h in reader[0]]
    
    if headers[0] == "field":
        return _parse_csv_vertical(reader)
    else:
        return _parse_csv_columnar(reader)


def _parse_csv_vertical(reader):
    """Parse field,value CSV format (like INV-1006)."""
    data = {}
    line_items = []

    for row in reader[1:]:
        if len(row) < 2:
            continue
        field = row[0].strip()
        value = row[1].strip()
        
        if field == "item":
            line_items.append({"item": value})
        elif field == "quantity":
            line_items[-1]["quantity"] = int(value)
        elif field == "unit_price":
            line_items[-1]["unit_price"] = float(value)
        else:
            data[field] = value

    return InvoiceData(
        invoice_number=data.get("invoice_number"),
        vendor=data.get("vendor"),
        date=data.get("date"),
        due_date=data.get("due_date"),
        subtotal=float(data.get("subtotal", 0)),
        tax_amount=float(data.get("tax", 0)),
        total=float(data.get("total", 0)),
        currency=data.get("currency", "USD"),
        payment_terms=data.get("payment_terms"),
        notes=data.get("notes"),
        line_items=[LineItem(**item) for item in line_items],
        raw_format="csv"
    )


def _parse_csv_columnar(reader):
    """Parse columnar CSV format (like INV-1007, INV-1015)."""
    line_items = []
    invoice_number = None
    vendor = None
    date = None
    due_date = None
    subtotal = None
    tax_amount = None
    total = None

    for row in reader[1:]:
        if len(row) < 7:
            continue
        
        if not row[0].strip():
            label = row[6].strip().lower() if row[6].strip() else ""
            value = float(row[7].strip()) if len(row) > 7 and row[7].strip() else None
            if "subtotal" in label:
                subtotal = value
            elif "tax" in label:
                tax_amount = value
            elif "total" in label:
                total = value
            continue
        
        invoice_number = row[0].strip()
        vendor = row[1].strip()
        date = row[2].strip()
        due_date = row[3].strip()
        
        line_items.append(LineItem(
            item=row[4].strip(),
            quantity=int(row[5].strip()),
            unit_price=float(row[6].strip())
        ))

    return InvoiceData(
        invoice_number=invoice_number,
        vendor=vendor,
        date=date,
        due_date=due_date,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        line_items=line_items,
        raw_format="csv"
    )


def parse_xml(file_path):
    """Parse an XML invoice file."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    header = root.find("header")
    totals = root.find("totals")
    
    line_items = []
    for item in root.findall(".//line_items/item"):
        line_items.append(LineItem(
            item=item.find("name").text,
            quantity=int(item.find("quantity").text),
            unit_price=float(item.find("unit_price").text)
        ))
    
    return InvoiceData(
        invoice_number=header.find("invoice_number").text if header.find("invoice_number") is not None else None,
        vendor=header.find("vendor").text if header.find("vendor") is not None else None,
        date=header.find("date").text if header.find("date") is not None else None,
        due_date=header.find("due_date").text if header.find("due_date") is not None else None,
        currency=header.find("currency").text if header.find("currency") is not None else "USD",
        subtotal=float(totals.find("subtotal").text) if totals.find("subtotal") is not None else None,
        tax_amount=float(totals.find("tax_amount").text) if totals.find("tax_amount") is not None else None,
        total=float(totals.find("total").text) if totals.find("total") is not None else None,
        payment_terms=root.find("payment_terms").text if root.find("payment_terms") is not None else None,
        line_items=line_items,
        raw_format="xml"
    )


def parse_invoice(file_path):
    """Route to the correct parser based on file extension."""
    ext = Path(file_path).suffix.lower()
    
    if ext == ".json":
        return parse_json(file_path)
    elif ext == ".csv":
        return parse_csv(file_path)
    elif ext == ".xml":
        return parse_xml(file_path)
    elif ext == ".txt":
        return None
    elif ext == ".pdf":
        return None
    else:
        raise ValueError(f"Unsupported file format: {ext}")