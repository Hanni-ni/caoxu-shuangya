import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="草畜双押估值系统", layout="wide")
st.title("🌾 草畜双押 · 牧区双资产金融科技平台")
st.markdown("**天然草场经营权质押 + 畜禽活体抵押 | 天‑空‑地一体化智能风控 | 双资产联动 · 动态抵押率 · 贷后实时预警**")

# 侧边栏输入参数
st.sidebar.header("📊 输入参数")

grassland_area = st.sidebar.number_input("草场面积 (亩)", value=5000, step=100)
grass_price_per_mu = st.sidebar.number_input("草场流转均价 (元/亩·年)", value=50.0, step=5.0)
contract_years = st.sidebar.number_input("承包剩余年限 (年)", value=30, step=5)
discount_rate = st.sidebar.number_input("折现率 (%)", value=5.0, step=0.5) / 100
forage_price = st.sidebar.number_input("饲草市场价格 (元/吨)", value=500, step=50)
ndvi_to_yield = st.sidebar.number_input("NDVI转产草量系数 (kg/亩/0.1NDVI)", value=300, step=50)
carbon_price = st.sidebar.number_input("碳汇价格 (元/吨)", value=7.0, step=1.0)
carbon_rate = st.sidebar.number_input("每年固碳量 (吨/亩·年)", value=0.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("**联合抵押率参数**")
alpha = st.sidebar.number_input("草场估值权重 α", value=0.4, step=0.05)
beta = st.sidebar.number_input("活体估值权重 β", value=0.6, step=0.05)
base_mortgage_rate = st.sidebar.number_input("基础抵押率", value=0.6, step=0.05)

# 真实 NDVI 数据（MODIS 2020-2023）
default_ndvi = [0.355, 0.418, 0.360, 0.335]
years = [2020, 2021, 2022, 2023]

uploaded_file = st.sidebar.file_uploader("或上传 NDVI 序列 (CSV, 两列: 年份, NDVI)", type=["csv"])
if uploaded_file is not None:
    df_user = pd.read_csv(uploaded_file)
    if "年份" in df_user.columns and "NDVI" in df_user.columns:
        years = df_user["年份"].tolist()
        ndvi_list = df_user["NDVI"].tolist()
    else:
        st.sidebar.error("CSV 需要包含 '年份' 和 'NDVI' 两列")
        ndvi_list = default_ndvi
else:
    ndvi_list = default_ndvi

# 计算基础价值（折现）
base_value = (grassland_area * grass_price_per_mu * contract_years *
              (1 / (1 + discount_rate) ** contract_years)) / 10000

results = []
prev_ndvi = None

for i, (year, ndvi) in enumerate(zip(years, ndvi_list)):
    yield_kg_per_mu = ndvi / 0.1 * ndvi_to_yield
    total_yield_kg = yield_kg_per_mu * grassland_area
    total_yield_ton = total_yield_kg / 1000
    productivity_value = total_yield_ton * forage_price / 10000
    carbon_sequestration = grassland_area * carbon_rate
    carbon_value = carbon_sequestration * carbon_price / 10000
    total_value = base_value + productivity_value + carbon_value

    warning = ""
    if prev_ndvi is not None:
        decline = (prev_ndvi - ndvi) / prev_ndvi if prev_ndvi != 0 else 0
        if decline > 0.15:
            warning = f"⚠️ 触发贷后预警 (NDVI下降{decline:.1%})"
        elif decline > 0:
            warning = f"正常 (NDVI下降{decline:.1%})"
        else:
            warning = "正常 (NDVI上升)"
    else:
        warning = "基准年"

    results.append({
        "年份": year,
        "NDVI": ndvi,
        "年产草量(吨)": round(total_yield_ton, 1),
        "生产力价值(万元)": round(productivity_value, 2),
        "碳汇价值(万元)": round(carbon_value, 2),
        "草场总估值(万元)": round(total_value, 2),
        "风控状态": warning
    })
    prev_ndvi = ndvi

df_results = pd.DataFrame(results)

st.subheader("📈 模型验证结果（基于真实NDVI数据）")
st.dataframe(df_results, use_container_width=True)

last_row = df_results.iloc[-1]
st.subheader("🚨 风控结论")
if "触发贷后预警" in last_row["风控状态"]:
    st.error(last_row["风控状态"])
else:
    st.success(last_row["风控状态"])

st.subheader("📉 NDVI 年际变化趋势")
st.line_chart(df_results.set_index("年份")["NDVI"])

st.subheader("🏦 双资产联合抵押率模拟")
col1, col2 = st.columns(2)
with col1:
    cattle_count = st.number_input("肉牛存栏 (头)", value=50, step=5)
    cattle_price = st.number_input("肉牛单价 (万元/头)", value=1.5, step=0.1)
    health_factor = st.slider("活体健康系数", 0.5, 1.2, 0.9, 0.05)
with col2:
    grassland_value = st.number_input("草场估值 (万元，可从上方结果选取)", value=df_results.iloc[-1]["草场总估值(万元)"])
    live_value = cattle_count * cattle_price * health_factor
    st.metric("活体估值 (万元)", f"{live_value:.2f}")
    combined = grassland_value * alpha + live_value * beta
    mortgage_limit = combined * base_mortgage_rate
    st.metric("联合抵押率上限 (万元)", f"{mortgage_limit:.2f}")

st.caption("数据来源：USGS MODIS MOD13Q1 (2020-2023年新巴尔虎右旗生长季均值)")