create or replace view mart_product_daily as
select
    o.order_date as metric_date,
    l.product_id,
    p.product_name,
    p.category,
    p.supplier_id,
    sum(l.quantity) as units_ordered,
    sum(l.returned_qty) as returned_units,
    sum(l.quantity - l.returned_qty) as net_units,
    sum(l.quantity * l.unit_price_minor) as gross_sales_minor,
    sum((l.quantity - l.returned_qty) * l.unit_price_minor) as net_sales_minor,
    sum((l.quantity - l.returned_qty) * l.unit_cost_minor) as cogs_minor,
    sum((l.quantity - l.returned_qty) * (l.unit_price_minor - l.unit_cost_minor)) as gross_margin_minor,
    case
        when sum((l.quantity - l.returned_qty) * l.unit_price_minor) = 0 then null
        else
            sum((l.quantity - l.returned_qty) * (l.unit_price_minor - l.unit_cost_minor))::double
            / sum((l.quantity - l.returned_qty) * l.unit_price_minor)
    end as gross_margin_rate,
    count(distinct o.order_id) as orders
from fact_order_line l
join fact_order o using (order_id)
join dim_product p using (product_id)
group by 1, 2, 3, 4, 5;
