-- The mart must add up to the same total as the staging model. Any row returned is a failure.
with staged as (
    select sum(line_total_pence) as total_pence
    from {{ ref('stg_basket_lines') }}
),

marted as (
    select cast(sum(revenue_gbp) * 100 as bigint) as total_pence
    from {{ ref('daily_sales') }}
)

select
    staged.total_pence as staged_pence,
    marted.total_pence as mart_pence
from staged
cross join marted
where staged.total_pence <> marted.total_pence