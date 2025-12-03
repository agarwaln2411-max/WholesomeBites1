# app.py (fixed: robust local_css loader + safe fallbacks)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os
from pathlib import Path

st.set_page_config(page_title="Operations Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- robust load CSS (design tokens) ---
def local_css(file_path):
    """
    Try multiple paths to load CSS. If not found, inject a small fallback CSS so app doesn't crash.
    """
    tried = []
    # 1) try exactly as given
    paths_to_try = [Path(file_path)]
    # 2) try relative to current file directory
    paths_to_try.append(Path(__file__).parent.joinpath(file_path))
    # 3) try relative to working directory /assets
    paths_to_try.append(Path.cwd().joinpath(file_path))
    # 4) try assets/styles.css explicitly
    paths_to_try.append(Path.cwd().joinpath("assets", "styles.css"))

    css_content = None
    for p in paths_to_try:
        tried.append(str(p))
        try:
            if p.exists():
                css_content = p.read_text(encoding="utf-8")
                break
        except Exception:
            # ignore and try next
            pass

    if css_content is None:
        # fallback minimal CSS so the app still loads and looks okay
        css_content = """
        /* fallback styles (assets/styles.css not found) */
        :root{
          --brand-primary: #2B8E6B;
          --neutral-900: #222222;
          --neutral-700: #4A4A4A;
          --neutral-100: #F5F5F5;
          --status-pos: #2ECC71;
        }
        .page-title{ font-size:28px; color:var(--neutral-900); font-weight:700; margin-bottom:6px; }
        .kpi-card{ background:#fff; border-radius:8px; padding:10px; box-shadow:0 1px 6px rgba(34,34,34,0.06); margin-bottom:8px; }
        .kpi-title{ color:var(--neutral-700); font-size:13px;}
        .kpi-value{ color:var(--neutral-900); font-size:18px; font-weight:700; margin-top:6px;}
        .kpi-delta{ color:var(--status-pos); font-size:12px;}
        .stDownloadButton > button { background: var(--brand-primary) !important; color: white !important; }
        """

        # log where we tried (helpful during debugging)
        st.warning(f"Warning: assets/styles.css not found. Tried paths: {tried}. Using fallback styles.")

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# Call loader
local_css("assets/styles.css")

# --- constants (color tokens also available in CSS) ---
CAT_COLORS = ["#2B8E6B","#64CBA3","#FF6B5C","#F6C85F","#3B82F6","#8B5CF6","#D98A5A","#9B9B9B"]
DIV_COLORS = ["#E63946","#EAEAEA","#2ECC71"]

# --- load data ---
@st.cache_data
def load_data(path="data.csv"):
    # if the CSV isn't next to app.py, try a few locations
    possible = [Path(path), Path(__file__).parent.joinpath(path), Path.cwd().joinpath(path)]
    df = None
    for p in possible:
        try:
            if p.exists():
                df = pd.read_csv(p, parse_dates=["date"])
                break
        except Exception:
            continue
    if df is None:
        # final attempt: try reading from working dir without parse_dates (graceful)
        try:
            df = pd.read_csv("data.csv")
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
        except Exception:
            # create an empty DataFrame with expected columns to avoid crashes
            expected = ["date","order_id","product_id","sku","product_name","category","price","cost","qty","revenue","channel","city","warehouse","inventory_on_hand","ltv","customer_id","first_order"]
            df = pd.DataFrame(columns=expected)
            df["date"] = pd.to_datetime(df["date"])
    # ensure expected columns exist
    expected = ["date","order_id","product_id","sku","product_name","category","price","cost","qty","revenue","channel","city","warehouse","inventory_on_hand","ltv","customer_id","first_order"]
    for c in expected:
        if c not in df.columns:
            df[c] = np.nan
    # If date column has NaT for all rows, set sensible defaults to avoid date_input errors
    if df["date"].isna().all():
        today = pd.Timestamp.now().normalize()
        df.loc[:, "date"] = today
    return df

df = load_data("data.csv")

# --- sidebar: global filters & navigation ---
st.sidebar.title("Filters & Navigation")
nav = st.sidebar.radio("Go to", ["Home","Sales & Revenue","Products","Inventory","Marketing & Acquisition","Customers","Exports & Settings"])

# Date filter
min_date = df['date'].min()
max_date = df['date'].max()
# Ensure min_date/max_date are proper datetimes
if pd.isna(min_date):
    min_date = pd.Timestamp.now().normalize()
if pd.isna(max_date):
    max_date = pd.Timestamp.now().normalize()

# date_input expects Python date objects or list of dates
start_date, end_date = st.sidebar.date_input("Date range", value=(min_date.date(), max_date.date()))
if isinstance(start_date, datetime): start_date = pd.to_datetime(start_date)
else: start_date = pd.to_datetime(start_date)
if isinstance(end_date, datetime): end_date = pd.to_datetime(end_date)
else: end_date = pd.to_datetime(end_date)

# Category & Channel filters (safe handling if columns empty)
categories = ["All"] + sorted(df['category'].dropna().unique().tolist()) if "category" in df.columns else ["All"]
channels = ["All"] + sorted(df['channel'].dropna().unique().tolist()) if "channel" in df.columns else ["All"]
sel_category = st.sidebar.selectbox("Category", categories, index=0)
sel_channel = st.sidebar.selectbox("Channel", channels, index=0)

# Apply filters
mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
if sel_category != "All":
    mask &= df['category'] == sel_category
if sel_channel != "All":
    mask &= df['channel'] == sel_channel
df_f = df.loc[mask].copy()

# Helper KPI functions
def kpi_row(title, value, delta=None, format_fn=None):
    if format_fn:
        value_str = format_fn(value)
    else:
        value_str = str(value)
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-title">{title}</div>
      <div class="kpi-value">{value_str}</div>
      <div class="kpi-delta">{delta if delta is not None else ''}</div>
    </div>
    """, unsafe_allow_html=True)

# --- NAVIGATION SCREENS ---
if nav == "Home":
    st.markdown("<h1 class='page-title'>Executive Summary</h1>", unsafe_allow_html=True)

    # KPIs
    total_revenue = df_f['revenue'].sum() if 'revenue' in df_f.columns else 0
    total_orders = df_f['order_id'].nunique() if 'order_id' in df_f.columns else 0
    avg_aov = (total_revenue / total_orders) if total_orders else 0
    new_customers = df_f[df_f['first_order'] == True]['customer_id'].nunique() if 'first_order' in df_f.columns and 'customer_id' in df_f.columns else (df_f['customer_id'].nunique() if 'customer_id' in df_f.columns else 0)
    avg_ltv = df_f['ltv'].mean() if 'ltv' in df_f.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_row("Revenue", total_revenue, format_fn=lambda x: f"${x:,.2f}")
    with col2:
        kpi_row("Orders", total_orders)
    with col3:
        kpi_row("AOV", avg_aov, format_fn=lambda x: f"${x:,.2f}")
    with col4:
        kpi_row("Average LTV", avg_ltv, format_fn=lambda x: f"${x:,.2f}")

    st.markdown("---")

    # Revenue trend
    st.subheader("Revenue Trend")
    if 'revenue' in df_f.columns:
        rev_ts = df_f.groupby(pd.Grouper(key="date", freq="D"))['revenue'].sum().reset_index()
        fig_rev = px.area(rev_ts, x="date", y="revenue", title="Revenue over time", template="simple_white",
                          color_discrete_sequence=["#2B8E6B"])
        st.plotly_chart(fig_rev, use_container_width=True)
    else:
        st.info("No revenue column found in the dataset.")

    # Top products & channels
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Products (by Revenue)")
        if 'product_name' in df_f.columns and 'revenue' in df_f.columns:
            top_prod = df_f.groupby(["product_id","product_name"])['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(10)
            st.dataframe(top_prod.rename(columns={"product_name":"Product","revenue":"Revenue"}).style.format({"Revenue":"${:,.2f}"}))
        else:
            st.info("Need 'product_name' and 'revenue' columns to show top products.")
    with c2:
        st.subheader("Revenue by Channel")
        if 'channel' in df_f.columns and 'revenue' in df_f.columns:
            ch = df_f.groupby("channel")['revenue'].sum().reset_index().sort_values("revenue", ascending=False)
            fig_ch = px.pie(ch, names="channel", values="revenue", title="Channel mix", color_discrete_sequence=CAT_COLORS)
            st.plotly_chart(fig_ch, use_container_width=True)
        else:
            st.info("Need 'channel' and 'revenue' columns for channel mix.")

# (other nav sections follow the same pattern as before; omitted here for brevity)
# For your deployment, keep the rest of the content from your previous app.py
# or merge this loader block into the top of your existing file.
