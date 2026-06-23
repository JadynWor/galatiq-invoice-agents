import argparse
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from agents.graph import build_graph
from setup_db import init_database
from pathlib import Path


def process_single(graph, invoice_path, console):
    """Process one invoice and print the result."""
    initial_state = {
        "invoice_path": invoice_path,
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
    console.print(Panel("\n".join(result.get("logs", [])), title="Pipeline Logs"))

    return result


def process_batch(graph, invoice_dir, console):
    """Process all invoices in a directory and print summary."""
    invoice_files = sorted(Path(invoice_dir).glob("*"))
    invoice_files = [f for f in invoice_files if f.suffix in [".json", ".csv", ".xml", ".txt", ".pdf"]]

    results = []
    for f in invoice_files:
        console.print(f"\n[bold]Processing {f.name}...[/bold]")
        result = process_single(graph, str(f), console)
        results.append(result)

    # Summary table
    console.print("\n")
    summary = Table(title="Batch Summary")
    summary.add_column("Invoice #", style="cyan")
    summary.add_column("Vendor", style="white")
    summary.add_column("Total", style="green")
    summary.add_column("Validation", style="yellow")
    summary.add_column("Approval", style="magenta")
    summary.add_column("Payment", style="blue")

    total_approved = 0
    total_rejected = 0

    for r in results:
        inv = r.get("invoice") or {}
        val = r.get("validation") or {}
        app = r.get("approval") or {}
        pay = r.get("payment") or {}

        status = app.get("status", "N/A")
        if status == "approved":
            total_approved += 1
        else:
            total_rejected += 1

        summary.add_row(
            str(inv.get("invoice_number", "N/A")),
            str(inv.get("vendor", "N/A")),
            f"${inv.get('total', 0) or 0:.2f}",
            "PASS" if val.get("passed") else "FAIL",
            status.upper(),
            "YES" if pay.get("success") else "NO"
        )

    console.print(summary)
    console.print(f"\n[green]Approved: {total_approved}[/green] | [red]Rejected: {total_rejected}[/red] | Total: {len(results)}")


def main():
    load_dotenv()
    init_database()
    console = Console()

    parser = argparse.ArgumentParser(description="Invoice Processing Pipeline")
    parser.add_argument("--invoice_path", type=str, help="Path to a single invoice file")
    parser.add_argument("--invoice_dir", type=str, help="Path to directory of invoices for batch processing")
    args = parser.parse_args()

    graph = build_graph()

    if args.invoice_dir:
        process_batch(graph, args.invoice_dir, console)
    elif args.invoice_path:
        process_single(graph, args.invoice_path, console)
    else:
        console.print("[red]Provide --invoice_path or --invoice_dir[/red]")


if __name__ == "__main__":
    main()