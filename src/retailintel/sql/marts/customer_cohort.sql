create or replace view mart_customer_cohort as
with first_order as (
    select
        customer_id,
        date_trunc('month', min(order_date)) as cohort_month
    from fact_order
    group by 1
),
cohort_size as (
    select
        cohort_month,
        count(*) as cohort_customers
    from first_order
    group by 1
),
customer_month as (
    select
        o.customer_id,
        f.cohort_month,
        date_trunc('month', o.order_date) as activity_month,
        count(distinct o.order_id) as orders,
        sum((l.quantity - l.returned_qty) * l.unit_price_minor) as net_sales_minor,
        sum((l.quantity - l.returned_qty) * (l.unit_price_minor - l.unit_cost_minor))
            as gross_margin_minor
    from fact_order o
    join first_order f using (customer_id)
    join fact_order_line l using (order_id)
    group by 1, 2, 3
)
select
    c.cohort_month,
    c.activity_month,
    date_diff('month', c.cohort_month, c.activity_month) as cohort_age_months,
    s.cohort_customers,
    count(distinct c.customer_id) as active_customers,
    count(distinct c.customer_id)::double / s.cohort_customers as retention_rate,
    sum(c.orders) as orders,
    sum(c.net_sales_minor) as net_sales_minor,
    sum(c.gross_margin_minor) as gross_margin_minor
from customer_month c
join cohort_size s using (cohort_month)
group by 1, 2, 3, 4;
