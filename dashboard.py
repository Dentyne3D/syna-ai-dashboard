import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- ⚙️ VPS CONFIGURATION ---
MY_API_KEYS = [
    "AIzaSyAnJGumxJk5RRQBB0N2C2HM5iUu2Wc6nFg",
    "AIzaSyDAduX4UKQ9gWexUEPO9bT7RNV6CIXupOA",
    "AIzaSyA5oqj_i4tDGmW2jkgo_KKc7Iuj8li1DC4",
    "AIzaSyDl8Tcvm7BL6baTsxERnNX5fm2P26OzIdc",
    "AIzaSyDRp4sUElM-8egcqWVQ-YPP1LCtncJn3Vo"
]

SYMBOL = "XAUUSD"
FIXED_LOT = 0.01
SL_POINTS = 500
TP_POINTS = 1000
TRAILING_START = 300 

st.set_page_config(page_title="SYNA AI - VPS PRO", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=10 * 1000, key="vps_final_refresh")

# --- 🎨 CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #050505; color: #e0e0e0; font-family: 'JetBrains Mono', monospace; }
    .price-big { font-size: 80px; font-weight: 800; color: #adff2f; line-height: 1; }
    .analysis-box { background-color: #0d0d0d; border-left: 4px solid #adff2f; padding: 15px; border-radius: 5px; border: 1px solid #1a1a1a; min-height: 100px; }
</style>
""", unsafe_allow_html=True)

# --- 🔍 CORE FUNCTIONS ---

def get_ai_analysis_vps(summary, tf, key_index=0):
    if key_index >= len(MY_API_KEYS):
        return "⚠️ All Keys Failed. (Possible Region Lock)"
    
    try:
        # ✅ แก้ไข URL และใช้ v1beta เพื่อความชัวร์ในรุ่น Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={MY_API_KEYS[key_index]}"
        
        payload = {
            "contents": [{
                "parts": [{"text": f"Analyze XAUUSD {tf} Gold: {summary}. Decision: [BUY], [SELL], or [WAIT] and short reason in Thai."}]
            }]
        }
        
        res = requests.post(url, json=payload, timeout=15)
        
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # ถ้าเจอ 404 หรือ 429 ให้กระโดดไป Key ถัดไปทันที
            return get_ai_analysis_vps(summary, tf, key_index + 1)
    except:
        return get_ai_analysis_vps(summary, tf, key_index + 1)

def apply_trailing_vps():
    if not mt5.initialize(): return
    pos = mt5.positions_get(symbol=SYMBOL)
    if not pos: return
    for p in pos:
        tick = mt5.symbol_info_tick(SYMBOL)
        pt = mt5.symbol_info(SYMBOL).point
        if p.type == 0: # BUY
            if (tick.bid - p.price_open) / pt > TRAILING_START:
                new_sl = tick.bid - (50 * pt)
                if new_sl > p.sl: mt5.order_send({"action": 6, "position": p.ticket, "sl": new_sl, "tp": p.tp})
        elif p.type == 1: # SELL
            if (p.price_open - tick.ask) / pt > TRAILING_START:
                new_sl = tick.ask + (50 * pt)
                if p.sl == 0 or new_sl < p.sl: mt5.order_send({"action": 6, "position": p.ticket, "sl": new_sl, "tp": p.tp})

# --- 🖥️ MAIN ENGINE ---
if mt5.initialize():
    now = datetime.now()
    tick = mt5.symbol_info_tick(SYMBOL)
    apply_trailing_vps()

    # Layout Header
    st.markdown(f"### 💠 SYNA AI IMMORTAL <span style='font-size:12px;color:#444;'>| VPS-READY</span>", unsafe_allow_html=True)
    st.markdown(f"<span class='price-big'>{tick.bid:,.2f}</span>", unsafe_allow_html=True)
    st.divider()

    # Analysis Section
    df_h1 = pd.DataFrame(mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 30))
    df_m15 = pd.DataFrame(mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 30))

    if not df_h1.empty and not df_m15.empty:
        curr_t = pd.to_datetime(df_m15['time'].iloc[-1], unit='s')
        
        if 'vps_t' not in st.session_state or st.session_state['vps_t'] != curr_t or st.session_state.get('force'):
            with st.spinner("AI Global Sync..."):
                st.session_state['h1'] = get_ai_analysis_vps(df_h1.tail(15).to_string(), "H1")
                st.session_state['m15'] = get_ai_analysis_vps(df_m15.tail(15).to_string(), "M15")
                st.session_state['vps_t'] = curr_t
                st.session_state['force'] = False
                
                # Auto Trade Logic
                h1_sig, m15_sig = st.session_state['h1'].upper(), st.session_state['m15'].upper()
                if "[BUY]" in h1_sig and "[BUY]" in m15_sig:
                    mt5.order_send({"action": 1, "symbol": SYMBOL, "volume": FIXED_LOT, "type": 0, "price": tick.ask, "sl": tick.ask-(SL_POINTS*mt5.symbol_info(SYMBOL).point), "tp": tick.ask+(TP_POINTS*mt5.symbol_info(SYMBOL).point), "magic": 999, "type_filling": 1})
                elif "[SELL]" in h1_sig and "[SELL]" in m15_sig:
                    mt5.order_send({"action": 1, "symbol": SYMBOL, "volume": FIXED_LOT, "type": 1, "price": tick.bid, "sl": tick.bid+(SL_POINTS*mt5.symbol_info(SYMBOL).point), "tp": tick.bid-(TP_POINTS*mt5.symbol_info(SYMBOL).point), "magic": 999, "type_filling": 1})

        col1, col2 = st.columns(2)
        with col1: st.info(f"🌍 **H1 Macro:**\n\n{st.session_state.get('h1', 'Checking...')}")
        with col2: st.info(f"⚡ **M15 Entry:**\n\n{st.session_state.get('m15', 'Checking...')}")

    # Portfolio Info
    st.divider()
    acc = mt5.account_info()
    st.metric("Equity", f"{acc.equity:,.2f}", delta=f"{acc.equity - 309.08:,.2f}")
    if st.button("🔄 Force Refresh AI", use_container_width=True): st.session_state['force'] = True
    if st.button("❌ CLOSE ALL POSITIONS", type="primary", use_container_width=True):
        for p in mt5.positions_get(symbol=SYMBOL):
            mt5.order_send({"action": 1, "symbol": SYMBOL, "volume": p.volume, "position": p.ticket, "type": 1 if p.type==0 else 0, "price": mt5.symbol_info_tick(SYMBOL).bid if p.type==0 else mt5.symbol_info_tick(SYMBOL).ask, "magic": 999, "type_filling": 1})
        st.rerun()

mt5.shutdown()