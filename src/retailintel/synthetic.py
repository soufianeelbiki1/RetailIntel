from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from random import Random


@dataclass(frozen=True)
class SyntheticRetailDataset:
    suppliers: list[tuple[str, str, int]]
    products: list[tuple[str, str, str, str, int, int]]
    orders: list[tuple[str, date, str, str | None]]
    order_lines: list[tuple[str, int, str, int, int, int, int]]
    inventory_snapshots: list[tuple[date, str, int, int, int, int]]
    purchase_orders: list[tuple[str, str, str, date, date, date | None, int]]


def generate_retail_dataset(seed: int = 20260831, order_count: int = 600) -> SyntheticRetailDataset:
    """Generate deterministic synthetic retail operations with no real customer data."""

    if order_count <= 0:
        raise ValueError("order_count must be positive")

    rng = Random(seed)
    suppliers = [
        ("sup-north", "North Supply Co", 5),
        ("sup-atlas", "Atlas Wholesale", 9),
        ("sup-coast", "Coast Distribution", 14),
        ("sup-euro", "Euro Import Partner", 21),
    ]
    categories = ["apparel", "footwear", "accessories", "home"]

    products: list[tuple[str, str, str, str, int, int]] = []
    for index in range(20):
        product_id = f"sku-{index + 1:03d}"
        supplier_id = suppliers[index % len(suppliers)][0]
        unit_cost = rng.randint(1_200, 8_000)
        markup = rng.uniform(1.35, 2.2)
        list_price = int(unit_cost * markup)
        products.append(
            (
                product_id,
                f"Synthetic Product {index + 1}",
                categories[index % len(categories)],
                supplier_id,
                unit_cost,
                list_price,
            )
        )

    product_lookup = {product[0]: product for product in products}
    product_ids = list(product_lookup)
    start = date(2026, 7, 1)
    orders: list[tuple[str, date, str, str | None]] = []
    order_lines: list[tuple[str, int, str, int, int, int, int]] = []

    for order_index in range(order_count):
        order_id = f"ord-{order_index + 1:05d}"
        order_date = start + timedelta(days=order_index % 30)
        customer_id = f"cus-{rng.randint(1, 240):04d}"
        promotion_code = rng.choices(
            [None, "WELCOME10", "SUMMER15"],
            weights=[0.72, 0.16, 0.12],
            k=1,
        )[0]
        orders.append((order_id, order_date, customer_id, promotion_code))

        line_count = rng.randint(1, 3)
        for line_no, product_id in enumerate(rng.sample(product_ids, line_count), start=1):
            product = product_lookup[product_id]
            quantity = rng.randint(1, 4)
            discount = 0.0
            if promotion_code == "WELCOME10":
                discount = 0.10
            elif promotion_code == "SUMMER15":
                discount = 0.15
            unit_price = max(1, int(product[5] * (1 - discount)))
            returned_qty = 1 if quantity > 1 and rng.random() < 0.08 else 0
            order_lines.append(
                (
                    order_id,
                    line_no,
                    product_id,
                    quantity,
                    returned_qty,
                    unit_price,
                    product[4],
                )
            )

    inventory_snapshots: list[tuple[date, str, int, int, int, int]] = []
    purchase_orders: list[tuple[str, str, str, date, date, date | None, int]] = []
    purchase_order_sequence = 0
    for product in products:
        product_id = product[0]
        supplier_id = product[3]
        lead_time = next(supplier[2] for supplier in suppliers if supplier[0] == supplier_id)
        on_hand = rng.randint(55, 140)
        for day_offset in range(30):
            snapshot_date = start + timedelta(days=day_offset)
            reorder_point = 45 + (product_ids.index(product_id) % 4) * 8
            safety_stock = max(15, reorder_point // 2)
            daily_demand = rng.randint(0, 9)
            on_hand = max(0, on_hand - daily_demand)
            on_order = 0
            if on_hand < reorder_point and day_offset % 5 == 0:
                on_order = rng.randint(45, 90)
                purchase_order_sequence += 1
                expected = snapshot_date + timedelta(days=lead_time)
                received = expected + timedelta(days=rng.choice([-1, 0, 0, 1, 3]))
                purchase_orders.append(
                    (
                        f"po-{purchase_order_sequence:04d}",
                        supplier_id,
                        product_id,
                        snapshot_date,
                        expected,
                        received,
                        on_order,
                    )
                )
            inventory_snapshots.append(
                (snapshot_date, product_id, on_hand, on_order, reorder_point, safety_stock)
            )

    return SyntheticRetailDataset(
        suppliers=suppliers,
        products=products,
        orders=orders,
        order_lines=order_lines,
        inventory_snapshots=inventory_snapshots,
        purchase_orders=purchase_orders,
    )
