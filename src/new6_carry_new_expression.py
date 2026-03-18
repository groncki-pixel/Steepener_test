"""
NEW-6: Carry & Scenario P&L for New Expression
================================================
Rebuilds the carry and scenario P&L analysis for the recommended SOFR futures
+ Micro 10Y short expression. Computes: SOFR implied rate vs current OIS,
carry on Micro 10Y short, scenario matrix across spread outcomes x holding
periods x Warsh scenarios.

Uses: SOFR Strips sheet from data_steepener.xlsx
Note: SOFR Strips sheet has data starting at col 4 (date) with values in cols 5-8.

Output: Console carry table + scenario P&L matrix
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DATA_FILE = "../data/data_steepener.xlsx"


def load_bloomberg_sheet(sheet, date_col=1, val_col=2):
    """Load Bloomberg-format sheet."""
    df = pd.read_excel(DATA_FILE, sheet_name=sheet, header=None)
    date_mask = df.apply(lambda row: row.astype(str).str.contains("Date", case=False).any(), axis=1)
    header_row = date_mask.idxmax() if date_mask.any() else 0
    data = df.iloc[header_row + 1:, [date_col, val_col]].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    return data.dropna().set_index("Date").sort_index()["Value"]


def load_tips_sheet():
    """Load USGGT02y which has date in col 0, value in col 1."""
    df = pd.read_excel(DATA_FILE, sheet_name="USGGT02y", header=None)
    date_mask = df.apply(lambda row: row.astype(str).str.contains("Date", case=False).any(), axis=1)
    header_row = date_mask.idxmax() if date_mask.any() else 0
    data = df.iloc[header_row + 1:, :2].copy()
    data.columns = ["Date", "Value"]
    data = data.dropna(subset=["Date", "Value"])
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    return data.dropna().set_index("Date").sort_index()["Value"]


# TODO: Implement analysis
# Note: SOFR Strips sheet has data starting at col 4 (date) with values in cols 5-8

print("NEW-6: Carry & Scenario P&L (New Expression) — NOT YET IMPLEMENTED. See docstring for spec.")
