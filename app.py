import json
import pathlib

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Stock Signal Bot", layout="wide")

STATE = pathlib.Path(__file__).parent / "state"


def load(name, default):
    p = STATE / name
    if not p.exists():
        return default
    with open(p) as f:
        return json.load(f)


classification = load("classification.json", {"date": "", "volatile": [], "steady": []})
live_quotes = load("live_quotes.json", {})
signal_log = load("signal_log.json", [])

st.title("Stock Signal Bot")
st.caption(
    "Informational screener, not financial advice. Volatile/steady buckets and "
    "moving averages come from historical data (yfinance); live price and RSI "
    "checks come from Finnhub. Runs automatically on GitHub Actions."
)

if classification["date"]:
    st.caption(f"Classification last updated: {classification['date']}")
else:
    st.warning("No classification yet — the daily scan hasn't run.")


def render_bucket(title, rows, help_text):
    st.subheader(title)
    st.caption(help_text)
    if not rows:
        st.write("Nothing in this bucket today.")
        return
    df = pd.DataFrame(rows)
    if not df.empty:
        df["live"] = df["symbol"].map(
            lambda s: live_quotes.get(s, {}).get("price")
        )
        df["today %"] = df["symbol"].map(
            lambda s: live_quotes.get(s, {}).get("dp")
        )
        cols = ["symbol", "live", "today %", "price", "ann_vol", "atr_pct",
                "rsi14", "sma50", "sma200", "beta"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)


col1, col2 = st.columns(2)
with col1:
    render_bucket("Volatile", classification.get("volatile", []),
                   "Highest measured volatility in the watchlist — alerts fire on outsized intraday moves.")
with col2:
    render_bucket("Steady", classification.get("steady", []),
                   "Lowest measured volatility, in an established uptrend — alerts fire on RSI extremes.")

st.subheader("Signal history")
if signal_log:
    log_df = pd.DataFrame(signal_log).iloc[::-1]
    st.dataframe(log_df, use_container_width=True, hide_index=True)
else:
    st.write("No signals fired yet.")
