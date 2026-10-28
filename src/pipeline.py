"""Consolidate CRM, Excel and JSON sources into one SQLite warehouse (star schema),
validate data quality and write a quality report."""
import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, REPORTS = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "reports"
DB_PATH = OUT / "warehouse.db"

SALES_COLUMN_MAP = {  # standardise differing regional layouts
    "Order No": "order_id", "Cust ID": "customer_id", "Product Code": "sku", "Qty": "quantity",
    "Price": "unit_price", "Discount %": "discount_pct", "Date": "order_date", "Region": "region",
}
COUNTRY_MAP = {"nepal": "Nepal", "np": "Nepal", "india": "India", "in": "India",
               "uae": "UAE", "united arab emirates": "UAE"}


# ---------- Extract ----------
def extract():
    crm = pd.read_csv(RAW / "crm_contacts.csv", dtype=str)
    sales = []
    for f in sorted(RAW.glob("sales_*.xlsx")):
        df = pd.read_excel(f).rename(columns=SALES_COLUMN_MAP)
        df["source_file"] = f.name
        sales.append(df)
    products = pd.DataFrame(json.loads((RAW / "product_catalogue.json").read_text())["products"])
    return crm, pd.concat(sales, ignore_index=True), products


# ---------- Transform ----------
def parse_mixed_dates(series: pd.Series) -> pd.Series:
    out = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    for fmt in ("%d/%m/%Y", "%b %d, %Y"):
        out = out.fillna(pd.to_datetime(series, format=fmt, errors="coerce"))
    return out


def clean_customers(crm: pd.DataFrame):
    df = crm.copy()
    df.columns = ["customer_id", "full_name", "email", "country", "segment", "signup_date"]
    df["full_name"] = df["full_name"].str.strip()
    df["email"] = df["email"].str.lower().str.strip()
    df["country"] = df["country"].str.strip().str.lower().map(COUNTRY_MAP).fillna("Unknown")
    df["signup_date"] = parse_mixed_dates(df["signup_date"])
    before = len(df)
    df = df.drop_duplicates(subset="customer_id", keep="first")
    return df, {"duplicates_removed": before - len(df)}


def clean_sales(sales: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame):
    df = sales.copy()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    issues = {}
    bad_qty = df["quantity"] <= 0
    issues["invalid_quantity_rows"] = int(bad_qty.sum())
    df = df[~bad_qty]
    orphan = ~df["customer_id"].isin(customers["customer_id"])
    issues["orphan_customer_rows"] = int(orphan.sum())
    df = df[~orphan]
    unknown_sku = ~df["sku"].isin(products["sku"])
    issues["unknown_sku_rows"] = int(unknown_sku.sum())
    df = df[~unknown_sku]
    issues["duplicate_order_ids"] = int(df.duplicated("order_id").sum())
    df = df.drop_duplicates("order_id")
    df["revenue"] = (df["quantity"] * df["unit_price"] * (1 - df["discount_pct"] / 100)).round(2)
    return df, issues


# ---------- Load ----------
def load(customers, products, sales):
    OUT.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as con:
        con.executescript("""
            CREATE TABLE dim_customer(customer_id TEXT PRIMARY KEY, full_name TEXT, email TEXT,
                                      country TEXT, segment TEXT, signup_date TEXT);
            CREATE TABLE dim_product(sku TEXT PRIMARY KEY, name TEXT, category TEXT, unit_price REAL);
            CREATE TABLE fact_sales(order_id TEXT PRIMARY KEY, customer_id TEXT REFERENCES dim_customer,
                                    sku TEXT REFERENCES dim_product, quantity INTEGER, unit_price REAL,
                                    discount_pct REAL, order_date TEXT, region TEXT, revenue REAL,
                                    source_file TEXT);
        """)
        customers.assign(signup_date=customers["signup_date"].dt.strftime("%Y-%m-%d")).to_sql(
            "dim_customer", con, if_exists="append", index=False)
        products.to_sql("dim_product", con, if_exists="append", index=False)
        sales.assign(order_date=sales["order_date"].dt.strftime("%Y-%m-%d")).to_sql(
            "fact_sales", con, if_exists="append", index=False)


# ---------- Validate ----------
def validate(customers, sales) -> list[dict]:
    checks = [
        ("Unique customer_id", customers["customer_id"].is_unique),
        ("Unique order_id", sales["order_id"].is_unique),
        ("No negative revenue", bool((sales["revenue"] >= 0).all())),
        ("No missing order dates", bool(sales["order_date"].notna().all())),
        ("All countries standardised", bool(customers["country"].isin(["Nepal", "India", "UAE"]).all())),
    ]
    with sqlite3.connect(DB_PATH) as con:
        wh = con.execute("SELECT ROUND(SUM(revenue),2) FROM fact_sales").fetchone()[0]
    checks.append(("Warehouse revenue reconciles to source", abs(wh - round(sales["revenue"].sum(), 2)) < 0.01))
    return [{"check": n, "status": "PASS" if ok else "FAIL"} for n, ok in checks]


def write_report(stats: dict, results: list[dict]):
    REPORTS.mkdir(exist_ok=True)
    lines = ["# Data Quality Report", "", "## Cleaning summary", ""]
    lines += [f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in stats.items()]
    lines += ["", "## Validation checks", "", "| Check | Status |", "|---|---|"]
    lines += [f"| {r['check']} | {r['status']} |" for r in results]
    (REPORTS / "data_quality_report.md").write_text("\n".join(lines))


def run():
    crm, sales_raw, products = extract()
    customers, cust_stats = clean_customers(crm)
    sales, sales_stats = clean_sales(sales_raw, customers, products)
    load(customers, products, sales)
    results = validate(customers, sales)
    stats = {"raw_crm_rows": len(crm), "raw_sales_rows": len(sales_raw), **cust_stats, **sales_stats,
             "clean_customers": len(customers), "clean_sales_rows": len(sales),
             "total_revenue": round(float(sales["revenue"].sum()), 2)}
    write_report(stats, results)
    return stats, results


if __name__ == "__main__":
    s, r = run()
    for k, v in s.items():
        print(f"{k:28s}{v}")
    print()
    for x in r:
        print(f"[{x['status']}] {x['check']}")
