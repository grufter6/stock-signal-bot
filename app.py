import json
import pathlib
import html
import datetime as dt

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Signal Bot", layout="wide", page_icon="📈")

# ---------------------------------------------------------------------------
# palette — dark-mode categorical slots from the validated palette
# (dataviz skill references/palette.md), fixed order, not cycled.
# ---------------------------------------------------------------------------
COLOR_PRICE = "#3987e5"    # slot 1, blue (dark)
COLOR_SMA50 = "#d95926"    # slot 2, orange (dark)
COLOR_SMA200 = "#199e70"   # slot 3, aqua (dark)
GRIDLINE = "rgba(255,255,255,0.08)"
AXIS_MUTED = "#898781"
INK_SECONDARY = "#c3c2b7"  # dark secondary ink
COLOR_UP = "#0ca30c"       # status good
COLOR_DOWN = "#e34948"     # categorical slot 8, used here for negative delta

STATE = pathlib.Path(__file__).parent / "state"
try:
    FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")
except Exception:
    FINNHUB_KEY = ""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

.stApp {
  background:
    radial-gradient(circle at 15% -10%, rgba(0,229,255,0.10), transparent 40%),
    radial-gradient(circle at 90% 5%, rgba(74,58,167,0.12), transparent 35%),
    #05070d;
}

h1.hero-title {
  font-family: 'Chakra Petch', sans-serif;
  font-weight: 700;
  font-size: 2.6rem;
  letter-spacing: 0.03em;
  background: linear-gradient(90deg, #3987e5, #1baf7a 60%, #00e5ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0;
}

h2, h3 {
  font-family: 'Chakra Petch', sans-serif;
  color: #e8f4ff !important;
  border-bottom: 1px solid rgba(0,229,255,0.2);
  padding-bottom: 6px;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(13,20,32,0.55);
  border: 1px solid rgba(0,229,255,0.15) !important;
  border-radius: 16px;
  box-shadow: 0 0 30px rgba(0,229,255,0.04);
}

/* ---- ticker carousels ---- */
.ticker-title {
  display: flex; align-items: center; gap: 8px;
  font-family: 'Chakra Petch', sans-serif; color: #e8f4ff;
  border-bottom: none; margin-bottom: 2px; font-size: 1.3rem;
}
.ticker-help { color: #898781; font-size: 0.82rem; margin: 0 0 10px 0; }
.pulse-dot {
  width: 9px; height: 9px; border-radius: 50%;
  background: #00e5ff; box-shadow: 0 0 8px #00e5ff;
  animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(1.5); }
}

.ticker-row {
  overflow: hidden; position: relative; margin-bottom: 24px;
  mask-image: linear-gradient(90deg, transparent, black 6%, black 94%, transparent);
  -webkit-mask-image: linear-gradient(90deg, transparent, black 6%, black 94%, transparent);
}
.ticker-track {
  display: flex; gap: 14px; width: max-content;
  animation-timing-function: linear; animation-iteration-count: infinite;
}
.ticker-row:hover .ticker-track { animation-play-state: paused; }
@keyframes scroll-left { from { transform: translateX(0); } to { transform: translateX(-50%); } }
@keyframes scroll-right { from { transform: translateX(-50%); } to { transform: translateX(0); } }

.ticker-card {
  flex: 0 0 auto; width: 132px;
  background: rgba(13,20,32,0.7);
  border: 1px solid rgba(0,229,255,0.15);
  border-radius: 12px; padding: 10px 12px;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.ticker-card:hover {
  transform: translateY(-3px);
  border-color: rgba(0,229,255,0.55);
  box-shadow: 0 4px 18px rgba(0,229,255,0.14);
}
.ticker-sym { font-family: 'Chakra Petch', sans-serif; font-weight: 700; font-size: 1rem; color: #e8f4ff; }
.ticker-spark { margin: 4px 0; line-height: 0; }
.ticker-price { font-size: 0.86rem; color: #c3c2b7; }
.ticker-pct { font-weight: 700; font-size: 0.86rem; margin-top: 2px; }
.ticker-pct.up { color: #0ca30c; }
.ticker-pct.down { color: #e34948; }

.news-card {
  display: flex; gap: 14px; padding: 14px; margin-bottom: 10px;
  background: rgba(13,20,32,0.6);
  border: 1px solid rgba(0,229,255,0.12);
  border-radius: 12px;
}
.news-thumb { width: 96px; height: 72px; object-fit: cover; border-radius: 8px; flex-shrink: 0; }
.news-body { display: flex; flex-direction: column; gap: 4px; justify-content: center; }
.news-headline { color: #e8f4ff; font-weight: 600; text-decoration: none; font-size: 0.98rem; }
.news-headline:hover { color: #00e5ff; }
.news-meta { color: #898781; font-size: 0.78rem; }
.news-summary { color: #c3c2b7; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


def load(name, default):
    p = STATE / name
    if not p.exists():
        return default
    with open(p) as f:
        return json.load(f)


classification = load("classification.json", {"date": "", "volatile": [], "steady": []})
live_quotes = load("live_quotes.json", {})
signal_log = load("signal_log.json", [])

st.markdown('<h1 class="hero-title">Stock Signal Bot</h1>', unsafe_allow_html=True)
st.caption(
    "Informational screener, not financial advice. Volatile/steady buckets come from "
    "historical data (yfinance); live price, search and news come from Finnhub. "
    "Runs automatically on GitHub Actions."
)

if classification["date"]:
    st.caption(f"Classification last updated: {classification['date']}")
else:
    st.warning("No classification yet — the daily scan hasn't run.")


@st.cache_data(ttl=900)
def load_history(symbol: str) -> pd.DataFrame:
    return yf.Ticker(symbol).history(period="6mo", interval="1d")


def sparkline_svg(symbol: str, width: int = 104, height: int = 34) -> str:
    hist = load_history(symbol)
    if hist.empty:
        return ""
    closes = hist["Close"].dropna().tail(30).to_numpy()
    if len(closes) < 2:
        return ""
    lo, hi = float(closes.min()), float(closes.max())
    span = (hi - lo) or 1.0
    n = len(closes)
    pts = [f"{(i / (n - 1)) * width:.1f},{height - ((c - lo) / span) * height:.1f}"
           for i, c in enumerate(closes)]
    color = COLOR_UP if closes[-1] >= closes[0] else COLOR_DOWN
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="none"><polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def render_ticker_row(title: str, help_text: str, rows: list, direction: str = "left", speed: int = 26):
    st.markdown(
        f'<div class="ticker-title"><span class="pulse-dot"></span>{html.escape(title)}</div>'
        f'<p class="ticker-help">{html.escape(help_text)}</p>',
        unsafe_allow_html=True,
    )
    if not rows:
        st.caption("No data yet.")
        return
    cards = []
    for r in rows:
        sym = r["symbol"]
        price = r.get("price")
        pct = r.get("pct")
        price_txt = f"${price:,.2f}" if price is not None else "—"
        pct_txt = f"{pct:+.2f}%" if pct is not None else "—"
        pct_cls = "up" if (pct or 0) >= 0 else "down"
        spark = sparkline_svg(sym)
        cards.append(
            f'<div class="ticker-card"><div class="ticker-sym">{html.escape(sym)}</div>'
            f'<div class="ticker-spark">{spark}</div>'
            f'<div class="ticker-price">{price_txt}</div>'
            f'<div class="ticker-pct {pct_cls}">{pct_txt}</div></div>'
        )
    cards_html = "".join(cards)
    anim = "scroll-left" if direction == "left" else "scroll-right"
    st.markdown(
        f'<div class="ticker-row"><div class="ticker-track" '
        f'style="animation-duration:{speed}s;animation-name:{anim};">'
        f'{cards_html}{cards_html}</div></div>',
        unsafe_allow_html=True,
    )


volatile_top = classification.get("volatile", [])[:5]
steady_top = classification.get("steady", [])[:5]

volatile_rows = [{"symbol": r["symbol"],
                   "price": live_quotes.get(r["symbol"], {}).get("price", r.get("price")),
                   "pct": live_quotes.get(r["symbol"], {}).get("dp")} for r in volatile_top]
steady_rows = [{"symbol": r["symbol"],
                "price": live_quotes.get(r["symbol"], {}).get("price", r.get("price")),
                "pct": live_quotes.get(r["symbol"], {}).get("dp")} for r in steady_top]

with_live = [r for r in (volatile_rows + steady_rows) if r["pct"] is not None]
gainers = sorted(with_live, key=lambda r: r["pct"], reverse=True)[:5]
losers = sorted(with_live, key=lambda r: r["pct"])[:5]

with st.container(border=True):
    render_ticker_row("Top Gainers", "Best today's % move in the watchlist.", gainers, direction="left")
    render_ticker_row("Top Losers", "Worst today's % move in the watchlist.", losers, direction="right")
    if not with_live:
        st.caption("Gainers/losers populate once the signal-check job runs during market hours.")

with st.container(border=True):
    render_ticker_row("Volatile", "Highest measured volatility in the watchlist.",
                       volatile_rows, direction="left", speed=30)
    render_ticker_row("Steady", "Lowest measured volatility, established uptrend.",
                       steady_rows, direction="right", speed=30)


@st.cache_data(ttl=3600)
def search_symbols(query: str):
    if not FINNHUB_KEY:
        return []
    try:
        r = requests.get("https://finnhub.io/api/v1/search",
                          params={"q": query, "token": FINNHUB_KEY}, timeout=10)
        r.raise_for_status()
        return r.json().get("result", [])
    except Exception:
        return []


@st.cache_data(ttl=1800)
def get_news(symbol: str):
    if not FINNHUB_KEY:
        return []
    today = dt.date.today()
    frm = today - dt.timedelta(days=10)
    try:
        r = requests.get("https://finnhub.io/api/v1/company-news",
                          params={"symbol": symbol, "from": frm.isoformat(),
                                  "to": today.isoformat(), "token": FINNHUB_KEY},
                          timeout=10)
        r.raise_for_status()
        return r.json()[:8]
    except Exception:
        return []


watchlist_symbols = [r["symbol"] for r in volatile_top + steady_top]

if "active_symbol" not in st.session_state:
    st.session_state.active_symbol = watchlist_symbols[0] if watchlist_symbols else "AAPL"

st.subheader("Explore any symbol")
pick_col, search_col = st.columns([1, 2])
with pick_col:
    if watchlist_symbols:
        default_idx = (watchlist_symbols.index(st.session_state.active_symbol)
                        if st.session_state.active_symbol in watchlist_symbols else 0)
        wl_choice = st.selectbox("From today's watchlist", watchlist_symbols, index=default_idx)
        if wl_choice != st.session_state.active_symbol:
            st.session_state.active_symbol = wl_choice

with search_col:
    query = st.text_input("🔍 Search any stock or ETF", placeholder="e.g. NVDA, VOO, Tesla")
    if query:
        if not FINNHUB_KEY:
            st.caption("Search needs a Finnhub key — add FINNHUB_API_KEY in this app's "
                       "Settings → Secrets (Manage app menu).")
        else:
            results = search_symbols(query)
            if results:
                labels = [f"{r['symbol']} — {r.get('description', '')}" for r in results[:15]]
                choice = st.selectbox("Matches", labels)
                chosen_symbol = results[labels.index(choice)]["symbol"]
                if st.button(f"View {chosen_symbol}"):
                    st.session_state.active_symbol = chosen_symbol
            else:
                st.caption("No matches found.")

symbol = st.session_state.active_symbol

with st.container(border=True):
    st.subheader(f"Price chart — {symbol}")
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
            xaxis=dict(showgrid=False, linecolor=AXIS_MUTED, tickfont=dict(color=INK_SECONDARY)),
            yaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickprefix="$",
                       linecolor=AXIS_MUTED, tickfont=dict(color=INK_SECONDARY)),
        )
        st.plotly_chart(fig, use_container_width=True)

with st.container(border=True):
    st.subheader(f"News — {symbol}")
    if not FINNHUB_KEY:
        st.info("Add FINNHUB_API_KEY in this app's Settings → Secrets to enable news.")
    else:
        news_items = get_news(symbol)
        if not news_items:
            st.write("No recent news found for this symbol.")
        else:
            for item in news_items:
                headline = html.escape(item.get("headline", ""))
                summary = html.escape((item.get("summary") or "")[:220])
                source = html.escape(item.get("source", ""))
                url = item.get("url", "#")
                ts = item.get("datetime")
                when = dt.datetime.utcfromtimestamp(ts).strftime("%b %d, %Y") if ts else ""
                img = item.get("image") or ""
                thumb = f'<img src="{img}" class="news-thumb"/>' if img else ""
                st.markdown(
                    f'<div class="news-card">{thumb}<div class="news-body">'
                    f'<a href="{url}" target="_blank" class="news-headline">{headline}</a>'
                    f'<div class="news-meta">{source} · {when}</div>'
                    f'<div class="news-summary">{summary}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

with st.container(border=True):
    st.subheader("Signal history")
    if signal_log:
        log_df = pd.DataFrame(signal_log).iloc[::-1]
        st.dataframe(log_df, use_container_width=True, hide_index=True)
    else:
        st.write("No signals fired yet.")
