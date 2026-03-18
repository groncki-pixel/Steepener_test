"""
NEW-1: Fed Path Repricing Analysis
===================================
Compares WIRP implied rates on Feb 27 vs Mar 18 to quantify how many cuts
were removed from the Fed path. Uses Wirp_02_27 and Wirp_03_18 sheets.
Computes: implied cuts removed, implied rate change at each meeting, and
compares to A07 passthrough estimates to argue whether the repricing is
justified given the oil shock magnitude.

Uses: Wirp_02_27, Wirp_03_18 sheets from data_steepener.xlsx

Output: Console table of implied rate paths + repricing summary
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
# Note: WIRP sheets are structured tables, not time series — parse them differently

print("NEW-1: Fed Path Repricing — NOT YET IMPLEMENTED. See docstring for spec.")
