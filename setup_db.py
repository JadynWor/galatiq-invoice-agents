import sqlite3
import os


def init_database(db_path: str = "inventory.db"):
    """Create and seed the mock legacy inventory database.
    
    Simulates Acme Corp's inventory, vendor, and pricing systems
    that the validation agent checks invoices against.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ── Inventory: what items exist and current stock levels ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item TEXT PRIMARY KEY,
            stock INTEGER,
            category TEXT DEFAULT 'general'
        )
    """)

    inventory_data = [
        ("WidgetA", 15, "widget"),
        ("WidgetB", 10, "widget"),
        ("GadgetX", 5, "gadget"),
        ("FakeItem", 0, "unknown"),
        # SuperGizmo, MegaSprocket, WidgetC intentionally excluded
        # Validation agent should flag these as unknown items
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO inventory VALUES (?, ?, ?)",
        inventory_data
    )

    # ── Vendors: known suppliers and their trust levels ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            name TEXT PRIMARY KEY,
            trusted INTEGER DEFAULT 1,
            risk_level TEXT DEFAULT 'low',
            avg_order_value REAL DEFAULT 0.0
        )
    """)

    vendor_data = [
        ("Widgets Inc.", 1, "low", 4100.0),
        ("Gadgets Co.", 1, "low", 15000.0),
        ("Fraudster LLC", 0, "high", 0.0),
        ("NoProd Industries", 0, "medium", 0.0),
        ("Consolidated Materials Group", 1, "low", 7185.0),
        ("Summit Manufacturing Co.", 1, "low", 3000.0),
        ("QuickShip Distributers", 1, "low", 9975.0),
        ("Precision Parts Ltd.", 1, "low", 5940.0),
        ("Global Supply Chain Partners", 1, "medium", 15225.0),
        ("Atlas Industrial Supply", 1, "medium", 22562.80),
        ("Acme Industrial Supplies", 1, "low", 2750.0),
        ("MegaWidgets Corp", 1, "medium", 15525.0),
        ("TechParts International", 1, "low", 4125.0),
        ("Reliable Components Inc.", 1, "low", 6500.0),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO vendors VALUES (?, ?, ?, ?)",
        vendor_data
    )

    # ── Pricing: expected unit prices with tolerance for flagging outliers ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pricing (
            item TEXT PRIMARY KEY,
            expected_unit_price REAL,
            tolerance_pct REAL DEFAULT 0.20,
            FOREIGN KEY (item) REFERENCES inventory(item)
        )
    """)

    pricing_data = [
        ("WidgetA", 250.0, 0.20),
        ("WidgetB", 500.0, 0.20),
        ("GadgetX", 750.0, 0.20),
        ("FakeItem", 0.0, 0.0),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO pricing VALUES (?, ?, ?)",
        pricing_data
    )

    # ── Processing history: populated at runtime by the pipeline ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_history (
            invoice_number TEXT PRIMARY KEY,
            processed_at TEXT,
            status TEXT,
            total REAL,
            vendor TEXT,
            flags_count INTEGER DEFAULT 0,
            tokens_used INTEGER DEFAULT 0,
            risk_score REAL DEFAULT 0.0
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at {os.path.abspath(db_path)}")


if __name__ == "__main__":
    init_database()