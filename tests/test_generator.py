from datetime import UTC, date

import pytest

from grocery_platform.generator import AFFINITIES, CATALOGUE, generate_baskets
from grocery_platform.validation import split_valid

DAY = date(2026, 10, 19)


def test_same_inputs_give_identical_output() -> None:
    first = list(generate_baskets(DAY, 50, seed=1))
    second = list(generate_baskets(DAY, 50, seed=1))
    assert first == second


def test_different_seeds_give_different_output() -> None:
    assert list(generate_baskets(DAY, 50, seed=1)) != list(generate_baskets(DAY, 50, seed=2))


def test_different_days_give_different_output() -> None:
    other_day = date(2026, 10, 20)
    assert list(generate_baskets(DAY, 20)) != list(generate_baskets(other_day, 20))


def test_basket_count_and_lines_per_basket() -> None:
    lines = list(generate_baskets(DAY, 100))
    per_basket: dict[str, int] = {}
    for line in lines:
        per_basket[line.basket_id] = per_basket.get(line.basket_id, 0) + 1
    assert len(per_basket) == 100
    assert all(1 <= count <= 12 for count in per_basket.values())


def test_no_duplicate_products_within_a_basket() -> None:
    lines = list(generate_baskets(DAY, 100))
    seen = {(line.basket_id, line.product_id) for line in lines}
    assert len(seen) == len(lines)


def test_all_generated_lines_are_valid() -> None:
    valid, rejected = split_valid(generate_baskets(DAY, 200))
    assert valid
    assert rejected == []


def test_timestamps_are_on_the_requested_day_in_shopping_hours() -> None:
    for line in generate_baskets(DAY, 100):
        assert line.purchased_at.tzinfo == UTC
        assert line.purchased_at.date() == DAY
        assert 8 <= line.purchased_at.hour <= 21


def test_prices_never_exceed_catalogue_base_price() -> None:
    base = {product_id: price for product_id, _, _, price in CATALOGUE}
    for line in generate_baskets(DAY, 100):
        assert 0 < line.unit_price_pence <= base[line.product_id]


def test_zero_baskets_gives_no_lines() -> None:
    assert list(generate_baskets(DAY, 0)) == []


def test_negative_baskets_rejected() -> None:
    with pytest.raises(ValueError, match="n_baskets"):
        list(generate_baskets(DAY, -1))


def test_invalid_store_or_customer_counts_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        list(generate_baskets(DAY, 1, n_stores=0))


def test_companion_products_are_bought_together_more_than_chance() -> None:
    baskets: dict[str, set[str]] = {}
    for line in generate_baskets(DAY, 2000):
        baskets.setdefault(line.basket_id, set()).add(line.product_id)

    for anchor, companion, probability in AFFINITIES:
        with_anchor = [items for items in baskets.values() if anchor in items]
        share = sum(companion in items for items in with_anchor) / len(with_anchor)
        base_rate = sum(companion in items for items in baskets.values()) / len(baskets)
        assert share > base_rate, (anchor, companion, probability)
        assert share > 0.3
