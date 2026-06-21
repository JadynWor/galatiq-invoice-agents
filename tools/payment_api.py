import uuid
from models.invoice import PaymentResult


def mock_payment(vendor, amount):
    """Simulate processing a payment."""
    # Generate a transaction ID
    transaction_id = str(uuid.uuid4())
    # Build a message like "Paid $5000.0 to Widgets Inc."
    message = f"Paid ${amount:.2f} to {vendor}"
    # Return a PaymentResult
    return PaymentResult(
        success=True,
        transaction_id=transaction_id,
        message=message
    )