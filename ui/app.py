import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.graph import build_graph
from setup_db import init_database


def process_invoice(graph, file_path):
    """Run a single invoice through the pipeline."""
    initial_state = {
        "invoice_path": file_path,
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
    return graph.invoke(initial_state)


def render_result(result):
    """Display pipeline results with expanding sections."""
    invoice = result.get("invoice") or {}
    validation = result.get("validation") or {}
    approval = result.get("approval") or {}
    payment = result.get("payment") or {}
    logs = result.get("logs", [])

    inv_num = invoice.get("invoice_number", "N/A")
    vendor = invoice.get("vendor", "N/A")
    total = invoice.get("total", 0) or 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Invoice", inv_num)
    col2.metric("Total", f"${total:,.2f}")

    val_passed = validation.get("passed", False)
    col3.metric("Validation", "PASSED" if val_passed else "FAILED")

    app_status = approval.get("status", "N/A").upper()
    col4.metric("Decision", app_status)

    st.divider()

    with st.expander("1. Ingestion", expanded=True):
        st.write(f"**Vendor:** {vendor}")
        st.write(f"**Invoice #:** {inv_num}")
        st.write(f"**Date:** {invoice.get('date', 'N/A')}")
        st.write(f"**Due Date:** {invoice.get('due_date', 'N/A')}")
        st.write(f"**Currency:** {invoice.get('currency', 'USD')}")

        items = invoice.get("line_items", [])
        if items:
            st.write("**Line Items:**")
            for item in items:
                st.write(f"  - {item.get('item')}: qty {item.get('quantity')} × ${item.get('unit_price', 0):.2f}")

        st.write(f"**Total:** ${total:,.2f}")

    with st.expander("2. Validation", expanded=True):
        flags = validation.get("flags", [])
        if val_passed:
            st.success(f"Validation passed ({len(flags)} flags)")
        else:
            st.error(f"Validation failed ({len(flags)} flags)")

        for flag in flags:
            severity = flag.get("severity", "info")
            msg = f"**[{flag.get('code')}]** {flag.get('message')}"
            if severity == "critical":
                st.error(msg)
            elif severity == "warning":
                st.warning(msg)
            else:
                st.info(msg)

        inv_checks = validation.get("inventory_checks", {})
        if inv_checks:
            st.write("**Inventory Checks:**")
            for item_name, check in inv_checks.items():
                status = "✅" if check.get("sufficient") else "❌"
                st.write(f"  {status} {item_name}: {check.get('requested', 0)} requested / {check.get('stock', 0)} in stock")

    with st.expander("3. Approval", expanded=True):
        if app_status == "APPROVED":
            st.success(f"Decision: {app_status}")
        elif app_status == "REJECTED":
            st.error(f"Decision: {app_status}")
        else:
            st.warning(f"Decision: {app_status}")

        st.write(f"**Reasoning:** {approval.get('reasoning', 'N/A')}")

        risk = approval.get("risk_score", 0)
        st.progress(min(risk, 1.0), text=f"Risk Score: {risk:.2f}")

        reflection = approval.get("reflection")
        if reflection:
            st.write(f"**Critic Reflection:** {reflection}")

    with st.expander("4. Payment", expanded=True):
        if payment.get("success"):
            st.success(f"Payment processed: {payment.get('message')}")
            st.write(f"**Transaction ID:** `{payment.get('transaction_id')}`")
        else:
            st.warning(f"Payment skipped: {payment.get('message', 'Invoice not approved')}")

    with st.expander("Pipeline Logs", expanded=False):
        for log in logs:
            st.code(log)


def main():
    st.set_page_config(page_title="Invoice Processing Agent", page_icon="🧾", layout="wide")
    st.title("🧾 Invoice Processing Agent")
    st.caption("Multi-agent system for automated invoice processing")

    init_database()
    graph = build_graph()

    st.sidebar.header("Process Invoices")

    mode = st.sidebar.radio("Mode", ["Single Invoice", "Batch Processing"])

    if mode == "Single Invoice":
        invoice_dir = Path("data/invoices")
        if invoice_dir.exists():
            files = sorted([f.name for f in invoice_dir.iterdir()
                          if f.suffix in [".json", ".csv", ".xml", ".txt", ".pdf"]])
            selected = st.sidebar.selectbox("Select test invoice", files)
            file_path = str(invoice_dir / selected)
        else:
            file_path = st.sidebar.text_input("Invoice file path")

        uploaded = st.sidebar.file_uploader("Or upload an invoice", type=["json", "csv", "xml", "txt", "pdf"])
        if uploaded:
            save_path = f"/tmp/{uploaded.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            file_path = save_path

        if st.sidebar.button("Process Invoice", type="primary"):
            with st.spinner("Processing invoice..."):
                result = process_invoice(graph, file_path)
            render_result(result)

    else:
        invoice_dir = Path("data/invoices")
        if st.sidebar.button("Process All Invoices", type="primary"):
            files = sorted([f for f in invoice_dir.iterdir()
                          if f.suffix in [".json", ".csv", ".xml", ".txt", ".pdf"]])

            progress = st.progress(0, text="Processing invoices...")
            results = []

            for i, f in enumerate(files):
                progress.progress((i + 1) / len(files), text=f"Processing {f.name}...")
                result = process_invoice(graph, str(f))
                results.append(result)

            progress.empty()

            approved = sum(1 for r in results if (r.get("approval") or {}).get("status") == "approved")
            rejected = sum(1 for r in results if (r.get("approval") or {}).get("status") == "rejected")
            escalated = sum(1 for r in results if (r.get("approval") or {}).get("status") == "escalated")
            total_spend = sum((r.get("invoice") or {}).get("total", 0) or 0 for r in results
                            if (r.get("approval") or {}).get("status") == "approved")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Approved", approved)
            col2.metric("Rejected", rejected)
            col3.metric("Escalated", escalated)
            col4.metric("Approved Spend", f"${total_spend:,.2f}")

            st.divider()

            for i, result in enumerate(results):
                inv = result.get("invoice") or {}
                inv_num = inv.get("invoice_number", f"Invoice {i+1}")
                with st.expander(f"{inv_num} — {inv.get('vendor', 'N/A')} — ${(inv.get('total', 0) or 0):,.2f}"):
                    render_result(result)


if __name__ == "__main__":
    main()