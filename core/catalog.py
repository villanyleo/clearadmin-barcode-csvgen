"""
CSV-fájlból betöltött termékkatalógus.

Várt séma:
    1. oszlop = "ean"  — az EAN-13 vonalkód
    2. oszlop = "name" — a termék neve
    minden további, nem üres fejlécű oszlop egy elnevezett árlista
    (pl. Kisker, Nagyker, Export, stb.)

A fájl tartalmazhat UTF-8 BOM-ot és egy felesleges, üres záró oszlopot; mindkettőt
itt kezeljük. Ha ugyanaz az EAN több sorban szerepel, az első nyer.
"""
import csv
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Product:
    name: str
    prices: Dict[str, str]  # árlista neve -> ár, ahogy a CSV-ben szerepel


class Catalog:
    def __init__(self, price_names: List[str], products: Dict[str, Product]):
        self.price_names = price_names      # az árlisták neve, sorrendben
        self._products = products

    def get(self, ean: str) -> Optional[Product]:
        return self._products.get(ean)

    def __len__(self) -> int:
        return len(self._products)


def load_catalog(path: str) -> Catalog:
    """Beolvassa a *path* fájlt és Catalog-ot ad vissza. Hibát dob üres/olvashatatlan fájlnál."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("A CSV-fájl üres.")

        # Ároszlopok: minden az ean/name után, aminek nem üres a fejléce.
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
                continue  # az első előfordulás nyer
            name = row[1].strip() if len(row) > 1 else ""
            prices = {
                pname: (row[i].strip() if i < len(row) else "")
                for i, pname in price_cols
            }
            products[ean] = Product(name=name, prices=prices)

    return Catalog(price_names, products)
