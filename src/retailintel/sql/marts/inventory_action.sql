create or replace view mart_inventory_action as
with latest as (
    select
        s.*,
        row_number() over (partition by product_id order by snapshot_date desc) as row_number
    from fact_inventory_snapshot s
)
select
    l.snapshot_date,
    l.product_id,
    p.product_name,
    p.category,
    p.supplier_id,
    sup.supplier_name,
    sup.lead_time_days,
    l.on_hand_qty,
    l.on_order_qty,
    l.reorder_point_qty,
    l.safety_stock_qty,
    greatest(l.reorder_point_qty - (l.on_hand_qty + l.on_order_qty), 0) as reorder_gap_qty,
    case
        when l.on_hand_qty = 0 then 'stockout'
        when l.on_hand_qty + l.on_order_qty < l.reorder_point_qty then 'reorder'
        when l.on_hand_qty < l.safety_stock_qty then 'watch'
        else 'healthy'
    end as inventory_action
from latest l
join dim_product p using (product_id)
join dim_supplier sup using (supplier_id)
where l.row_number = 1;
