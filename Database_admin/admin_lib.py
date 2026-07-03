"""Shared helpers for Database_admin scripts."""

from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ADMIN_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ADMIN_ROOT / "config" / ".env"
DATA_DIR = ADMIN_ROOT / "data"


def load_config() -> Dict[str, str]:
    config: Dict[str, str] = {}
    if not CONFIG_PATH.exists():
        return config
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config


def db_path() -> Path:
    config = load_config()
    raw = config.get("DB_PATH", "../db/Anumani.db")
    return (ADMIN_ROOT / raw).resolve()


def products_csv_path() -> Path:
    config = load_config()
    raw = config.get("CSV_FILE_PATH", "data/products.csv")
    return (ADMIN_ROOT / raw).resolve()


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def title_words(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return " ".join(part[:1].upper() + part[1:].lower() for part in text.split(" "))


def normalize_unit(value: object) -> str:
    text = clean_text(value)
    if not text:
        return "Each"
    key = text.lower()
    if key in {"kg", "kgs", "kilo", "kilos", "kilogram", "kilograms"}:
        return "Kg"
    if key in {"each", "ea", "unit", "piece", "pieces", "count", "item", "items"}:
        return "Each"
    return title_words(text)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, fieldnames: Iterable[str], rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(fieldnames)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in names})


def print_header(title: str) -> None:
    print("=" * 70)
    print(title)
    print("=" * 70)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None
