"""
Export a session to the import CSV format expected by the accounting system.

The format is fixed and must match what the importer reads exactly:
    * comma-delimited, CRLF line endings, no BOM
    * encoded as Mac OS Central European (mac_latin2)
    * header: termeknev, ar, afakod, mennyiseg, egyseg
    * afakod is always "27" and egyseg is always "db"
"""
import csv

EXPORT_ENCODING = "mac_latin2"
HEADER = ["termeknev", "ar", "afakod", "mennyiseg", "egyseg"]
AFA_CODE = "27"
UNIT = "db"


def write_export(path: str, rows) -> None:
    """Write *rows* (iterable of (name, price, quantity)) to *path*.

    csv.writer already uses a comma delimiter and a '\\r\\n' line terminator,
    matching the importer's expected format.
    """
    with open(path, "w", newline="", encoding=EXPORT_ENCODING, errors="replace") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for name, price, quantity in rows:
            writer.writerow([name, price, AFA_CODE, quantity, UNIT])
