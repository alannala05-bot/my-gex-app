import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# --- 1. 基礎設定 ---
st.set_page_config(
    page_title="GEX Pro 專業交易監控",
    layout="centered",
    page_icon="📈"
)

# 🔑 個人資訊 (建議之後改用 st.secrets)
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNCAxNjo1NDo0MiIsInVzZXJfaWQiOiJhbGFubmFsYTA1IiwiZW1haWwiOiJhbGFubmFsYTA1QGdtYWlsLmNvbSIsImlwIjoiMzYuMjM4LjI0Ni42In0.-Q3sLZ8ZtHjRlgEcSqoEyoejG4EHHZmtR_KDo4Tw1yk"
TG_TOKEN = "8534915217:AAHuJkSqUJC71OnLp0OueZOQLP5bw175oNw"
TG_CHAT_ID = "902651547"

# 🔄 自動重整 (60秒)
st_autorefresh(interval=60000, key="datarefresh")

# --- 2. 功能函數 ---

def send_tg_alert(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.sidebar.error(f"TG 發送失敗: {e}")

@st.cache_data(ttl=300)
def fetch_market_data(token, is_sim=False, s_price=32284.0, s_pcr=1.31):
    if is_sim:
        return s_price, s_pcr
    try:
        api = DataLoader()
        api.login_by_token(api_token=token)
        # 抓取期貨
        df_fut = api.taiwan_futures_snapshot()
        if df_fut is not None and not df_fut.empty:
            # 確保抓取大台指(TXF)
            txf_data = df_fut[df_fut['full_code'] == 'TXF']
            price = txf_data['last_price'].iloc[0] if not txf_data.empty else 32284.0
        else:
            price = 32284.0
            
        # 抓取選擇權計算 PCR
        df_opt = api.taiwan_options_snapshot()
        if df_opt is not None and not df_opt.empty:
            p_len = len(df_opt[df_opt['option_type'] == 'Put'])
            c_len = len(df_opt[df_opt['option_type'] == 'Call'])
            pcr = p_len / c_len if c_len > 0 else 1.31
        else:
            pcr = 1.31
        return price, pcr
    except Exception as e:
        st.sidebar.warning(f"數據更新暫緩: {e}")
        return 32284.0, 1.31

# --- 3. 介面控制 ---
with st.sidebar:
    st.title("⚙️ 系統設定")
    use_simulation = st.toggle("開啟模擬模式", value=False)
    if use_simulation:
        sim_price = st.slider("模擬價格", 20000.0, 40000.0, 32284.0)
        sim_pcr = st.slider("模擬 P/C Ratio", 0.4, 2.0, 1.31)
    else:
        sim_price, sim_pcr = 32284.0, 1.31
    st.write("---")
    st.caption("數據每 5 分鐘自動快照")

# --- 4. 邏輯運算 ---
price, pcr = fetch_market_data(FINMIND_TOKEN, use_simulation, sim_price, sim_pcr)

# 分數邏輯 (模擬策略)
if pcr >= 1.0:
    score_val = round(-5.5 + ((pcr - 1.31) * 20.0), 1)
    main_color = "#2ecc71" # 綠色 (做空)
    icon = "🟢 做空"
else:
    score_val = round((1 / pcr) * 7.5, 1)
    main_color = "#ff4b4b" # 紅色 (做多)
    icon = "🔴 做多"

score_val = max(-10.0, min(10.0, score_val))

# --- 5. 報警機制 ---
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = datetime.min

upper_t = 6.5
lower_t = -6.5
is_extreme = score_val >= upper_t or score_val <= lower_t
is_cooled = (datetime.now() - st.session_state.last_alert_time) > timedelta(minutes=1)

if is_extreme and is_cooled:
    alert_type = "🚀 多方強攻" if score_val >= upper_t else "🚨 空方壓制"
    msg = (
        f"{alert_type} 警報\n"
        f"━━━━━━━━━━━━\n"
        f"訊號：{icon}\n"
        f"評分：{score_val:+.1f}\n"
        f"價格：{price:,.0f}\n"
        f"時間：{datetime.now().strftime('%H:%M:%S')}"
    )
    send_tg_alert(msg)
    st.session_state.last_alert_time = datetime.now()
    st.toast("警報已發送至 Telegram")

# --- 6. 介面渲染 ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e1117; color: white; }}
    .card {{ background-color: #1c1e26; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 15px; }}
    </style>
    """, unsafe_allow_html=True)

st.title("📈 GEX Pro 監控系統")
st.write(f"最後更新：{datetime.now().strftime('%H:%M:%S')}")

st.markdown(f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 20px; font-weight: bold; color: {main_color};">{icon}</span>
            <span style="color: #888;">Score: {score_val:+.1f}</span>
        </div>
        <div style="margin: 15px 0; font-size: 18px;">
            <b>進場參考：</b> {price:,.0f} <br>
            <span style="color: #ff4b4b;">停損：{price+150:,.0f}</span> | 
            <span style="color: #2ecc71;">停利：{price-300:,.0f}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
col1.metric("台指期價格", f"{price:,.0f}")
col2.metric("P/C Ratio", f"{pcr:.2f}")

st.divider()
st.caption("數據僅供參考，請注意投資風險。")
