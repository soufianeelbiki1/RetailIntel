create or replace view mart_promotion_margin as
select
    coalesce(o.promotion_code, 'NO_PROMOTION') as promotion_code,
    p.category,
    count(distinct o.order_id) as orders,
    sum(l.quantity) as units_ordered,
    sum(l.returned_qty) as returned_units,
    sum(l.quantity - l.returned_qty) as net_units,
    sum(l.quantity * l.unit_price_minor) as gross_sales_minor,
    sum((l.quantity - l.returned_qty) * l.unit_price_minor) as net_sales_minor,
    sum((l.quantity - l.returned_qty) * l.unit_cost_minor) as cogs_minor,
    sum((l.quantity - l.returned_qty) * (l.unit_price_minor - l.unit_cost_minor))
        as gross_margin_minor,
    case
        when sum((l.quantity - l.returned_qty) * l.unit_price_minor) = 0 then null
        else
            sum((l.quantity - l.returned_qty) * (l.unit_price_minor - l.unit_cost_minor))::double
            / sum((l.quantity - l.returned_qty) * l.unit_price_minor)
    end as gross_margin_rate,
    case
        when sum(l.quantity) = 0 then null
        else sum(l.returned_qty)::double / sum(l.quantity)
    end as unit_return_rate,
    avg(l.unit_price_minor) as average_realized_unit_price_minor
from fact_order o
join fact_order_line l using (order_id)
join dim_product p using (product_id)
group by 1, 2;
