-- A product should appear at most once per basket. Any row returned is a failure.
select
    basket_id,
    product_id,
    count(*) as occurrences
from {{ ref('stg_basket_lines') }}
group by 1, 2
having count(*) > 1