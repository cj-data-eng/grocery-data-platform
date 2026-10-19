"""Data models shared across the package."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BasketLine:
    """One product line within a shopping basket.

    Money is stored as integer pence to avoid floating point rounding errors.
    """

    basket_id: str
    store_id: str
    customer_id: str
    purchased_at: datetime
    product_id: str
    product_name: str
    category: str
    quantity: int
    unit_price_pence: int
