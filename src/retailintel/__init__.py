"""RetailIntel decision-intelligence package."""

from .synthetic import SyntheticRetailDataset, generate_retail_dataset
from .warehouse import build_warehouse

__all__ = ["SyntheticRetailDataset", "build_warehouse", "generate_retail_dataset"]
