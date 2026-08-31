from retailintel import build_warehouse


def test_demand_spine_includes_zero_demand_days() -> None:
    connection = build_warehouse()

    zero_days = connection.execute(
        "select count(*) from mart_demand_daily where net_units = 0"
    ).fetchone()[0]
    product_count = connection.execute("select count(*) from dim_product").fetchone()[0]

    assert zero_days > 0
    assert product_count > 0


def test_trailing_forecast_uses_only_prior_days() -> None:
    connection = build_warehouse()

    rows = connection.execute(
        """
        select metric_date, product_id, net_units, forecast_7d_mean, forecast_history_days
        from mart_demand_daily
        where forecast_history_days = 7
        order by product_id, metric_date
        limit 25
        """
    ).fetchall()

    assert rows
    for metric_date, product_id, _, forecast, history_days in rows:
        prior_mean = connection.execute(
            """
            select avg(net_units)
            from mart_demand_daily
            where product_id = ?
              and metric_date between ? - interval 7 day and ? - interval 1 day
            """,
            [product_id, metric_date, metric_date],
        ).fetchone()[0]
        assert history_days == 7
        assert forecast == prior_mean


def test_replenishment_policy_exposes_service_level_assumption() -> None:
    connection = build_warehouse()

    rows = connection.execute(
        """
        select
            target_service_level,
            service_level_z,
            recommended_safety_stock_qty,
            recommended_reorder_point_qty,
            recommended_reorder_qty,
            inventory_position_qty
        from mart_replenishment_recommendation
        """
    ).fetchall()

    assert rows
    for service_level, z_score, safety_stock, reorder_point, reorder_qty, inventory_position in rows:
        assert service_level == 0.95
        assert z_score == 1.645
        assert safety_stock >= 0
        assert reorder_point >= safety_stock
        assert reorder_qty == max(reorder_point - inventory_position, 0)


def test_replenishment_recommendation_covers_every_product() -> None:
    connection = build_warehouse()

    products = connection.execute("select count(*) from dim_product").fetchone()[0]
    recommendations = connection.execute(
        "select count(*) from mart_replenishment_recommendation"
    ).fetchone()[0]

    assert recommendations == products


def test_forecast_error_is_non_negative() -> None:
    connection = build_warehouse()

    invalid = connection.execute(
        """
        select count(*)
        from mart_demand_daily
        where absolute_forecast_error < 0
        """
    ).fetchone()[0]

    assert invalid == 0
