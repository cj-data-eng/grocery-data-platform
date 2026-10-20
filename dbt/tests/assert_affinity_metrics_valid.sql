-- Support and confidence are proportions, and lift must be positive. Any row returned is a failure.
select *
from {{ ref('product_affinity') }}
where support <= 0 or support > 1
   or confidence_a_to_b <= 0 or confidence_a_to_b > 1
   or lift <= 0