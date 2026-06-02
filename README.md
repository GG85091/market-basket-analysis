# Market Basket Analysis System

Python-based retail analytics platform built on association rule mining algorithms **Apriori** and **FP-Growth**.

## What it does

- Finds hidden purchasing patterns across 3,000+ transactions
- Recommends products based on basket analysis (top-5 per item)
- Seasonal analysis: Winter / Spring / Summer / Autumn
- Benchmarks Apriori vs FP-Growth performance
- Generates standalone HTML report with embedded charts
- Exports results to CSV and Excel

## Interfaces

| Interface | How to run |
|-----------|------------|
| Web (Streamlit) | `streamlit run streamlit_app.py` |
| CLI | `python main.py` |
| GUI (PyQt5) | `python gui_app.py` |

## Tech stack

Python · pandas · mlxtend · Streamlit · matplotlib · seaborn · PyQt5 · rich · openpyxl

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Dataset

Auto-generated on first run (`transactions.csv`). ~3,000 transactions · 5 stores · 20 products · 2015–2026

Stores: Korzinka, Makro, Havas, Smart, Supermarket Baraka
