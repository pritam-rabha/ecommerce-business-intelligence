# E-Commerce Business Intelligence Platform

A full-stack, production-style **Business Intelligence dashboard** for an e-commerce business — built with Python, Streamlit, SQLite/SQLAlchemy, and Plotly. It ingests raw transactional order data, cleans and models it, stores it in a relational database, and surfaces it through an interactive, multi-page analytics dashboard with automated business insights.

Built to demonstrate the end-to-end skill set of a **Data Analyst / Business Intelligence Developer**: data cleaning, data modeling, SQL, and dashboard/visualization design.

> **Dataset note:** This project is built for the [Online Retail Dataset (Kaggle)](https://www.kaggle.com/datasets/carrie1/ecommerce-data). A synthetic dataset with the identical schema is bundled under `data/` so the project runs out of the box; swap in the real `data.csv` from Kaggle (renamed to `orders.csv`) for production use — no code changes required. See [Dataset](#-dataset) below.

---

## Table of Contents

- [Project Overview](#-project-overview)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Tech Stack](#-technologies-used)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Dataset](#-dataset)
- [Future Improvements](#-future-improvements)
- [License](#-license)

---

## Project Overview

Online retailers generate huge volumes of raw transactional data, but raw data isn't decision-ready. This project simulates the work of an in-house BI team: turning messy invoice-level order data into a governed dataset and a self-service analytics platform that a Sales, Marketing, or Executive team could actually use.

The platform covers the full pipeline:

**Raw CSV → Cleaning & Validation → SQLite Database → Analytical Layer → Interactive Dashboard → Automated Insights & Export**

---

## Features

### Data Engineering
- Automated cleaning pipeline: duplicate removal, missing-value handling, datatype enforcement, cancelled-order removal, invalid quantity/price filtering
- Derived fields: `TotalPrice`, `Year`, `Month`, `Weekday`, `Week`, etc.
- Cleaned data persisted both as CSV and into a SQLite database via SQLAlchemy
- Reusable, parameterized SQL query layer (`OrderQueries`) — portable to MySQL/Postgres with a one-line connection string change

### Interactive Dashboard (7 pages)
| Page | Key Metrics |
|---|---|
| **Executive Dashboard** | Revenue, Orders, Customers, Products, AOV, MoM Growth, KPI cards |
| **Sales Analytics** | Monthly / Weekly / Daily revenue trends, simple moving-average forecast |
| **Customer Analytics** | Top customers, New vs. Returning, simplified CLV, value segmentation |
| **Product Analytics** | Top/bottom products, revenue breakdown treemap, quantity sold |
| **Geographic Analytics** | Choropleth world map, revenue/orders by country, weekday × month heatmap |
| **Business Insights** | Auto-generated natural-language insights, order value distribution |
| **Data Explorer** | Raw filtered data preview, CSV/Excel export, live database query snapshot |

### Filtering
Sidebar filters for **Date Range, Country, Customer, Product, and Invoice Number**, combined with logical AND and applied live across every page.

### Visualization
9 chart types via Plotly: bar, line, area, pie, donut, treemap, heatmap, scatter, histogram — plus an interactive choropleth map.

### Export
One-click **CSV** and formatted **Excel** (via OpenPyXL) export of the currently filtered dataset.

### Performance
- `st.cache_data` for the cleaning pipeline and aggregation results
- `st.cache_resource` for the database engine/connection
- Aggregation pushed to pandas/SQL rather than row-by-row Python loops

---

## Screenshots

> Add screenshots of the running app here after your first local run.

```
screenshots/
├── executive_dashboard.png
├── sales_analytics.png
├── customer_analytics.png
├── product_analytics.png
├── geographic_analytics.png
└── business_insights.png
```

---

## Technologies Used

| Category | Technology |
|---|---|
| Language | Python 3.12 |
| Dashboard Framework | Streamlit |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly, Matplotlib |
| Database | SQLite (SQLAlchemy ORM/Core) — MySQL-ready |
| Export | OpenPyXL |
| Version Control | Git, GitHub |

---

## Project Structure

```
ecommerce-business-intelligence/
│
├── app.py                    # Main Streamlit application (pages, layout, caching)
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── .gitignore                # Git ignore rules
│
├── assets/                   # Static assets (logo, icons)
├── screenshots/              # Dashboard screenshots for documentation
│
├── database/
│   └── ecommerce.db          # Auto-generated SQLite database
│
├── data/
│   ├── orders.csv            # Raw dataset (Kaggle schema)
│   └── orders_clean.csv      # Cleaned dataset (auto-generated)
│
└── src/
    ├── __init__.py
    ├── utils.py               # Logging config, paths, formatting helpers
    ├── data_cleaning.py        # DataCleaner class: full cleaning pipeline
    ├── database.py              # SQLAlchemy engine, schema, OrderQueries
    ├── analysis.py               # Pandas analytical functions (all pages)
    ├── charts.py                  # Plotly chart builder functions
    ├── filters.py                  # Sidebar filters + filtering logic
    ├── insights.py                  # Automated business insight generation
    └── export.py                     # CSV / Excel export helpers
```

---

## Installation

**Prerequisites:** Python 3.12 (3.10+ generally works), pip, git.

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/ecommerce-business-intelligence.git
cd ecommerce-business-intelligence

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

On first run, if `data/orders_clean.csv` doesn't exist yet, the app automatically runs the cleaning pipeline against `data/orders.csv` and builds the SQLite database — no manual setup steps required.

**To run the cleaning pipeline or rebuild the database manually:**

```bash
python -m src.data_cleaning     # regenerates data/orders_clean.csv
python -m src.database          # rebuilds database/ecommerce.db
```

---

## Dataset

This project targets the **[Online Retail Dataset](https://www.kaggle.com/datasets/carrie1/ecommerce-data)** on Kaggle — real transactional data from a UK-based online retailer (Dec 2010–Dec 2011), with columns:

`InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country`

**To use the real dataset:**
1. Download `data.csv` from the Kaggle link above.
2. Rename it to `orders.csv`.
3. Place it in the `data/` folder, replacing the bundled sample file.
4. Run the app — the schema matches exactly, no code changes needed.

**Bundled sample data:** For out-of-the-box functionality (e.g. in environments without internet access to Kaggle), `data/orders.csv` ships with a synthetic dataset generated to match the real dataset's schema and known data-quality quirks (cancellations, missing Customer IDs, occasional duplicates). See `generate_sample_data.py` for the generation logic. Replace it with the real file for actual analysis.

---

## Future Improvements

- [ ] Native MySQL/PostgreSQL deployment (connection string is already parameterized in `database.py`)
- [ ] RFM (Recency, Frequency, Monetary) customer segmentation model
- [ ] Cohort retention analysis
- [ ] Proper time-series forecasting (Prophet / ARIMA) beyond the current SMA baseline
- [ ] Role-based authentication for multi-user access
- [ ] Scheduled ETL refresh (Airflow / cron) instead of on-demand cleaning
- [ ] Unit test suite (pytest) for `src/` modules
- [ ] Dockerfile for containerized deployment
- [ ] Deployment to Streamlit Community Cloud

---

## License

This project is released under the [MIT License](LICENSE). Free to use, modify, and distribute for personal, academic, or portfolio purposes.

---

<p align="center">Built as a portfolio project demonstrating Data Analytics / Business Intelligence engineering skills.</p>
