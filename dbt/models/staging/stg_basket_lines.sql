select
    basket_id,
    store_id,
    customer_id,
    purchased_at,
    cast(purchase_date as date) as purchase_date,
    product_id,
    product_name,
    category,
    quantity,
    unit_price_pence,
    quantity * unit_price_pence as line_total_pence
from {{ source('raw', 'basket_lines') }}