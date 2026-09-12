create or replace view mart_supplier_reliability as
select
    po.supplier_id,
    s.supplier_name,
    s.lead_time_days as contracted_lead_time_days,
    count(*) as purchase_orders,
    avg(date_diff('day', po.ordered_date, po.received_date)) filter (where po.received_date is not null) as actual_lead_time_days,
    avg(
        case
            when po.received_date is null then null
            when po.received_date <= po.expected_date then 1.0
            else 0.0
        end
    ) as on_time_delivery_rate,
    avg(
        case
            when po.received_date is null then null
            else greatest(date_diff('day', po.expected_date, po.received_date), 0)
        end
    ) as average_late_days,
    sum(po.quantity) as units_ordered
from fact_purchase_order po
join dim_supplier s using (supplier_id)
group by 1, 2, 3;
