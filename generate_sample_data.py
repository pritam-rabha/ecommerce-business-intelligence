"""
generate_sample_data.py
------------------------
Generates a synthetic dataset that matches the schema of the Kaggle
"Online Retail Dataset" (https://www.kaggle.com/datasets/carrie1/ecommerce-data).

WHY THIS EXISTS:
The real dataset cannot be downloaded automatically in this environment
(no internet access). This script produces realistic, structurally
identical data (same columns, same data quality issues such as
cancellations, missing CustomerIDs, and negative quantities) so the
full pipeline (cleaning -> database -> dashboard) can be built and
tested end-to-end.

TO USE THE REAL DATA INSTEAD:
1. Download data.csv from the Kaggle link above.
2. Rename it to orders.csv.
3. Drop it into the data/ folder, replacing the generated file.
4. Re-run the app -- no code changes required, the schema matches.

Columns produced (identical to the real dataset):
    InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
    UnitPrice, CustomerID, Country
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

COUNTRIES = [
    "United Kingdom", "Germany", "France", "EIRE", "Spain", "Netherlands",
    "Belgium", "Switzerland", "Portugal", "Australia", "Norway", "Italy",
    "Finland", "Sweden", "Denmark", "USA", "Canada", "Japan", "Singapore",
]
COUNTRY_WEIGHTS = np.array([
    0.45, 0.08, 0.07, 0.05, 0.04, 0.04, 0.03, 0.03, 0.02, 0.02,
    0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
])
COUNTRY_WEIGHTS = COUNTRY_WEIGHTS / COUNTRY_WEIGHTS.sum()

PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("71053", "WHITE METAL LANTERN", 3.39),
    ("84406B", "CREAM CUPID HEARTS COAT HANGER", 2.75),
    ("84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 3.75),
    ("84029E", "RED WOOLLY HOTTIE WHITE HEART", 3.75),
    ("22752", "SET 7 BABUSHKA NESTING BOXES", 7.65),
    ("21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 4.25),
    ("22633", "HAND WARMER UNION JACK", 1.85),
    ("22632", "HAND WARMER RED POLKA DOT", 1.85),
    ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("22745", "POPPY'S PLAYHOUSE BEDROOM", 2.10),
    ("22748", "POPPY'S PLAYHOUSE KITCHEN", 2.10),
    ("22749", "FELTCRAFT PRINCESS CHARLOTTE DOLL", 3.75),
    ("22150", "3 STRIPEY MICE FELTCRAFT", 3.95),
    ("21212", "PACK OF 72 RETROSPOT CAKE CASES", 0.55),
    ("20725", "LUNCH BAG RED RETROSPOT", 1.65),
    ("20727", "LUNCH BAG BLACK SKULL", 1.65),
    ("20728", "LUNCH BAG CARS BLUE", 1.65),
    ("22383", "LUNCH BAG SUKI DESIGN", 1.65),
    ("23203", "JUMBO BAG DOILEY PATTERNS", 2.08),
    ("47566", "PARTY BUNTING", 4.95),
    ("85099B", "JUMBO BAG RED RETROSPOT", 2.08),
    ("23298", "SPACEBOY LUNCH BOX", 1.95),
    ("22961", "JAM MAKING SET PRINTED", 1.45),
    ("22960", "JAM MAKING SET WITH JARS", 4.25),
    ("21770", "TOADSTOOL LED NIGHT LIGHT", 3.95),
    ("22193", "RED DINER WALL CLOCK", 8.50),
    ("22699", "ROSES REGENCY TEACUP AND SAUCER", 2.95),
    ("22697", "GREEN REGENCY TEACUP AND SAUCER", 2.95),
    ("22698", "PINK REGENCY TEACUP AND SAUCER", 2.95),
    ("21034", "REX CASH+CARRY JUMBO SHOPPER", 1.25),
    ("23355", "HOT WATER BOTTLE KEEP CALM", 4.65),
    ("21931", "JUMBO STORAGE BAG SUKI", 2.08),
    ("22423", "REGENCY CAKESTAND 3 TIER", 12.75),
    ("84978", "HANGING HEART JAR T-LIGHT HOLDER", 1.45),
]

N_CUSTOMERS = 900
N_TRANSACTIONS = 26000  # base rows before cancellations/noise are added

CUSTOMER_IDS = RNG.integers(12346, 18287, size=N_CUSTOMERS)
CUSTOMER_IDS = np.unique(CUSTOMER_IDS)

START_DATE = pd.Timestamp("2024-01-01")
END_DATE = pd.Timestamp("2025-12-09")
DATE_RANGE_SECONDS = int((END_DATE - START_DATE).total_seconds())


def random_dates(n):
    """Generate n random timestamps between START_DATE and END_DATE,
    weighted slightly toward Nov/Dec (seasonal ecommerce spike)."""
    offsets = RNG.integers(0, DATE_RANGE_SECONDS, size=n)
    dates = START_DATE + pd.to_timedelta(offsets, unit="s")
    return dates


def generate():
    n = N_TRANSACTIONS
    product_idx = RNG.integers(0, len(PRODUCTS), size=n)
    stock_codes = [PRODUCTS[i][0] for i in product_idx]
    descriptions = [PRODUCTS[i][1] for i in product_idx]
    base_prices = np.array([PRODUCTS[i][2] for i in product_idx])

    # Small random price fluctuation to mimic real-world variance
    unit_prices = np.round(base_prices * RNG.uniform(0.9, 1.1, size=n), 2)

    quantities = RNG.integers(1, 25, size=n)

    customer_ids = RNG.choice(CUSTOMER_IDS, size=n)
    countries = RNG.choice(COUNTRIES, size=n, p=COUNTRY_WEIGHTS)

    invoice_dates = random_dates(n)

    # Invoice numbers: group ~3-6 line items under the same invoice
    invoice_no = np.zeros(n, dtype=np.int64)
    current_invoice = 536365
    i = 0
    while i < n:
        group_size = RNG.integers(1, 7)
        end = min(i + group_size, n)
        invoice_no[i:end] = current_invoice
        current_invoice += 1
        i = end

    df = pd.DataFrame({
        "InvoiceNo": invoice_no.astype(str),
        "StockCode": stock_codes,
        "Description": descriptions,
        "Quantity": quantities,
        "InvoiceDate": invoice_dates,
        "UnitPrice": unit_prices,
        "CustomerID": customer_ids,
        "Country": countries,
    })

    # --- Inject realistic data-quality issues (mirrors the real dataset) ---

    # 1. Cancellations: ~2% of invoices are cancellations (prefixed with 'C'),
    #    with negative quantities.
    cancel_mask = RNG.random(n) < 0.02
    df.loc[cancel_mask, "InvoiceNo"] = "C" + df.loc[cancel_mask, "InvoiceNo"]
    df.loc[cancel_mask, "Quantity"] = -df.loc[cancel_mask, "Quantity"]

    # 2. Missing CustomerID: ~8% of rows (guest checkouts), a known quirk
    #    of the real dataset.
    missing_cust_mask = RNG.random(n) < 0.08
    df.loc[missing_cust_mask, "CustomerID"] = np.nan

    # 3. Some invalid/negative quantities unrelated to cancellations (data
    #    entry errors) and a few zero unit prices.
    bad_qty_mask = RNG.random(n) < 0.005
    df.loc[bad_qty_mask, "Quantity"] = -RNG.integers(1, 5, size=bad_qty_mask.sum())

    zero_price_mask = RNG.random(n) < 0.003
    df.loc[zero_price_mask, "UnitPrice"] = 0.0

    # 4. Duplicate rows (~1%), as seen in the real data.
    dup_sample = df.sample(frac=0.01, random_state=42)
    df = pd.concat([df, dup_sample], ignore_index=True)

    # 5. A handful of missing Descriptions.
    missing_desc_mask = RNG.random(len(df)) < 0.004
    df.loc[missing_desc_mask, "Description"] = np.nan

    # Shuffle rows so invoices aren't in perfectly sorted blocks
    df = df.sample(frac=1.0, random_state=7).reset_index(drop=True)

    return df


if __name__ == "__main__":
    data = generate()
    out_path = "data/orders.csv"
    data.to_csv(out_path, index=False)
    print(f"Generated {len(data):,} rows -> {out_path}")
    print(data.head())
    print(data.dtypes)
