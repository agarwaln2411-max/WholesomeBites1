# app.py - final robust version with debug toggle
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Operations Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Embedded fallback CSS (used silently if assets/styles.css not found) ---
EMBEDDED_CSS = """
:root{
  --brand-primary: #2B8E6B;
  --brand-primary-600: #246F52;
  --brand-primary-300: #96E1C4;
  --brand-secondary: #F4E9D7;
  --brand-accent: #FF6B5C;
  --brand-accent-alt: #F6C85F;
  --neutral-900: #222222;
  --neutral-700: #4A4A4A;
  --neutral-400: #9B9B9B;
  --neutral-100: #F5F5F5;
  --status-pos: #2ECC71;
  --status-neg: #E63946;
  --status-warn: #FFA500;
  --status-info: #3B82F6;
}
.page-title{ font-size: 28px; color: var(--neutral-900); font-weight: 700; margin-bottom: 8px; }
.kpi-card{ background: white; border-radius: 8px; padding: 12px; box-shadow: 0 1px 6px rgba(34,34,34,0.06); margin-bottom: 10px; }
.kpi-title { color: var(--neutral-700); font-size: 13px; }
.kpi-value { color: var(--neutral-900); font-size: 20px; font-weight:700; margin-top:6px; }
.kpi-delta { color: var(--status-pos); font-size: 13px; }
.reportview-container .main .block-container{ padding-left: 1rem; padding-right: 1rem; }
.stDataFrame table { border-collapse: collapse; }
a { color: var(--brand-primary); }
"""

def load_css(preferred_path="assets/styles.css"):
    candidates = [
        Path(preferred_path),
        Path(__file__).parent.joinpath(preferred_path),
        Path.cwd().joinpath(preferred_path),
        Path.cwd().joinpath("assets", "styles.css")
    ]
    css_text = None
    for c in candidates:
        try:
            if c.exists():
                css_text = c.read_text(encoding="utf-8")
                break
        except Exception:
            continue
    if css_text is None:
        css_text = EMBEDDED_CSS
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)

load_css("assets/styles.css")

# --- constants (color tokens also available in CSS) ---
CAT_COLORS = ["#2B8E6B","#64CBA3","#FF6B5C","#F6C85F","#3B82F6","#8B5CF6","#D98A5A","#9B9B9B"]
DIV_COLORS = ["#E63946","#EAEAEA","#2ECC71"]

# --- load data (defensive) ---
@st.cache_data
def load_data(path="data.csv"):
    possible = [
        Path(path),
        Path(__file__).parent.joinpath(path),
        Path.cwd().joinpath(path)
    ]
    df = None
    for p in possible:
        try:
            if p.exists():
                df = pd.read_csv(p)
                break
        except Exception:
            continue
    if df is None:
        # Create empty dataframe with expected columns so app doesn't crash
        cols = [
            "date","order_id","product_id","sku","product_name","category","price","cost","qty",
            "revenue","channel","city","warehouse","inventory_on_hand","ltv","customer_id","first_order",
            "spend","visits","add_to_cart","checkout","first_order_date"
        ]
        df = pd.DataFrame(columns=cols)
    # parse date safely
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.NaT
    # ensure expected columns exist
    expected = [
        "date","order_id","product_id","sku","product_name","category","price","cost","qty",
        "revenue","channel","city","warehouse","inventory_on_hand","ltv","customer_id","first_order",
        "spend","visits","add_to_cart","checkout","first_order_date"
    ]
    for c in expected:
        if c not in df.columns:
            df[c] = np.nan
    # fallback date if all NaT to avoid date_input errors
    if df["date"].isna().all():
        df.loc[:, "date"] = pd.Timestamp.now().normalize()
    return df

df = load_data("data.csv")

# --- DEBUG SNIPPET: show data diagnostics when needed ---
show_debug = st.sidebar.checkbox("Show data debug", value=False)
if show_debug:
    st.sidebar.markdown("### Raw data diagnostics")
    try:
        st.sidebar.write("Full dataset rows:", len(df))
        st.sidebar.write("Columns:", list(df.columns))
        st.sidebar.dataframe(df.head(10))
    except Exception as e:
        st.sidebar.write("Error reading df:", e)

# --- sidebar: global filters & navigation ---
st.sidebar.title("Filters & Navigation")
nav = st.sidebar.radio(
    "Go to",
    ["Home","Sales & Revenue","Products","Inventory","Marketing & Acquisition","Customers","Exports & Settings"]
)

# Date filter with defensive defaults
min_date = df['date'].min() if not df['date'].isna().all() else pd.Timestamp.now().normalize()
max_date = df['date'].max() if not df['date'].isna().all() else pd.Timestamp.now().normalize()

start_date_obj = min_date.date() if hasattr(min_date, "date") else pd.Timestamp.now().date()
end_date_obj = max_date.date() if hasattr(max_date, "date") else pd.Timestamp.now().date()

start_date, end_date = st.sidebar.date_input("Date range", value=(start_date_obj, end_date_obj))
start_date = pd.to_datetime(start_dat_
