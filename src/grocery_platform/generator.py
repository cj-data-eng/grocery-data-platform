"""Deterministic synthetic grocery basket generator."""

import random
from collections.abc import Iterator
from datetime import UTC, date, datetime, time

from faker import Faker

from grocery_platform.models import BasketLine

# (product_id, name, category, base price in pence)
CATALOGUE: tuple[tuple[str, str, str, int], ...] = (
    ("P001", "Whole Milk 2L", "dairy", 155),
    ("P002", "Semi-Skimmed Milk 2L", "dairy", 150),
    ("P003", "Salted Butter 250g", "dairy", 210),
    ("P004", "Mature Cheddar 400g", "dairy", 420),
    ("P005", "Greek Yoghurt 500g", "dairy", 180),
    ("P006", "Free Range Eggs 12pk", "dairy", 290),
    ("P007", "White Bread 800g", "bakery", 115),
    ("P008", "Wholemeal Bread 800g", "bakery", 125),
    ("P009", "Croissants 4pk", "bakery", 160),
    ("P010", "Bananas 5pk", "produce", 90),
    ("P011", "Gala Apples 6pk", "produce", 200),
    ("P012", "Baby Spinach 200g", "produce", 150),
    ("P013", "Carrots 1kg", "produce", 70),
    ("P014", "Potatoes 2.5kg", "produce", 180),
    ("P015", "Tomatoes 6pk", "produce", 160),
    ("P016", "Chicken Breast 650g", "meat", 420),
    ("P017", "Beef Mince 500g", "meat", 330),
    ("P018", "Pork Sausages 8pk", "meat", 250),
    ("P019", "Penne Pasta 500g", "pantry", 100),
    ("P020", "Basmati Rice 1kg", "pantry", 210),
    ("P021", "Chopped Tomatoes 400g", "pantry", 65),
    ("P022", "Baked Beans 4pk", "pantry", 190),
    ("P023", "Orange Juice 1L", "drinks", 160),
    ("P024", "Sparkling Water 6pk", "drinks", 200),
    ("P025", "Tea Bags 80pk", "drinks", 180),
    ("P026", "Instant Coffee 100g", "drinks", 320),
)

# Shopping hours 08:00-21:59, weighted towards lunchtime and after work.
SHOPPING_HOURS: tuple[int, ...] = tuple(range(8, 22))
HOUR_WEIGHTS: tuple[int, ...] = (3, 4, 6, 8, 6, 4, 4, 5, 8, 10, 9, 6, 3, 2)

PROMO_CHANCE = 0.10
PROMO_PERCENT_OF_PRICE = 80


def generate_baskets(
    day: date,
    n_baskets: int,
    seed: int = 42,
    n_stores: int = 10,
    n_customers: int = 500,
) -> Iterator[BasketLine]:
    """Yield the basket lines for ``n_baskets`` baskets on ``day``.

    The output depends only on the arguments, so the same inputs always produce
    identical data. That makes tests and re-runs reproducible.
    """
    if n_baskets < 0:
        raise ValueError("n_baskets must not be negative")
    if n_stores < 1 or n_customers < 1:
        raise ValueError("n_stores and n_customers must be at least 1")

    run_seed = seed * 100_000_000 + day.toordinal()
    rng = random.Random(run_seed)
    fake = Faker("en_GB")
    fake.seed_instance(run_seed)

    for _ in range(n_baskets):
        basket_id = str(fake.uuid4())
        store_id = f"S{rng.randint(1, n_stores):03d}"
        customer_id = f"C{rng.randint(1, n_customers):05d}"
        hour = rng.choices(SHOPPING_HOURS, weights=HOUR_WEIGHTS)[0]
        purchased_at = datetime.combine(
            day, time(hour, rng.randint(0, 59), rng.randint(0, 59)), tzinfo=UTC
        )

        for product_id, name, category, base_price in rng.sample(CATALOGUE, rng.randint(1, 12)):
            on_promo = rng.random() < PROMO_CHANCE
            price = base_price * PROMO_PERCENT_OF_PRICE // 100 if on_promo else base_price
            yield BasketLine(
                basket_id=basket_id,
                store_id=store_id,
                customer_id=customer_id,
                purchased_at=purchased_at,
                product_id=product_id,
                product_name=name,
                category=category,
                quantity=rng.choices((1, 2, 3, 4), weights=(70, 20, 7, 3))[0],
                unit_price_pence=price,
            )