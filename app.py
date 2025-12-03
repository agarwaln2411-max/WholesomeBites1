# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Operations Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- load CSS (design tokens) ---
def local_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("assets/styles.css")

# --- constants (color tokens also available in CSS) ---
CAT_COLORS = ["#2B8E6B","#64CBA3","#FF6B5C","#F6C85F","#3B82F6","#8B5CF6","#D98A5A","#9B9B9B"]
DIV_COLORS = ["#E63946","#EAEAEA","#2ECC71"]

# --- load data ---
@st.cache_data
def load_data(path="data.csv"):
    df = pd.read_csv(path, parse_dates=["date"])
    # ensure required columns exist
    expected = ["date","order_id","product_id","sku","product_name","category","price","cost","qty","revenue","channel","city","warehouse","inventory_on_hand","ltv","customer_id","first_order"]
    for c in expected:
        if c not in df.columns:
            df[c] = np.nan
    return df

df = load_data("data.csv")

# --- sidebar: global filters & navigation ---
st.sidebar.title("Filters & Navigation")
nav = st.sidebar.radio("Go to", ["Home","Sales & Revenue","Products","Inventory","Marketing & Acquisition","Customers","Exports & Settings"])

# Date filter
min_date = df['date'].min()
max_date = df['date'].max()
start_date, end_date = st.sidebar.date_input("Date range", value=(min_date, max_date))
if isinstance(start_date, datetime): start_date = pd.to_datetime(start_date)
if isinstance(end_date, datetime): end_date = pd.to_datetime(end_date)

# Category & Channel filters
categories = ["All"] + sorted(df['category'].dropna().unique().tolist())
channels = ["All"] + sorted(df['channel'].dropna().unique().tolist())
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
    total_revenue = df_f['revenue'].sum()
    total_orders = df_f['order_id'].nunique()
    avg_aov = (total_revenue / total_orders) if total_orders else 0
    new_customers = df_f[df_f['first_order'] == True]['customer_id'].nunique() if 'first_order' in df_f.columns else df_f['customer_id'].nunique()
    avg_ltv = df_f['ltv'].mean()

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
    rev_ts = df_f.groupby(pd.Grouper(key="date", freq="D"))['revenue'].sum().reset_index()
    fig_rev = px.area(rev_ts, x="date", y="revenue", title="Revenue over time", template="simple_white",
                      color_discrete_sequence=["#2B8E6B"])
    st.plotly_chart(fig_rev, use_container_width=True)

    # Top products & channels
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Products (by Revenue)")
        top_prod = df_f.groupby(["product_id","product_name"])['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(10)
        st.dataframe(top_prod.rename(columns={"product_name":"Product","revenue":"Revenue"}).style.format({"Revenue":"${:,.2f}"}))
    with c2:
        st.subheader("Revenue by Channel")
        ch = df_f.groupby("channel")['revenue'].sum().reset_index().sort_values("revenue", ascending=False)
        fig_ch = px.pie(ch, names="channel", values="revenue", title="Channel mix", color_discrete_sequence=CAT_COLORS)
        st.plotly_chart(fig_ch, use_container_width=True)

elif nav == "Sales & Revenue":
    st.markdown("<h1 class='page-title'>Sales & Revenue</h1>", unsafe_allow_html=True)
    st.subheader("Revenue by Date Granularity")
    gran = st.selectbox("Granularity", ["D","W","M"], index=2, format_func=lambda x: {"D":"Daily","W":"Weekly","M":"Monthly"}[x])
    grp = {'D':'D','W':'W','M':'M'}[gran]
    rev_ts = df_f.groupby(pd.Grouper(key="date", freq=grp))['revenue'].sum().reset_index()
    fig = px.line(rev_ts, x="date", y="revenue", title="Revenue", markers=True, color_discrete_sequence=["#2B8E6B"])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue by Category / Top N")
    topn = st.slider("Top N products", min_value=3, max_value=20, value=8)
    prod_rev = df_f.groupby("product_name")['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(topn)
    fig2 = px.bar(prod_rev, x="revenue", y="product_name", orientation="h", title=f"Top {topn} Products by Revenue",
                  color_discrete_sequence=CAT_COLORS)
    st.plotly_chart(fig2, use_container_width=True)

elif nav == "Products":
    st.markdown("<h1 class='page-title'>Products / Catalog</h1>", unsafe_allow_html=True)
    st.subheader("Product Table")
    prod_cols = ["product_id","sku","product_name","category","price","cost","revenue"]
    prod_table = df_f.groupby(prod_cols)['qty'].sum().reset_index().groupby(["product_id","sku","product_name","category","price","cost"])['qty'].sum().reset_index()
    # compute revenue & margin per SKU
    prod_table['revenue'] = prod_table['price'] * prod_table['qty']
    prod_table['margin'] = prod_table['price'] - prod_table['cost']
    st.dataframe(prod_table.sort_values("revenue", ascending=False).head(200).reset_index(drop=True))

    st.subheader("Price distribution")
    fig_price = px.histogram(df_f, x="price", nbins=30, title="Price Distribution", color_discrete_sequence=["#F6C85F"])
    st.plotly_chart(fig_price, use_container_width=True)

elif nav == "Inventory":
    st.markdown("<h1 class='page-title'>Inventory & Fulfillment</h1>", unsafe_allow_html=True)
    st.subheader("Inventory by Warehouse")
    inv = df_f.groupby("warehouse")['inventory_on_hand'].sum().reset_index()
    fig_inv = px.bar(inv, x="warehouse", y="inventory_on_hand", title="Inventory on hand by warehouse", color_discrete_sequence=["#8B5CF6"])
    st.plotly_chart(fig_inv, use_container_width=True)

    st.subheader("Stockouts / Low stock")
    threshold = st.number_input("Stock threshold", min_value=0, value=10)
    low_stock = df_f.groupby(["product_id","product_name"])['inventory_on_hand'].mean().reset_index().sort_values("inventory_on_hand").head(50)
    low_stock['status'] = np.where(low_stock['inventory_on_hand'] <= threshold, "LOW", "OK")
    st.dataframe(low_stock.head(200))

elif nav == "Marketing & Acquisition":
    st.markdown("<h1 class='page-title'>Marketing & Acquisition</h1>", unsafe_allow_html=True)
    st.subheader("Spend & Revenue by Channel")
    if 'spend' not in df_f.columns:
        st.info("No 'spend' column present in dataset — add ad spend per row to calculate CAC / ROAS.")
    else:
        ch_perf = df_f.groupby("channel").agg({'spend':'sum','revenue':'sum'}).reset_index()
        ch_perf['roas'] = ch_perf['revenue'] / ch_perf['spend']
        fig_roas = px.bar(ch_perf, x='channel', y='roas', title="ROAS by Channel", color_discrete_sequence=CAT_COLORS)
        st.plotly_chart(fig_roas, use_container_width=True)

    st.subheader("Funnel (visits -> orders)")
    if 'visits' in df_f.columns:
        funnel = pd.DataFrame({
            "stage": ["Visits","Add to Cart","Checkout","Purchased"],
            "value": [df_f['visits'].sum(), df_f['add_to_cart'].sum() if 'add_to_cart' in df_f.columns else 0, df_f['checkout'].sum() if 'checkout' in df_f.columns else 0, df_f['order_id'].nunique()]
        })
        fig_f = px.funnel(funnel, x='value', y='stage', color_discrete_sequence=["#64CBA3","#2B8E6B","#F6C85F","#FF6B5C"])
        st.plotly_chart(fig_f, use_container_width=True)
    else:
        st.info("Add events columns like 'visits','add_to_cart' to visualize funnel.")

elif nav == "Customers":
    st.markdown("<h1 class='page-title'>Customers</h1>", unsafe_allow_html=True)
    st.subheader("Top Customers by Revenue")
    cust = df_f.groupby("customer_id")['revenue'].sum().reset_index().sort_values("revenue", ascending=False).head(20)
    st.dataframe(cust)

    st.subheader("Cohort: First order month retention (basic)")
    if 'first_order_date' in df.columns:
        df['first_month'] = df['first_order_date'].dt.to_period("M")
        df['order_month'] = df['date'].dt.to_period("M")
        cohorts = df.groupby(['first_month','order_month'])['customer_id'].nunique().reset_index()
        pivot = cohorts.pivot(index='first_month', columns='order_month', values='customer_id').fillna(0)
        st.dataframe(pivot)
    else:
        st.info("No 'first_order_date' column in data.csv — cohort requires first order info.")

elif nav == "Exports & Settings":
    st.markdown("<h1 class='page-title'>Exports & Settings</h1>", unsafe_allow_html=True)
    st.subheader("Download current filtered data")
    st.write("You can export the currently filtered rows as CSV.")
    csv = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="filtered_data.csv", mime="text/csv")

    st.markdown("### Developer / Deployment notes")
    st.markdown("""
    - Data file lives in `/data.csv` (for demo). For prod, connect to a database or cloud storage.
    - Use caching for heavy queries.
    - Use Streamlit Secrets or environment variables to store credentials.
    """)

# Footer
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
