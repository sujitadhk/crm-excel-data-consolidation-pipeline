"""Generate messy, realistic sample data that mimics three business sources:
1. CRM export (CSV)            - customers with duplicates, inconsistent formats
2. Regional sales workbooks    - Excel files with different column names per region
3. Product catalogue (JSON)    - export from an internal system / API
All data is synthetic."""
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)
random.seed(42)

FIRST = ["Aarav", "Sita", "Ramesh", "Anita", "Bikash", "Sunita", "Prakash", "Maya", "Rohan", "Kiran",
         "Nisha", "Suresh", "Pooja", "Dipak", "Rina", "Manish", "Asha", "Binod", "Laxmi", "Sagar"]
LAST = ["Sharma", "Thapa", "Gurung", "Shrestha", "Adhikari", "Rai", "Karki", "Magar", "Joshi", "Basnet"]
COUNTRY_VARIANTS = {"Nepal": ["Nepal", "NEPAL", "nepal", "NP"], "India": ["India", "IN", "india"],
                    "UAE": ["UAE", "United Arab Emirates", "uae"]}
SEGMENTS = ["Enterprise", "SMB", "Startup"]


def make_customers(n=300):
    rows = []
    for i in range(1, n + 1):
        first, last = random.choice(FIRST), random.choice(LAST)
        country = random.choice(list(COUNTRY_VARIANTS))
        signup = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 900)))
        fmt = random.choice(["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"])
        email = f"{first}.{last}{i}@example.com".lower()
        rows.append({
            "CustomerID": f"C{i:04d}",
            "Full Name": f"  {first} {last} " if random.random() < 0.2 else f"{first} {last}",
            "Email": None if random.random() < 0.05 else (email.upper() if random.random() < 0.1 else email),
            "Country": random.choice(COUNTRY_VARIANTS[country]),
            "Segment": random.choice(SEGMENTS),
            "Signup Date": signup.strftime(fmt),
        })
    df = pd.DataFrame(rows)
    dupes = df.sample(15, random_state=1).copy()          # duplicate CRM records
    return pd.concat([df, dupes], ignore_index=True).sample(frac=1, random_state=3)


def make_products():
    cats = {"Software": 120, "Hardware": 450, "Services": 80, "Support": 40}
    products = []
    for i in range(1, 41):
        cat = random.choice(list(cats))
        products.append({"sku": f"P{i:03d}", "name": f"{cat} Item {i}", "category": cat,
                         "unit_price": round(cats[cat] * float(rng.uniform(0.8, 1.6)), 2)})
    return products


def make_sales(customers, products, region, n, id_start, rename):
    cust_ids = customers["CustomerID"].unique()
    rows = []
    for i in range(n):
        p = random.choice(products)
        qty = int(rng.integers(1, 15))
        d = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 600)))
        rows.append({
            "order_id": f"{region[0]}{id_start + i}",
            "customer_id": random.choice(cust_ids) if random.random() > 0.02 else "C9999",  # orphan keys
            "sku": p["sku"],
            "quantity": qty if random.random() > 0.01 else -qty,                         # bad quantity
            "unit_price": p["unit_price"],
            "discount_pct": random.choice([0, 0, 0, 5, 10, 15]),
            "order_date": d,
            "region": region,
        })
    df = pd.DataFrame(rows)
    return df.rename(columns=rename)


def main():
    customers = make_customers()
    customers.to_csv(RAW / "crm_contacts.csv", index=False)
    products = make_products()
    (RAW / "product_catalogue.json").write_text(json.dumps({"products": products}, indent=2))

    north = make_sales(customers, products, "North", 900, 1000, {})
    south = make_sales(customers, products, "South", 800, 5000, {
        "order_id": "Order No", "customer_id": "Cust ID", "sku": "Product Code", "quantity": "Qty",
        "unit_price": "Price", "discount_pct": "Discount %", "order_date": "Date", "region": "Region"})
    north.to_excel(RAW / "sales_north.xlsx", index=False)
    south.to_excel(RAW / "sales_south.xlsx", index=False)
    print("Sample data written to", RAW)


if __name__ == "__main__":
    main()
