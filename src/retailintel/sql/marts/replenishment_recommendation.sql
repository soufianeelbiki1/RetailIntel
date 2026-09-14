create or replace view mart_replenishment_recommendation as
with latest_snapshot as (
    select
        s.*,
        row_number() over (partition by product_id order by snapshot_date desc) as row_number
    from fact_inventory_snapshot s
),
latest_demand as (
    select
        d.*,
        row_number() over (
            partition by d.product_id order by d.metric_date desc
        ) as row_number
    from latest_snapshot s
    join mart_demand_daily d
      on d.product_id = s.product_id
     and d.metric_date <= s.snapshot_date
    where s.row_number = 1
),
inputs as (
    select
        s.snapshot_date,
        s.product_id,
        p.product_name,
        p.category,
        p.supplier_id,
        sup.supplier_name,
        sup.lead_time_days,
        s.on_hand_qty,
        s.on_order_qty,
        d.metric_date as policy_demand_date,
        d.forecast_7d_mean as policy_demand_mean_7d,
        d.forecast_history_days as policy_history_days,
        coalesce(d.demand_stddev_28d, 0) as demand_stddev_28d
    from latest_snapshot s
    join dim_product p using (product_id)
    join dim_supplier sup using (supplier_id)
    join latest_demand d using (product_id)
    where s.row_number = 1
      and d.row_number = 1
      and d.forecast_history_days = 7
),
policy as (
    select
        *,
        0.95::double as target_service_level,
        1.645::double as service_level_z,
        ceil(1.645 * demand_stddev_28d * sqrt(lead_time_days))::integer as recommended_safety_stock_qty,
        ceil(
            policy_demand_mean_7d * lead_time_days
            + 1.645 * demand_stddev_28d * sqrt(lead_time_days)
        )::integer as recommended_reorder_point_qty
    from inputs
)
select
    *,
    on_hand_qty + on_order_qty as inventory_position_qty,
    greatest(
        recommended_reorder_point_qty - (on_hand_qty + on_order_qty),
        0
    )::integer as recommended_reorder_qty,
    case
        when on_hand_qty = 0 then 'stockout'
        when on_hand_qty + on_order_qty < recommended_reorder_point_qty then 'reorder'
        when on_hand_qty < recommended_safety_stock_qty then 'watch'
        else 'healthy'
    end as recommended_action
from policy;
