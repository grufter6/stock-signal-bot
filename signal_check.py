"""
Runs every 5 minutes on the GitHub Actions cron. Exits immediately outside
US market hours. Reads today's state/classification.json (written by
daily_scan.py), pulls a live quote per symbol from Finnhub, checks for a
signal, and pushes a notification via ntfy.sh. Dedupes so each symbol+signal
only notifies once per day (tracked in state/notified_today.json).
"""
import os
import json
import datetime
import requests
import pytz

FINNHUB_KEY = os.environ["FINNHUB_API_KEY"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

CLASSIFICATION_PATH = "state/classification.json"
NOTIFIED_PATH = "state/notified_today.json"

VOLATILE_MOVE_MULTIPLIER = 1.5  # today's move must exceed this * the symbol's avg daily range
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70


def market_is_open() -> bool:
    now = datetime.datetime.now(pytz.timezone("America/New_York"))
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_t <= now <= close_t


def get_quote(symbol: str) -> dict:
    r = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": FINNHUB_KEY},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def notify(message: str):
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), timeout=10)


def main():
    if not market_is_open():
        print("market closed, skipping")
        return

    if not os.path.exists(CLASSIFICATION_PATH):
        print("no classification.json yet, skipping")
        return

    with open(CLASSIFICATION_PATH) as f:
        classification = json.load(f)

    today = datetime.date.today().isoformat()
    if classification.get("date") != today:
        print("classification.json is stale, skipping")
        return

    notified = {}
    if os.path.exists(NOTIFIED_PATH):
        with open(NOTIFIED_PATH) as f:
            notified = json.load(f)
    if notified.get("date") != today:
        notified = {"date": today, "keys": []}

    def already_sent(key: str) -> bool:
        return key in notified["keys"]

    def mark_sent(key: str):
        notified["keys"].append(key)

    for row in classification.get("volatile", []):
        sym = row["symbol"]
        try:
            q = get_quote(sym)
        except Exception as e:
            print(f"quote failed {sym}: {e}")
            continue
        pct_move = q.get("dp")
        if pct_move is None:
            continue
        threshold = row["atr_pct"] * VOLATILE_MOVE_MULTIPLIER
        key = f"{sym}:volatile_move"
        if abs(pct_move) >= threshold and not already_sent(key):
            notify(f"[volatile] {sym} moved {pct_move:+.1f}% today "
                   f"(avg daily range ~{row['atr_pct']:.1f}%) — worth a look")
            mark_sent(key)

    for row in classification.get("steady", []):
        sym = row["symbol"]
        try:
            q = get_quote(sym)
        except Exception as e:
            print(f"quote failed {sym}: {e}")
            continue
        price = q.get("c")
        if price is None:
            continue
        rsi = row["rsi14"]
        if rsi <= RSI_OVERSOLD:
            key = f"{sym}:oversold"
            if not already_sent(key):
                notify(f"[steady] {sym} RSI {rsi} (oversold), price ${price:.2f}, "
                       f"50d avg ${row['sma50']:.2f} — possible entry")
                mark_sent(key)
        elif rsi >= RSI_OVERBOUGHT:
            key = f"{sym}:overbought"
            if not already_sent(key):
                notify(f"[steady] {sym} RSI {rsi} (overbought), price ${price:.2f}, "
                       f"50d avg ${row['sma50']:.2f} — consider trimming")
                mark_sent(key)

    with open(NOTIFIED_PATH, "w") as f:
        json.dump(notified, f, indent=2)


if __name__ == "__main__":
    main()
