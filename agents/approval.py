from tools.llm_client import LLMClient
from models.invoice import ApprovalDecision
from config import AUTO_APPROVE_LIMIT
import json


def approve_node(state):
    """VP level approval with rule-based fast paths and LLM reflection."""
    invoice = state.get("invoice", {})
    validation = state.get("validation", {})

    total = invoice.get("total", 0) or 0
    flags = validation.get("flags", [])
    passed = validation.get("passed", False)
    inv_num = invoice.get("invoice_number", "unknown")

    # Auto-reject: validation failed
    if not passed:
        decision = ApprovalDecision(
            status="rejected",
            reasoning="Critical validation failures: " + ", ".join(
                f["code"] for f in flags if f["severity"] == "critical"
            ),
            risk_score=1.0
        )
        return {
            "approval": decision.model_dump(),
            "logs": [f"REJECTED {inv_num}: critical validation failures"]
        }

    # Auto-approve: under threshold, no flags
    if total <= AUTO_APPROVE_LIMIT and not flags:
        decision = ApprovalDecision(
            status="approved",
            reasoning=f"Auto-approved: ${total:.2f} under ${AUTO_APPROVE_LIMIT} threshold, no flags",
            risk_score=0.1
        )
        return {
            "approval": decision.model_dump(),
            "logs": [f"APPROVED {inv_num}: ${total:.2f}, auto-approved"]
        }

    # LLM review: ambiguous cases need VP reasoning + critic reflection
    llm = LLMClient()

    flag_summary = "\n".join(
        f"- [{f['severity']}] {f['message']}" for f in flags
    ) if flags else "No flags."

    vp_prompt = f"""You are a VP of Finance reviewing an invoice for approval.

Invoice: {inv_num}
Vendor: {invoice.get('vendor')}
Total: ${total:.2f}
Currency: {invoice.get('currency', 'USD')}
Line Items: {json.dumps(invoice.get('line_items', []), indent=2)}

Validation Flags:
{flag_summary}

Based on the above, should this invoice be approved, rejected, or escalated for human review?
Respond in JSON with: status (approved/rejected/escalated), reasoning (string), risk_score (0.0 to 1.0)"""

    try:
        # First pass: VP reasoning
        first_response = llm.call(vp_prompt, "Review this invoice.", json_mode=True)

        if not first_response:
            decision = ApprovalDecision(
                status="escalated",
                reasoning="LLM unavailable, escalating for human review",
                risk_score=0.5,
                requires_human_review=True
            )
            return {
                "approval": decision.model_dump(),
                "logs": [f"ESCALATED {inv_num}: LLM unavailable"]
            }

        first_data = json.loads(first_response)

        # Second pass: Critic reviews the VP's decision
        critic_prompt = f"""You are a financial auditor reviewing a VP's approval decision.

The VP reviewed invoice {inv_num} (${total:.2f} from {invoice.get('vendor')}) and decided:
{first_response}

Play devil's advocate:
1. Did they weigh the validation flags appropriately?
2. Are there fraud patterns they missed?
3. Is the risk score appropriate for this amount?
4. Would you stake your job on this decision?

If the decision should change, say so.
Respond in JSON with: should_change (boolean), revised_status (approved/rejected/escalated), critique (string)"""

        critic_response = llm.call(critic_prompt, "Critique this decision.", json_mode=True)
        critic_data = json.loads(critic_response) if critic_response else {}

        # Final decision: use critic's revision if they flagged a change
        if critic_data.get("should_change"):
            final_status = critic_data.get("revised_status", "escalated")
            reflection = critic_data.get("critique", "")
        else:
            final_status = first_data.get("status", "escalated")
            reflection = critic_data.get("critique", "No changes recommended.")

        decision = ApprovalDecision(
            status=final_status,
            reasoning=first_data.get("reasoning", ""),
            risk_score=min(1.0, max(0.0, first_data.get("risk_score", 0.5))),
            reflection=reflection,
            requires_human_review=(final_status == "escalated")
        )

        return {
            "approval": decision.model_dump(),
            "logs": [
                f"VP initial decision for {inv_num}: {first_data.get('status')}",
                f"Critic reflection: {'CHANGED to ' + final_status if critic_data.get('should_change') else 'Agreed'}",
                f"FINAL: {final_status.upper()} {inv_num} (risk: {decision.risk_score})"
            ],
            "token_usage": llm.token_usage
        }

    except Exception as e:
        decision = ApprovalDecision(
            status="escalated",
            reasoning=f"Error during approval: {str(e)}",
            risk_score=0.5,
            requires_human_review=True
        )
        return {
            "approval": decision.model_dump(),
            "logs": [f"ERROR approving {inv_num}: {str(e)}, escalating"]
        }