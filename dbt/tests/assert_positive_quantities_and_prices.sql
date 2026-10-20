-- Quantities and prices must be positive. Any row returned is a failure.
select *
from {{ ref('stg_basket_lines') }}
where quantity <= 0
   or unit_price_pence <= 0