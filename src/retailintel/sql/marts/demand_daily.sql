create or replace view mart_demand_daily as
with bounds as (
    select min(order_date) as min_date, max(order_date) as max_date
    from fact_order
),
dates as (
    select cast(generate_series as date) as metric_date
    from bounds,
    generate_series(min_date, max_date, interval 1 day)
),
product_date_spine as (
    select d.metric_date, p.product_id, p.product_name, p.category, p.supplier_id
    from dates d
    cross join dim_product p
),
daily_demand as (
    select
        o.order_date as metric_date,
        l.product_id,
        sum(l.quantity - l.returned_qty) as net_units
    from fact_order_line l
    join fact_order o using (order_id)
    group by 1, 2
),
series as (
    select
        s.metric_date,
        s.product_id,
        s.product_name,
        s.category,
        s.supplier_id,
        coalesce(d.net_units, 0) as net_units
    from product_date_spine s
    left join daily_demand d using (metric_date, product_id)
)
select
    *,
    avg(net_units) over (
        partition by product_id
        order by metric_date
        rows between 7 preceding and 1 preceding
    ) as forecast_7d_mean,
    stddev_samp(net_units) over (
        partition by product_id
        order by metric_date
        rows between 28 preceding and 1 preceding
    ) as demand_stddev_28d,
    count(*) over (
        partition by product_id
        order by metric_date
        rows between 7 preceding and 1 preceding
    ) as forecast_history_days,
    abs(
        net_units
        - avg(net_units) over (
            partition by product_id
            order by metric_date
            rows between 7 preceding and 1 preceding
        )
    ) as absolute_forecast_error
from series;
