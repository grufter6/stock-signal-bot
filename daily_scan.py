"""
Runs once a day (near market open). Pulls ~6 months of daily history per
symbol from yfinance, computes volatility/trend metrics, classifies each
symbol as "volatile" or "steady", and writes state/classification.json.

That file is what signal_check.py reads every 5 minutes during market
hours, so it doesn't need to re-pull heavy history on every run.
"""
import json
import datetime
import numpy as np
import yfinance as yf

from watchlist import UNIVERSE, TOP_N_PER_BUCKET

VOLATILE_ANN_VOL_MIN = 0.45   # annualized volatility above this -> volatile
STEADY_ANN_VOL_MAX = 0.25     # annualized volatility below this -> steady candidate


def rsi14(closes: np.ndarray) -> float:
    deltas = np.diff(closes[-15:])
    gains = deltas.clip(min=0).mean()
    losses = (-deltas.clip(max=0)).mean()
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - (100 / (1 + rs))


def analyze(symbol: str, spy_returns: np.ndarray) -> dict | None:
    hist = yf.Ticker(symbol).history(period="6mo", interval="1d")
    if hist.empty or len(hist) < 60:
        return None

    closes = hist["Close"].to_numpy()
    highs = hist["High"].to_numpy()
    lows = hist["Low"].to_numpy()
    returns = np.diff(closes) / closes[:-1]

    ann_vol = float(returns[-20:].std() * np.sqrt(252))
    sma50 = float(closes[-50:].mean())
    sma200 = float(closes[-200:].mean()) if len(closes) >= 200 else float(closes.mean())
    rsi = float(rsi14(closes))

    tr = np.maximum(highs[1:] - lows[1:],
                     np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])))
    atr14 = float(tr[-14:].mean())
    atr_pct = float(atr14 / closes[-1] * 100)

    # beta vs SPY over the overlapping window
    n = min(len(returns), len(spy_returns))
    beta = None
    if n > 20:
        cov = np.cov(returns[-n:], spy_returns[-n:])
        if cov[1, 1] != 0:
            beta = float(cov[0, 1] / cov[1, 1])

    price = float(closes[-1])
    bucket = "neutral"
    if ann_vol >= VOLATILE_ANN_VOL_MIN or atr_pct >= 3.5:
        bucket = "volatile"
    elif ann_vol <= STEADY_ANN_VOL_MAX and price > sma50 and price > sma200:
        bucket = "steady"

    return {
        "symbol": symbol,
        "price": price,
        "ann_vol": round(ann_vol, 4),
        "atr_pct": round(atr_pct, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "rsi14": round(rsi, 1),
        "beta": round(beta, 2) if beta is not None else None,
        "bucket": bucket,
    }


def main():
    spy_hist = yf.Ticker("SPY").history(period="6mo", interval="1d")
    spy_closes = spy_hist["Close"].to_numpy()
    spy_returns = np.diff(spy_closes) / spy_closes[:-1]

    results = []
    for sym in UNIVERSE:
        try:
            r = analyze(sym, spy_returns)
            if r:
                results.append(r)
        except Exception as e:
            print(f"skip {sym}: {e}")

    volatile = sorted([r for r in results if r["bucket"] == "volatile"],
                       key=lambda r: r["ann_vol"], reverse=True)[:TOP_N_PER_BUCKET]
    steady = sorted([r for r in results if r["bucket"] == "steady"],
                     key=lambda r: r["ann_vol"])[:TOP_N_PER_BUCKET]

    out = {
        "date": datetime.date.today().isoformat(),
        "volatile": volatile,
        "steady": steady,
    }
    with open("state/classification.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"volatile: {[r['symbol'] for r in volatile]}")
    print(f"steady:   {[r['symbol'] for r in steady]}")


if __name__ == "__main__":
    main()
