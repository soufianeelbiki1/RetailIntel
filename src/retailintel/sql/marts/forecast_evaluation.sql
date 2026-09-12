-- Score both baselines on the same SKU-day observations in the final seven
-- calendar days. Compute lag before filtering so holdout rows retain history.
create or replace view mart_forecast_evaluation as
with history as (
    select
        *,
        lag(net_units, 7) over (
            partition by product_id order by metric_date
        ) as forecast_seasonal_naive
    from mart_demand_daily
),
eligible as (
    select *
    from history
    where metric_date >= (select max(metric_date) from history) - interval 6 day
      and forecast_history_days = 7
      and forecast_seasonal_naive is not null
),
predictions as (
    select metric_date, product_id, category, net_units, 'trailing_mean_7d' as baseline,
        forecast_7d_mean as prediction
    from eligible
    union all
    select metric_date, product_id, category, net_units, 'seasonal_naive_7d' as baseline,
        forecast_seasonal_naive as prediction
    from eligible
)
select
    case when grouping(product_id) = 1 then 'category' else 'sku' end as evaluation_grain,
    category,
    product_id,
    baseline,
    min(metric_date) as holdout_start,
    max(metric_date) as holdout_end,
    count(*) as evaluated_sku_days,
    sum(net_units) as actual_units,
    avg(abs(prediction - net_units)) as mae_units,
    sum(abs(prediction - net_units)) / nullif(sum(net_units), 0) as wape,
    avg(prediction - net_units) as mean_error_units
from predictions
group by grouping sets (
    (category, product_id, baseline),
    (category, baseline)
);
