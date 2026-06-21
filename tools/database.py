import sqlite3
from config import DB_PATH


def check_inventory(item, quantity):
    """Check if item exists and has enough stock."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM inventory WHERE item = ?", (item,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return {"exists": False, "stock": 0, "requested": quantity, "sufficient": False}
    
    stock = row[0]
    return {"exists": True, "stock": stock, "requested": quantity, "sufficient": stock >= quantity}

def check_vendor(vendor):
    """check if vendor is known and trusted."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT trusted, risk_level FROM vendors WHERE name = ?", (vendor,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return {"exists": False, "trusted": False, "risk_level": "unknown"}
    
    trusted, risk_level = row
    return {"exists": True, "trusted": bool(trusted), "risk_level": risk_level}

def check_pricing(item, unit_price):
    """Check if pricing is within expected ranges."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT expected_unit_price, tolerance_pct FROM pricing WHERE item = ?", (item,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return {"known_price": False}
    
    expected, tolerance = row
    if expected == 0:
        return {"known_price": True, "expected": 0, "actual": unit_price, "within_tolerance": unit_price == 0}
    
    difference = abs(unit_price - expected) / expected
    return {"known_price": True, "expected": expected, "actual": unit_price, "within_tolerance": difference <= tolerance}
