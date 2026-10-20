with lines as (
    select distinct
        basket_id,
        product_id
    from {{ ref('stg_basket_lines') }}
),

total as (
    select count(distinct basket_id) as total_baskets
    from lines
),

product_counts as (
    select
        product_id,
        count(*) as baskets
    from lines
    group by 1
),

pairs as (
    select
        a.product_id as product_a,
        b.product_id as product_b,
        count(*) as baskets_together
    from lines as a
    inner join lines as b
        on a.basket_id = b.basket_id
        and a.product_id < b.product_id
    group by 1, 2
),

names as (
    select distinct
        product_id,
        product_name
    from {{ ref('stg_basket_lines') }}
)

select
    pairs.product_a,
    names_a.product_name as product_a_name,
    pairs.product_b,
    names_b.product_name as product_b_name,
    pairs.baskets_together,
    cast(1.0 * pairs.baskets_together / total.total_baskets as decimal(8, 5)) as support,
    cast(1.0 * pairs.baskets_together / counts_a.baskets as decimal(8, 5)) as confidence_a_to_b,
    cast(
        1.0 * pairs.baskets_together * total.total_baskets / (counts_a.baskets * counts_b.baskets)
        as decimal(8, 3)
    ) as lift
from pairs
cross join total
inner join product_counts as counts_a on pairs.product_a = counts_a.product_id
inner join product_counts as counts_b on pairs.product_b = counts_b.product_id
inner join names as names_a on pairs.product_a = names_a.product_id
inner join names as names_b on pairs.product_b = names_b.product_id