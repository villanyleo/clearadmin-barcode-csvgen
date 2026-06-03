"""
Munkamenet exportálása a számlázó szoftver által várt import CSV formátumba.

A formátum kötött, és pontosan meg kell egyeznie azzal, amit az importáló beolvas:
    * vesszővel tagolt, CRLF sorvégek, BOM nélkül
    * Mac OS közép-európai (mac_latin2) kódolás
    * fejléc: termeknev, ar, afakod, mennyiseg, egyseg
    * az afakod mindig "27", az egyseg mindig "db"
"""
import csv

EXPORT_ENCODING = "mac_latin2"
HEADER = ["termeknev", "ar", "afakod", "mennyiseg", "egyseg"]
AFA_CODE = "27"
UNIT = "db"


def write_export(path: str, rows) -> None:
    """A *rows* sorokat (name, price, quantity hármasok) a *path* fájlba írja.

    A csv.writer alapból vesszős elválasztót és '\\r\\n' sorvéget használ, ami
    megfelel az importáló által várt formátumnak.
    """
    with open(path, "w", newline="", encoding=EXPORT_ENCODING, errors="replace") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for name, price, quantity in rows:
            writer.writerow([name, price, AFA_CODE, quantity, UNIT])
