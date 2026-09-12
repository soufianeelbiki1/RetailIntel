create table dim_supplier (
    supplier_id varchar primary key,
    supplier_name varchar not null,
    lead_time_days integer not null check (lead_time_days > 0)
);

create table dim_product (
    product_id varchar primary key,
    product_name varchar not null,
    category varchar not null,
    supplier_id varchar not null references dim_supplier(supplier_id),
    unit_cost_minor bigint not null check (unit_cost_minor > 0),
    list_price_minor bigint not null check (list_price_minor > unit_cost_minor)
);

create table fact_order (
    order_id varchar primary key,
    order_date date not null,
    customer_id varchar not null,
    promotion_code varchar
);

create table fact_order_line (
    order_id varchar not null references fact_order(order_id),
    line_no integer not null check (line_no > 0),
    product_id varchar not null references dim_product(product_id),
    quantity integer not null check (quantity > 0),
    returned_qty integer not null check (returned_qty >= 0 and returned_qty <= quantity),
    unit_price_minor bigint not null check (unit_price_minor > 0),
    unit_cost_minor bigint not null check (unit_cost_minor > 0),
    primary key (order_id, line_no)
);

create table fact_inventory_snapshot (
    snapshot_date date not null,
    product_id varchar not null references dim_product(product_id),
    on_hand_qty integer not null check (on_hand_qty >= 0),
    on_order_qty integer not null check (on_order_qty >= 0),
    reorder_point_qty integer not null check (reorder_point_qty >= 0),
    safety_stock_qty integer not null check (safety_stock_qty >= 0),
    primary key (snapshot_date, product_id)
);

create table fact_purchase_order (
    purchase_order_id varchar primary key,
    supplier_id varchar not null references dim_supplier(supplier_id),
    product_id varchar not null references dim_product(product_id),
    ordered_date date not null,
    expected_date date not null,
    received_date date,
    quantity integer not null check (quantity > 0),
    check (expected_date >= ordered_date),
    check (received_date is null or received_date >= ordered_date)
);
