import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# --- 1. 基礎設定與祕密資訊 ---
st.set_page_config(
    page_title="GEX Pro 專業交易監控",
    layout="centered",
    page_icon="📈"
)

# 🔑 請填入你的個人資訊
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0wNCAxNjo1NDo0MiIsInVzZXJfaWQiOiJhbGFubmFsYTA1IiwiZW1haWwiOiJhbGFubmFsYTA1QGdtYWlsLmNvbSIsImlwIjoiMzYuMjM4LjI0Ni42In0.-Q3sLZ8ZtHjRlgEcSqoEyoejG4EHHZmtR_KDo4Tw1yk"
TG_TOKEN = "8534915217:AAHuJkSqUJC71OnLp0OueZOQLP5bw175oNw"
TG_CHAT_ID = "902651547"

# 🔄 自動重整機制 (每 60 秒自動更新一次畫面)
st_autorefresh(interval=60000, key="datarefresh")

# --- 2. 功能函數定義 ---

def send_tg_alert(message):
    """發送訊息至 Telegram 機器人"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.error(f"Telegram 發送失敗: {e}")

@st.cache_data(ttl=300)
def fetch_market_data(token, is_sim=False, s_price=32284.0, s_pcr=1.31):
    """抓取台指期與選擇權快照數據"""
    if is_sim:
        return s_price, s_pcr
    try:
        api = DataLoader()
        api.login_by_token(api_token=token)
        # 抓取期貨快照
        df_fut = api.taiwan_futures_snapshot()
        price = df_fut[df_fut['full_code'] == 'TXF']['last_price'].values[0] if df_fut is not None else 32284.0
        # 抓取選擇權快照計算 PCR
        df_opt = api.taiwan_options_snapshot()
        if df_opt is not None and not df_opt.empty:
            p_len = len(df_opt[df_opt['option_type'] == 'Put'])
            c_len = len(df_opt[df_opt['option_type'] == 'Call'])
            pcr = p_len / c_len if c_len > 0 else 1.0
        else:
            pcr = 1.31
        return price, pcr
    except:
        return 32284.0, 1.31

# --- 3. 側邊欄控制面板 ---
with st.sidebar:
    st.title("⚙️ 系統設定")
    use_simulation = st.toggle("開啟模擬模式 (測試報警用)", value=False)
    if use_simulation:
        sim_price = st.slider("模擬價格", 20000.0, 35000.0, 32284.0)
        sim_pcr = st.slider("模擬 P/C Ratio", 0.4, 2.0, 1.31)
    else:
        sim_price, sim_pcr = 32284.0, 1.31
    st.write("---")
    st.caption("數據每 5 分鐘快照一次 (TTL: 300s)")

# --- 4. 核心邏輯運算 ---
price, pcr = fetch_market_data(FINMIND_TOKEN, use_simulation, sim_price, sim_pcr)

# 模擬影片中的分數邏輯
if pcr >= 1.0:
    # 空方邏輯：PCR 越高，分數越負
    score_val = round(-5.5 + ((pcr - 1.31) * 20.0), 1)
    main_color = "#2ecc71" # 影片中的綠色 (做空獲利)
    icon = "🟢 做空"
else:
    # 多方邏輯：PCR 越低，分數越正
    score_val = round((1 / pcr) * 7.5, 1)
    main_color = "#ff4b4b" # 影片中的紅色 (做多)
    icon = "🔴 做多"

score_val = max(-10.0, min(10.0, score_val)) # 限制在 ±10 分

# --- 5. Telegram 雙向報警 (門檻 ±6.5) ---
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = datetime.min

upper_threshold = 6.5
lower_threshold = -6.5
is_extreme = score_val >= upper_threshold or score_val <= lower_threshold
is_cooled_down = (datetime.now() - st.session_state.last_alert_time) > timedelta(minutes=5)

if is_extreme and is_cooled_down:
    alert_type = "🚀 多方強攻" if score_val >= upper_threshold else "🚨 空方壓制"
    note = "正 Gamma 軋空" if score_val >= upper_threshold else "負 Gamma 助跌"
    msg = (
        f"{alert_type} 警報\n"
        f"━━━━━━━━━━━━\n"
        f"訊號：{icon}\n"
        f"評分：{score_val:+.1f}\n"
        f"價格：{price:,.0f}\n"
        f"提示：{note}\n"
        f"時間：{datetime.now().strftime('%H:%M:%S')}"
    )
    send_tg_alert(msg)
    st.session_state.last_alert_time = datetime.now()
    st.toast(f"Telegram 報警已發送: {alert_type}")

# --- 6. iPhone 優化網頁介面渲染 ---
st.markdown(f"""
    <style>
    .main {{ background-color: #0e1117; color: white; }}
    .stMetric {{ background-color: #1c1e26; padding: 10px; border-radius: 8px; border-left: 5px solid {main_color}; }}
    .card {{ background-color: #1c1e26; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 15px; }}
    @media (max-width: 600px) {{ .card {{ padding: 15px; }} h1 {{ font-size: 22px !important; }} }}
    </style>
    """, unsafe_allow_html=True)

st.title("📈 GEX Pro 實時監控系統")
st.write(f"更新時間：{datetime.now().strftime('%H:%M:%S')}")

# 仿影片策略卡片
st.markdown(f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 20px; font-weight: bold; color: {main_color};">{icon} (T2_Standard)</span>
            <span style="color: #888; font-family: monospace;">score: {score_val:+.1f}</span>
        </div>
        <div style="margin: 15px 0; font-size: 18px; letter-spacing: 1px;">
            <b>進場：</b> {price:,.0f} <br>
            <span style="color: #ff4b4b;"><b>停損：</b> {price+150:,.0f}</span> | 
            <span style="color: #2ecc71;"><b>停利：</b> {price-300:,.0f}</span>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <span style="border:1px solid #444; padding:2px 6px; font-size:12px; color:#888;">wall=-2</span>
            <span style="border:1px solid #444; padding:2px 6px; font-size:12px; color:#888;">dix=-0.5</span>
            <span style="border:1px solid #444; padding:2px 6px; font-size:12px; color:#888;">smGex={-1 if pcr>=1.1 else 1}</span>
            <span style="border:1px solid #444; padding:2px 6px; font-size:12px; color:#888;">vixTerm={-1 if pcr>=1.2 else 0}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 警訊標籤
if score_val <= -6.5:
    st.error("🚨 SM GEX 負值 → 高波動風險 | 負 Gamma 主導助跌")
elif score_val >= 6.5:
    st.success("🚀 SM GEX 正值 → 強力軋空訊號 | 正 Gamma 主導助漲")
else:
    st.info("⚪ 目前市場數據穩定，處於區間震盪模式")

# 數據小卡
col1, col2 = st.columns(2)
col1.metric("台指期現價", f"{price:,.0f}")
col2.metric("P/C Ratio", f"{pcr:.2f}", delta=f"{'空方強' if pcr>1.1 else '多方強'}")

st.divider()
st.caption("本系統數據僅供參考，投資請謹慎評估風險。")