import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.graph import build_graph
from setup_db import init_database


@st.cache_resource
def get_graph():
    """Build graph once and cache it."""
    init_database()
    return build_graph()


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
    """Display pipeline results."""
    invoice = result.get("invoice") or {}
    validation = result.get("validation") or {}
    approval = result.get("approval") or {}
    payment = result.get("payment") or {}

    inv_num = invoice.get("invoice_number", "N/A")
    vendor = invoice.get("vendor", "N/A")
    total = invoice.get("total", 0) or 0
    val_passed = validation.get("passed", False)
    app_status = approval.get("status", "N/A").upper()

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Invoice", inv_num)
    c2.metric("Total", f"${total:,.2f}")
    c3.metric("Validation", "✅ PASS" if val_passed else "❌ FAIL")
    c4.metric("Decision", app_status)

    # Ingestion
    with st.expander("📥 1. Ingestion — Data Extraction", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Vendor:** {vendor}")
            st.write(f"**Invoice #:** {inv_num}")
            st.write(f"**Date:** {invoice.get('date', 'N/A')}")
        with col2:
            st.write(f"**Due Date:** {invoice.get('due_date', 'N/A')}")
            st.write(f"**Currency:** {invoice.get('currency', 'USD')}")
            st.write(f"**Payment Terms:** {invoice.get('payment_terms', 'N/A')}")

        items = invoice.get("line_items", [])
        if items:
            st.markdown("**Line Items:**")
            item_data = []
            for item in items:
                item_data.append({
                    "Item": item.get("item"),
                    "Qty": item.get("quantity"),
                    "Unit Price": f"${item.get('unit_price', 0):.2f}",
                })
            st.table(item_data)

    # Validation
    with st.expander("🔍 2. Validation — Database Checks", expanded=False):
        flags = validation.get("flags", [])
        if val_passed:
            st.success(f"All checks passed ({len(flags)} flags)")
        else:
            st.error(f"Validation failed — {len(flags)} issue(s) found")

        for flag in flags:
            sev = flag.get("severity")
            msg = f"**{flag.get('code')}** — {flag.get('message')}"
            if sev == "critical":
                st.error(msg)
            elif sev == "warning":
                st.warning(msg)
            else:
                st.info(msg)

    # Approval
    with st.expander("✅ 3. Approval — VP Review", expanded=False):
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
            st.info(f"**Critic Reflection:** {reflection}")

    # Payment
    with st.expander("💳 4. Payment — Processing", expanded=False):
        if payment.get("success"):
            st.success(f"{payment.get('message')}")
            st.code(f"Transaction ID: {payment.get('transaction_id')}")
        else:
            st.warning(payment.get("message", "Payment skipped — invoice not approved"))

    # Logs
    with st.expander("📋 Pipeline Logs", expanded=False):
        for log in result.get("logs", []):
            st.text(log)


def main():
    st.set_page_config(page_title="Invoice Processing Agent", page_icon="🧾", layout="wide")
    st.title("🧾 Invoice Processing Agent")
    st.caption("Multi-agent system for automated invoice processing | LangGraph + OpenAI")

    graph = get_graph()

    mode = st.sidebar.radio("Mode", ["Single Invoice", "Batch Processing"])

    if mode == "Single Invoice":
        st.sidebar.markdown("---")
        invoice_dir = Path("data/invoices")
        files = sorted([f.name for f in invoice_dir.iterdir()
                       if f.suffix in [".json", ".csv", ".xml", ".txt", ".pdf"]])
        selected = st.sidebar.selectbox("Select invoice", files)

        uploaded = st.sidebar.file_uploader("Or upload", type=["json", "csv", "xml", "txt", "pdf"])

        if uploaded:
            save_path = f"/tmp/{uploaded.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            file_path = save_path
        else:
            file_path = str(invoice_dir / selected)

        if st.sidebar.button("🚀 Process Invoice", type="primary", use_container_width=True):
            with st.status("Processing invoice...", expanded=True) as status:
                st.write("📥 Running ingestion agent...")
                result = process_invoice(graph, file_path)
                st.write("🔍 Validation complete")
                st.write("✅ Approval decision made")
                status.update(label="Processing complete!", state="complete")
            render_result(result)

    else:
        st.sidebar.markdown("---")
        if st.sidebar.button("🚀 Process All Invoices", type="primary", use_container_width=True):
            invoice_dir = Path("data/invoices")
            files = sorted([f for f in invoice_dir.iterdir()
                          if f.suffix in [".json", ".csv", ".xml", ".txt", ".pdf"]])

            progress = st.progress(0, text="Starting batch processing...")
            results = []

            for i, f in enumerate(files):
                progress.progress((i + 1) / len(files), text=f"Processing {f.name}...")
                result = process_invoice(graph, str(f))
                results.append(result)

            progress.empty()

            # Summary
            approved = sum(1 for r in results if (r.get("approval") or {}).get("status") == "approved")
            rejected = sum(1 for r in results if (r.get("approval") or {}).get("status") == "rejected")
            escalated = sum(1 for r in results if (r.get("approval") or {}).get("status") == "escalated")
            total_approved = sum(
                (r.get("invoice") or {}).get("total", 0) or 0 for r in results
                if (r.get("approval") or {}).get("status") == "approved"
            )
            total_rejected = sum(
                (r.get("invoice") or {}).get("total", 0) or 0 for r in results
                if (r.get("approval") or {}).get("status") != "approved"
            )

            st.subheader("Batch Summary")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Invoices", len(results))
            c2.metric("Approved", approved)
            c3.metric("Rejected", rejected)
            c4.metric("Escalated", escalated)
            c5.metric("Approved Spend", f"${total_approved:,.2f}")

            st.divider()

            for result in results:
                inv = result.get("invoice") or {}
                app = result.get("approval") or {}
                inv_num = inv.get("invoice_number", "N/A")
                status = app.get("status", "N/A").upper()
                total = inv.get("total", 0) or 0
                icon = "✅" if status == "APPROVED" else "❌" if status == "REJECTED" else "⚠️"

                with st.expander(f"{icon} {inv_num} — {inv.get('vendor', 'N/A')} — ${total:,.2f} — {status}"):
                    render_result(result)


if __name__ == "__main__":
    main()