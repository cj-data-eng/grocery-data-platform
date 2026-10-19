from dataclasses import replace
from datetime import UTC, datetime

from grocery_platform.models import BasketLine
from grocery_platform.validation import check_line, split_valid

GOOD = BasketLine(
    basket_id="b1",
    store_id="S001",
    customer_id="C00001",
    purchased_at=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
    product_id="P001",
    product_name="Whole Milk 2L",
    category="dairy",
    quantity=1,
    unit_price_pence=155,
)


def test_good_line_has_no_problems() -> None:
    assert check_line(GOOD) == ()


def test_zero_quantity_is_invalid() -> None:
    assert check_line(replace(GOOD, quantity=0)) == ("quantity must be positive",)


def test_negative_price_is_invalid() -> None:
    assert check_line(replace(GOOD, unit_price_pence=-5)) == ("unit_price_pence must be positive",)


def test_empty_ids_are_invalid() -> None:
    reasons = check_line(replace(GOOD, basket_id="", store_id="", product_id=""))
    assert reasons == ("basket_id is empty", "store_id is empty", "product_id is empty")


def test_naive_timestamp_is_invalid() -> None:
    naive = replace(GOOD, purchased_at=datetime(2026, 10, 19, 12, 0))
    assert check_line(naive) == ("purchased_at must be timezone-aware",)


def test_split_valid_separates_good_and_bad() -> None:
    bad = replace(GOOD, quantity=0)
    valid, rejected = split_valid([GOOD, bad])
    assert valid == [GOOD]
    assert len(rejected) == 1
    assert rejected[0].line == bad
    assert rejected[0].reasons == ("quantity must be positive",)
