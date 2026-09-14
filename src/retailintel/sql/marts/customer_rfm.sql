create or replace view mart_customer_rfm as
with max_date as (
    select max(order_date) as max_order_date
    from fact_order
),
customer_metrics as (
    select
        o.customer_id,
        max(o.order_date) as last_order_date,
        count(distinct o.order_id) as orders,
        sum(l.quantity - l.returned_qty) as net_units,
        sum((l.quantity - l.returned_qty) * l.unit_price_minor) as net_sales_minor,
        sum((l.quantity - l.returned_qty) * (l.unit_price_minor - l.unit_cost_minor))
            as gross_margin_minor
    from fact_order o
    join fact_order_line l using (order_id)
    group by 1
),
scored as (
    select
        m.*,
        date_diff('day', m.last_order_date, d.max_order_date) as recency_days,
        6 - ntile(5) over (
            order by date_diff('day', m.last_order_date, d.max_order_date) asc
        ) as recency_score,
        ntile(5) over (order by m.orders asc) as frequency_score,
        ntile(5) over (order by m.net_sales_minor asc) as monetary_score
    from customer_metrics m
    cross join max_date d
)
select
    *,
    case
        when recency_score >= 4 and frequency_score >= 4 and monetary_score >= 4
            then 'champions'
        when recency_score <= 2 and frequency_score >= 3 then 'at_risk'
        when frequency_score >= 4 then 'loyal'
        when monetary_score >= 4 then 'big_spenders'
        when recency_score >= 4 and frequency_score <= 2 then 'new_or_promising'
        else 'standard'
    end as customer_segment
from scored;
