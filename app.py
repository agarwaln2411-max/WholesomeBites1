# app.py - final robust version (carefully validated)
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

# load CSS (silent fallback)
load_css("assets/styles.css")

# --- constants (color tokens also available in CSS) ---
CAT_COLORS = ["#2B8E6B", "#64CBA3", "#FF6B5C", "#F6C85F", "#3B82F6", "#8B5CF6", "#D98A5A", "#9B9B9B"]
DIV_COLORS = ["#E63946", "#EAEAEA", "#2ECC71"]

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
            "date", "order_id", "product_id", "sku", "product_name", "category", "price", "cost", "qty",
            "revenue", "channel", "city", "warehouse", "inventory_on_hand", "ltv", "customer_id", "first_order",
            "spend", "visits", "add_to_cart", "checkout", "first_order_date"
        ]
        df = pd.DataFrame(columns=cols)
    # parse date safely
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.NaT
    # ensure expected columns exist
    expected = [
        "date", "order_id", "product_id", "sku", "product_name", "category", "price", "cost", "qty",
        "revenue", "channel", "city", "warehouse", "inventory_on_hand", "ltv", "customer_id", "first_order",
        "spend", "visits", "add_to_cart", "checkout", "first_order_date"
    ]
    for c in expected:
        if c not in df.columns:
            df[c] = np.nan
    # fallback date if all NaT to avoid date_input errors
    if df["date"].isna().all():
        df.loc[:, "date"] = pd.Timestamp.now().normalize()
    return df

# load dataframe
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
    ["Home", "Sales & Revenue", "Products", "Inventory", "Marketing & Acquisition", "Customers", "Exports & Settings"]
)

# Date filter with defensive defaults
min_date = df['date'].min() if not df['date'].isna().all() else pd.Timestamp.now().normalize()
max_date = df['date'].max() if not df['date'].isna().all() else pd.Timestamp.now().normalize()

# convert to date objects (Streamlit prefers date)
start_date_obj = min_date.date() if hasattr(min_date, "date") else pd.Timestamp.now().date()
end_date_obj = max_date.date() if hasattr(max_date, "date") else pd.Timestamp.now().date()

start_date, end_date = st.sidebar.date_input("Date range", value=(start_date_obj, end_date_obj))
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# Category & Channel filters (safe)
categories = ["All"] + sorted(df['category'].dropna().unique().tolist()) if 'category' in df.columns and not df['category'].dropna().empty else ["All"]
channels = ["All"] + sorted(df['channel'].dropna().unique().tolist()) if 'channel' in df.columns and not df['channel'].dropna().empty else ["All"]
sel_category = st.sidebar.selectbox("Category", categories, index=0)
sel_channel = st.sidebar.selectbox("Channel", channels, index=0)

# Apply filters
mask = (df['date'] >= start_date) & (df['date'] <= end_date)
if sel_category != "All":
    mask &= df['category'] == sel_category
if sel_channel != "All":
    mask &= df['channel'] == sel_channel
df_f = df.loc[mask].copy()

# debug view of filtered df
if show_debug:
    try:
        st.sidebar.write("Filtered rows (df_f):", getattr(df_f, "shape", "unknown"))
        st.sidebar.dataframe(df_f.head(10))
    except Exception as e:
        st.sidebar.write("Error showing df_f:", e)

# Helper KPI function (safe formatting)
def kpi_row(title, value, delta=None, format_fn=None):
    if format_fn:
        try:
            value_str = format_fn(value)
        except Exception:
            value_str = str(value)
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

    # KPIs (handle missing columns)
    total_revenue = df_f['revenue'].sum() if 'revenue' in df_f.columns and not df_f['revenue'].isna().all() else 0
    total_orders = df_f['order_id'].nunique() if 'order_id' in df_f.columns and not df_f['order_id'].isna().all() else 0
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

    # Revenue trend (safe)
    st.subheader("Revenue Trend")
    if 'revenue' in df_f.columns:
        try:
            rev_ts = df_f.groupby(pd.Grouper(key="date", freq="D"))['revenue'].sum().reset_index()
            fig_rev = px.area(rev_ts, x="date", y="revenue", title="Revenue over time", template="simple_white", color_discrete_sequence=["#2B8E6B"])
            st.plotly_chart(fig_rev, use_container_width=True)
        except Exception:
            st.info("Revenue trend unavailable due to data shape.")
    else:
        st.info("No `revenue` column found in the dataset.")

    # Top products & channels
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Products (by Revenue)")
        if 'product_name' in df_f.columns and 'revenue' in df_f.columns:
            top_prod = df_f.groupby(["product_id", "product_name"])['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(10)
            st.dataframe(top_prod.rename(columns={"product_name": "Product", "revenue": "Revenue"}).style.format({"Revenue": "${:,.2f}"}))
        else:
            st.info("Need `product_name` and `revenue` columns to show top products.")
    with c2:
        st.subheader("Revenue by Channel")
        if 'channel' in df_f.columns and 'revenue' in df_f.columns:
            ch = df_f.groupby("channel")['revenue'].sum().reset_index().sort_values("revenue", ascending=False)
            fig_ch = px.pie(ch, names="channel", values="revenue", title="Channel mix", color_discrete_sequence=CAT_COLORS)
            st.plotly_chart(fig_ch, use_container_width=True)
        else:
            st.info("Need `channel` and `revenue` columns for channel mix.")

elif nav == "Sales & Revenue":
    st.markdown("<h1 class='page-title'>Sales & Revenue</h1>", unsafe_allow_html=True)
    st.subheader("Revenue by Date Granularity")

    gran = st.selectbox("Granularity", ["D", "W", "M"], index=2, format_func=lambda x: {"D": "Daily", "W": "Weekly", "M": "Monthly"}[x])
    grp_map = {"D": "D", "W": "W", "M": "M"}
    grp = grp_map.get(gran, "M")

    if 'revenue' in df_f.columns:
        try:
            rev_ts = df_f.groupby(pd.Grouper(key="date", freq=grp))['revenue'].sum().reset_index()
            fig = px.line(rev_ts, x="date", y="revenue", title="Revenue", markers=True, color_discrete_sequence=["#2B8E6B"])
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Unable to render revenue time series for the selected granularity.")
    else:
        st.info("No `revenue` column available to plot. Add a `revenue` column to the CSV or data source.")

    st.subheader("Revenue by Category / Top N")
    topn = st.slider("Top N products", min_value=3, max_value=20, value=8)
    if 'product_name' in df_f.columns and 'revenue' in df_f.columns:
        try:
            prod_rev = df_f.groupby("product_name")['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(topn)
            fig2 = px.bar(prod_rev, x="revenue", y="product_name", orientation="h", title=f"Top {topn} Products by Revenue", color_discrete_sequence=CAT_COLORS)
            st.plotly_chart(fig2, use_container_width=True)
        except Exception:
            st.info("Unable to render top products chart due to data issues.")
    else:
        st.info("Need both `product_name` and `revenue` columns for Top N chart.")

elif nav == "Products":
    st.markdown("<h1 class='page-title'>Products / Catalog</h1>", unsafe_allow_html=True)
    st.subheader("Product Table")

    # FIXED: single groupby that aggregates qty per SKU and computes revenue/margin
    missing_minimal = [c for c in ["product_id", "product_name", "qty"] if c not in df_f.columns]
    if missing_minimal:
        st.info(f"Product table requires columns: {missing_minimal}. Showing available data instead.")
        st.dataframe(df_f.head(200))
    else:
        # normalize numeric fields
        df_f["qty"] = pd.to_numeric(df_f["qty"], errors="coerce").fillna(0)
        df_f["price"] = pd.to_numeric(df_f["price"], errors="coerce").fillna(0)
        df_f["cost"] = pd.to_numeric(df_f["cost"], errors="coerce").fillna(0)

        group_cols = ["product_id", "sku", "product_name", "category", "price", "cost"]
        # aggregate once
        prod_table = df_f.groupby(group_cols, dropna=False)["qty"].sum().reset_index()
        prod_table["revenue"] = prod_table["price"] * prod_table["qty"]
        prod_table["margin"] = prod_table["price"] - prod_table["cost"]
        prod_table = prod_table.sort_values("revenue", ascending=False).reset_index(drop=True)
        st.dataframe(prod_table.head(200))

elif nav == "Inventory":
    st.markdown("<h1 class='page-title'>Inventory & Fulfillment</h1>", unsafe_allow_html=True)
    if 'warehouse' in df_f.columns and 'inventory_on_hand' in df_f.columns:
        inv = df_f.groupby("warehouse")['inventory_on_hand'].sum().reset_index()
        fig_inv = px.bar(inv, x="warehouse", y="inventory_on_hand", title="Inventory on hand by warehouse", color_discrete_sequence=["#8B5CF6"])
        st.plotly_chart(fig_inv, use_container_width=True)
    else:
        st.info("Inventory view requires `warehouse` and `inventory_on_hand` columns.")

    st.subheader("Stockouts / Low stock")
    threshold = st.number_input("Stock threshold", min_value=0, value=10)
    if 'product_id' in df_f.columns and 'inventory_on_hand' in df_f.columns and 'product_name' in df_f.columns:
        low_stock = df_f.groupby(["product_id", "product_name"])['inventory_on_hand'].mean().reset_index().sort_values("inventory_on_hand").head(50)
        low_stock['status'] = np.where(low_stock['inventory_on_hand'] <= threshold, "LOW", "OK")
        st.dataframe(low_stock.head(200))
    else:
        st.info("Stockout table needs `product_id`, `product_name` and `inventory_on_hand`.")

elif nav == "Marketing & Acquisition":
    st.markdown("<h1 class='page-title'>Marketing & Acquisition</h1>", unsafe_allow_html=True)
    st.subheader("Spend & Revenue by Channel")
    if 'spend' in df_f.columns and 'revenue' in df_f.columns and 'channel' in df_f.columns:
        ch_perf = df_f.groupby("channel").agg({'spend': 'sum', 'revenue': 'sum'}).reset_index()
        ch_perf['roas'] = ch_perf.apply(lambda r: r['revenue'] / r['spend'] if r['spend'] and r['spend'] > 0 else np.nan, axis=1)
        fig_roas = px.bar(ch_perf, x='channel', y='roas', title="ROAS by Channel", color_discrete_sequence=CAT_COLORS)
        st.plotly_chart(fig_roas, use_container_width=True)
    else:
        st.info("Add `spend`, `revenue`, and `channel` columns to see Spend vs Revenue.")

    st.subheader("Funnel (visits -> orders)")
    if 'visits' in df_f.columns:
        funnel = pd.DataFrame({
            "stage": ["Visits", "Add to Cart", "Checkout", "Purchased"],
            "value": [
                df_f['visits'].sum(),
                df_f['add_to_cart'].sum() if 'add_to_cart' in df_f.columns else 0,
                df_f['checkout'].sum() if 'checkout' in df_f.columns else 0,
                df_f['order_id'].nunique() if 'order_id' in df_f.columns else 0
            ]
        })
        fig_f = px.funnel(funnel, x='value', y='stage', color_discrete_sequence=["#64CBA3", "#2B8E6B", "#F6C85F", "#FF6B5C"])
        st.plotly_chart(fig_f, use_container_width=True)
    else:
        st.info("Add `visits` (and optionally `add_to_cart`, `checkout`) columns to visualize funnel.")

elif nav == "Customers":
    st.markdown("<h1 class='page-title'>Customers</h1>", unsafe_allow_html=True)
    if 'customer_id' in df_f.columns and 'revenue' in df_f.columns:
        cust = df_f.groupby("customer_id")['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(20)
        st.dataframe(cust)
    else:
        st.info("Customers view needs `customer_id` and `revenue` columns.")

    st.subheader("Cohort: First order month retention (basic)")
    if 'first_order_date' in df.columns:
        df['first_month'] = pd.to_datetime(df['first_order_date'], errors="coerce").dt.to_period("M")
        df['order_month'] = df['date'].dt.to_period("M")
        cohorts = df.groupby(['first_month', 'order_month'])['customer_id'].nunique().reset_index()
        pivot = cohorts.pivot(index='first_month', columns='order_month', values='customer_id').fillna(0)
        st.dataframe(pivot)
    else:
        st.info("No `first_order_date` column present — add it for cohort analysis.")

elif nav == "Exports & Settings":
    st.markdown("<h1 class='page-title'>Exports & Settings</h1>", unsafe_allow_html=True)
    st.subheader("Download current filtered data")
    try:
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="filtered_data.csv", mime="text/csv")
    except Exception:
        st.info("Unable to produce CSV export for the filtered dataset.")

    st.markdown("### Developer / Deployment notes")
    st.markdown("""
    - Data file lives in `/data.csv` (for demo). For prod, connect to a database or cloud storage.
    - Use caching for heavy queries.
    - Use Streamlit Secrets or environment variables to store credentials.
    """)

# Footer spacer
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
