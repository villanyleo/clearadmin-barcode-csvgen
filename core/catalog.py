"""
Product catalog loaded from a CSV file.

Expected schema:
    column 1 = "ean"  — the EAN-13 barcode
    column 2 = "name" — the product name
    every further column with a non-empty header is a named price list
    (e.g. Kisker, Nagyker, VIP, Export)

The file may carry a UTF-8 BOM and a stray trailing empty column; both are
handled here. If the same EAN appears on several rows, the first one wins.
"""
import csv
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Product:
    name: str
    prices: Dict[str, str]  # price-list name -> price as it appears in the CSV


class Catalog:
    def __init__(self, price_names: List[str], products: Dict[str, Product]):
        self.price_names = price_names      # ordered list of price-list names
        self._products = products

    def get(self, ean: str) -> Optional[Product]:
        return self._products.get(ean)

    def __len__(self) -> int:
        return len(self._products)


def load_catalog(path: str) -> Catalog:
    """Read *path* and return a Catalog. Raises on unreadable/empty files."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("The CSV file is empty.")

        # Price columns: everything after ean/name that has a non-empty header.
        price_cols = [
            (i, name.strip())
            for i, name in enumerate(header[2:], start=2)
            if name.strip()
        ]
        price_names = [name for _, name in price_cols]

        products: Dict[str, Product] = {}
        for row in reader:
            if not row or not row[0].strip():
                continue
            ean = row[0].strip()
            if ean in products:
                continue  # first occurrence wins
            name = row[1].strip() if len(row) > 1 else ""
            prices = {
                pname: (row[i].strip() if i < len(row) else "")
                for i, pname in price_cols
            }
            products[ean] = Product(name=name, prices=prices)

    return Catalog(price_names, products)
