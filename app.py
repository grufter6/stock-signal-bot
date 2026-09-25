import json
import pathlib

import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Signal Bot", layout="wide")

# categorical slots from the validated palette (references/palette.md) —
# fixed order, not cycled: price / sma50 / sma200
COLOR_PRICE = "#2a78d6"   # slot 1, blue
COLOR_SMA50 = "#eb6834"   # slot 2, orange
COLOR_SMA200 = "#1baf7a"  # slot 3, aqua
GRIDLINE = "#e1e0d9"
AXIS_MUTED = "#898781"
INK_SECONDARY = "#52514e"

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


@st.cache_data(ttl=900)
def load_history(symbol: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period="6mo", interval="1d")


st.subheader("Price chart")
all_rows = classification.get("volatile", []) + classification.get("steady", [])
symbols = [r["symbol"] for r in all_rows]
if symbols:
    symbol = st.selectbox("Symbol", symbols)
    hist = load_history(symbol)
    if hist.empty:
        st.write("No price history returned for this symbol.")
    else:
        sma50 = hist["Close"].rolling(50).mean()
        sma200 = hist["Close"].rolling(200).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], name="Close",
                                  mode="lines", line=dict(color=COLOR_PRICE, width=2)))
        fig.add_trace(go.Scatter(x=hist.index, y=sma50, name="SMA50",
                                  mode="lines", line=dict(color=COLOR_SMA50, width=2)))
        fig.add_trace(go.Scatter(x=hist.index, y=sma200, name="SMA200",
                                  mode="lines", line=dict(color=COLOR_SMA200, width=2)))
        fig.update_layout(
            height=450,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="left", x=0, font=dict(color=INK_SECONDARY)),
            xaxis=dict(showgrid=False, linecolor=AXIS_MUTED, tickfont=dict(color=AXIS_MUTED)),
            yaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickprefix="$",
                       linecolor=AXIS_MUTED, tickfont=dict(color=AXIS_MUTED)),
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No symbols to chart yet.")

st.subheader("Signal history")
if signal_log:
    log_df = pd.DataFrame(signal_log).iloc[::-1]
    st.dataframe(log_df, use_container_width=True, hide_index=True)
else:
    st.write("No signals fired yet.")
