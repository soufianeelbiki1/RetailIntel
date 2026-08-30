from __future__ import annotations

from retailintel import build_warehouse


def test_rfm_has_one_row_per_customer_and_bounded_scores() -> None:
    connection = build_warehouse()

    customers = connection.execute("select count(distinct customer_id) from fact_order").fetchone()[
        0
    ]
    rfm_rows = connection.execute("select count(*) from mart_customer_rfm").fetchone()[0]
    invalid_scores = connection.execute(
        """
        select count(*)
        from mart_customer_rfm
        where recency_days < 0
           or recency_score not between 1 and 5
           or frequency_score not between 1 and 5
           or monetary_score not between 1 and 5
        """
    ).fetchone()[0]
    invalid_segments = connection.execute(
        """
        select count(*)
        from mart_customer_rfm
        where customer_segment not in (
            'champions', 'at_risk', 'loyal', 'big_spenders', 'new_or_promising', 'standard'
        )
        """
    ).fetchone()[0]

    assert rfm_rows == customers
    assert invalid_scores == 0
    assert invalid_segments == 0


def test_cohort_retention_is_bounded_and_age_zero_contains_entire_cohort() -> None:
    connection = build_warehouse()

    invalid = connection.execute(
        """
        select count(*)
        from mart_customer_cohort
        where cohort_age_months < 0
           or retention_rate < 0
           or retention_rate > 1
        """
    ).fetchone()[0]
    incomplete_age_zero = connection.execute(
        """
        select count(*)
        from mart_customer_cohort
        where cohort_age_months = 0
          and active_customers <> cohort_customers
        """
    ).fetchone()[0]

    assert invalid == 0
    assert incomplete_age_zero == 0


def test_promotion_mart_reconciles_to_order_line_economics() -> None:
    connection = build_warehouse()

    atomic_net_sales = connection.execute(
        "select sum((quantity - returned_qty) * unit_price_minor) from fact_order_line"
    ).fetchone()[0]
    mart_net_sales = connection.execute(
        "select sum(net_sales_minor) from mart_promotion_margin"
    ).fetchone()[0]
    invalid_margin = connection.execute(
        """
        select count(*)
        from mart_promotion_margin
        where net_sales_minor - cogs_minor <> gross_margin_minor
           or gross_margin_rate < 0
           or gross_margin_rate > 1
           or unit_return_rate < 0
           or unit_return_rate > 1
        """
    ).fetchone()[0]

    assert mart_net_sales == atomic_net_sales
    assert invalid_margin == 0


def test_promotion_mart_does_not_publish_a_causal_lift_metric() -> None:
    connection = build_warehouse()

    column_names = {
        row[1]
        for row in connection.execute("pragma table_info('mart_promotion_margin')").fetchall()
    }

    assert all("lift" not in column_name.lower() for column_name in column_names)
    assert all("causal" not in column_name.lower() for column_name in column_names)
