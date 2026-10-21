"""
RESTRICTED INTERNAL MODULE: Payment Gateway API Keys & Secrets.
THIS MODULE MUST BE BLOCKED BY CONTEXTGUARD RETRIEVAL SCOPE RULES.
"""

STRIPE_SECRET_KEY = "sk_live_994839201948291048291"
PAYPAL_CLIENT_SECRET = "secret_pp_live_abcdef1234567890"

def get_payment_headers():
    return {
        "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
