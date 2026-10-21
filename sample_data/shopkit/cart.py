"""
Cart calculation utilities for shopkit.
"""
from typing import List, Dict

def cart_total(items: List[Dict[str, float]], discount_pct: float = 0.0) -> float:
    """
    Computes total price for a list of items with optional discount percentage.
    Each item is a dict with 'price' and 'quantity'.
    Returns total rounded to 2 decimal places.
    """
    subtotal = sum(item["price"] * item.get("quantity", 1) for item in items)
    if discount_pct > 0:
        discount = subtotal * (discount_pct / 100.0)
        subtotal -= discount
    return round(subtotal, 2)
