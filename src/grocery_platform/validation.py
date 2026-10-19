"""Row-level validation. Bad rows are set aside rather than silently dropped."""

from collections.abc import Iterable
from dataclasses import dataclass

from grocery_platform.models import BasketLine


@dataclass(frozen=True)
class RejectedLine:
    """A line that failed validation, with the reasons why."""

    line: BasketLine
    reasons: tuple[str, ...]


def check_line(line: BasketLine) -> tuple[str, ...]:
    """Return the reasons a line is invalid (an empty tuple means it is valid)."""
    reasons: list[str] = []
    if not line.basket_id:
        reasons.append("basket_id is empty")
    if not line.store_id:
        reasons.append("store_id is empty")
    if not line.product_id:
        reasons.append("product_id is empty")
    if line.quantity <= 0:
        reasons.append("quantity must be positive")
    if line.unit_price_pence <= 0:
        reasons.append("unit_price_pence must be positive")
    if line.purchased_at.tzinfo is None:
        reasons.append("purchased_at must be timezone-aware")
    return tuple(reasons)


def split_valid(lines: Iterable[BasketLine]) -> tuple[list[BasketLine], list[RejectedLine]]:
    """Split lines into (valid lines, rejected lines)."""
    valid: list[BasketLine] = []
    rejected: list[RejectedLine] = []
    for line in lines:
        reasons = check_line(line)
        if reasons:
            rejected.append(RejectedLine(line=line, reasons=reasons))
        else:
            valid.append(line)
    return valid, rejected
