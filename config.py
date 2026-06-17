# Approval thresholds
AUTO_APPROVE_LIMIT = 10000.0
HIGH_VALUE_THRESHOLD = 50000.0

# LLM settings 
LLM_MODEL = "gpt-4o-mini"
LLM_MAX_RETRIES = 2

# Fraud detection keywords 
FRAUD_KEYWORDS = [
    "urgent", "immediately", "wire transfer", "penalty",
    "asap", "rush payment", "do not delay"
]

#  Confidence thresholds
CONFIDENCE_THRESHOLD = 0.7

#  Database 
DB_PATH = "inventory.db"

#  Pricing tolerance 
PRICE_TOLERANCE = 0.20