select
    purchase_date,
    store_id,
    category,
    count(distinct basket_id) as baskets,
    sum(quantity) as units_sold,
    cast(sum(line_total_pence) / 100.0 as decimal(14, 2)) as revenue_gbp
from {{ ref('stg_basket_lines') }}
group by 1, 2, 3