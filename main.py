import argparse
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from agents.graph import build_graph
from setup_db import init_database

def main():
    load_dotenv()  # loads openai api from .env
    init_database()  # make sure DB exists
    console = Console()
    
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Invoice Processing Pipeline")
    parser.add_argument("--invoice_path", type=str, help="Path to a single invoice file")
    args = parser.parse_args()
    
    # Build and run the graph
    graph = build_graph()
    
    # Run the graph with initial state
    initial_state = {
        "invoice_path": args.invoice_path,
        "raw_content": "",
        "file_format": "",
        "invoice": None,
        "extraction_attempts": 0,
        "validation": None,
        "approval": None,
        "payment": None,
        "logs": [],
        "error": None,
        "token_usage": {"prompt": 0, "completion": 0, "total": 0}
    }
    result = graph.invoke(initial_state)

    # Print the results
    invoice = result.get("invoice") or {}
    validation = result.get("validation") or {}
    approval = result.get("approval") or {}
    payment = result.get("payment") or {}

    table = Table(title="Invoice Processing Result")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Invoice #", str(invoice.get("invoice_number", "N/A")))
    table.add_row("Vendor", str(invoice.get("vendor", "N/A")))
    table.add_row("Total", f"${invoice.get('total', 0):.2f}")
    table.add_row("Validation", "PASSED" if validation.get("passed") else "FAILED")
    table.add_row("Flags", str(len(validation.get("flags", []))))
    table.add_row("Approval", str(approval.get("status", "N/A")).upper())
    table.add_row("Payment", "SUCCESS" if payment.get("success") else "SKIPPED")

    console.print(table)

    # Print logs
    console.print(Panel("\n".join(result.get("logs", [])), title="Pipeline Logs"))

if __name__ == "__main__":
    main()