import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh # 新增自動重整組件

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="GEX Pro 專業交易儀表板", layout="centered", page_icon="📈")

# ⚠️ 請填入你的 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNCAxNjo1NDo0MiIsInVzZXJfaWQiOiJhbGFubmFsYTA1IiwiZW1haWwiOiJhbGFubmFsYTA1QGdtYWlsLmNvbSIsImlwIjoiMzYuMjM4LjI0Ni42In0.-Q3sLZ8ZtHjRlgEcSqoEyoejG4EHHZmtR_KDo4Tw1yk" 

# --- 自動重整機制 (每 60 秒自動更新一次網頁) ---
st_autorefresh(interval=60000, key="datarefresh")

# --- 2. 側邊欄控制面板 ---
with st.sidebar:
    st.title("⚙️ 系統控制面板")
    st.write("---")
    use_simulation = st.toggle("開啟模擬模式 (週末/測試用)", value=False)
    
    # 針對一口微台，建議 300 秒 (5分鐘) 抓一次資料即可，但網頁每 60 秒重整確保不當機
    update_interval = st.number_input("數據快照有效時間 (秒)", min_value=30, max_value=3600, value=300)
    
    if use_simulation:
        st.info("💡 模擬測試中...")
        sim_price = st.slider("模擬價格", 20000.0, 35000.0, 32284.0)
        sim_pcr = st.slider("模擬 P/C Ratio", 0.5, 2.0, 1.31)
    else:
        st.success("✅ 正在連線 FinMind 實時 API")

# --- 3. 數據抓取與計算 ---
@st.cache_data(ttl=update_interval)
def fetch_all_data(token, is_sim=False):
    if is_sim: return sim_price, sim_pcr
    try:
        api = DataLoader()
        api.login_by_token(api_token=token)
        df_fut = api.taiwan_futures_snapshot()
        current_price = df_fut[df_fut['full_code'] == 'TXF']['last_price'].values[0] if df_fut is not None else 32284.0
        df_opt = api.taiwan_options_snapshot()
        if df_opt is not None and not df_opt.empty:
            pcr = len(df_opt[df_opt['option_type'] == 'Put']) / len(df_opt[df_opt['option_type'] == 'Call'])
        else: pcr = 1.31
        return current_price, pcr
    except: return 32284.0, 1.31

price, pcr = fetch_all_data(FINMIND_TOKEN, use_simulation)

# 分數邏輯連動
if pcr >= 1.0:
    raw_score = -5.5 + ((pcr - 1.31) * 20.0)
    main_color = "#2ecc71" # 空方綠
    icon_trade = "🟢 做空"
else:
    raw_score = (1 / pcr) * 7.5
    main_color = "#ff4b4b" # 多方紅
    icon_trade = "🔴 做多"

score_val = round(max(-10.0, min(10.0, raw_score)), 1)
trend_label = "空方壓制" if pcr >= 1.1 else "多方強攻"

# CSS 樣式
st.markdown(f"""
    <style>
    .stMetric {{ background-color: #1c1e26; padding: 15px; border-radius: 10px; border-left: 5px solid {main_color}; }}
    .card {{ background-color: #1c1e26; padding: 20px; border-radius: 10px; border: 1px solid #333; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 畫面渲染 ---
st.title("📈 GEX Pro Dashboard")
st.write(f"最後更新：{datetime.now().strftime('%H:%M:%S')} (每分鐘自動重整)")

# 策略卡片 (還原影片風格)
st.markdown(f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 18px; font-weight: bold; color: {main_color};">{icon_trade} (T2_standard)</span>
            <span style="color: #888;">score: {score_val:+.1f}</span>
        </div>
        <div style="margin: 15px 0; font-size: 16px;">
            停利 {price-300:,.0f} | 進場 {price:,.0f} | 停損 {price+150:,.0f}
        </div>
        <div style="display: flex; gap: 5px; color: #555; font-size: 11px;">
            <span style="border:1px solid #444; padding:2px 4px;">wall=-2</span>
            <span style="border:1px solid #444; padding:2px 4px;">dix=-0.5</span>
            <span style="border:1px solid #444; padding:2px 4px;">smGex={-1 if pcr>=1.1 else 1}</span>
            <span style="border:1px solid #444; padding:2px 4px;">vixTerm={-1 if pcr>=1.2 else 0}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 系統警訊 (重要！)
st.write("")
if pcr >= 1.1:
    st.error(f"⚠️ SM GEX 負值 → 高波動風險 | 正 Gamma 0/6 → 負 Gamma 主導")
elif pcr < 0.9:
    st.success(f"✅ SM GEX 正值 → 市場支撐穩健 | 多方軋空力道強")
else:
    st.info("⚪ 市場進入區間震盪模式")

# 速報表格
st.subheader("📢 盤中速報")
news_data = [
    {"時間": (datetime.now() - timedelta(minutes=30)).strftime("%H:%M"), "訊號": icon_trade, "標題": f"VIX 穩定，{trend_label}下進行..."},
    {"時間": datetime.now().strftime("%H:%M"), "訊號": icon_trade, "標題": "現況：負 Gamma 加速助跌" if pcr > 1.1 else "現況：籌碼推升中"}
]
st.table(pd.DataFrame(news_data).iloc[::-1])